from datetime import time, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment
from apps.payments.models import Payment
from .availability import bookable_slots, free_slots_for_date, in_booking_hours, local_datetime, lock_free_slot
from .models import Appointment, AppointmentSlot
from .serializers import (
	AppointmentRequestSerializer, AppointmentSerializer, AppointmentSlotSerializer,
	DoctorAssignmentSerializer, PatientSlotQuerySerializer, SlotDateSerializer, SlotDatesQuerySerializer,
)

APPOINTMENT_EXAMPLE = {
	'id': 12345, 'appointment_number': 'APT-12345', 'consultation': 42, 'slot': 318,
	'slot_time': '2026-10-18T10:00:00+05:30', 'schedule_date': '2026-10-18', 'schedule_time': '10:00 AM',
	'status': 'awaiting_payment', 'status_label': 'Awaiting payment', 'patient_name': 'Rahul Sharma',
	'consultation_title': 'General Consultation', 'speciality': None,
	'chief_complaint': 'Headache - Cluster Headache - Chronic', 'mode_label': 'Online', 'doctor': None, 'doctor_name': None, 'doctor_specialization': None,
	'amount': 200, 'currency': 'INR', 'payment_status': 'not_started', 'created_at': '2026-10-16T18:20:00+05:30',
}


class SlotsView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSlotSerializer
	pagination_class = None

	@extend_schema(
		tags=['Mobile scheduling'], summary='Schedule Appointment: free time slots for a date',
		description=(
			'Times are 15-minute slots opened by verified doctors from the doctor app, between 08:00 and 23:59 India time. '
			'Each time appears once; `remaining_capacity` is how many doctors are still free then. '
			'Tapping "Request Appointment" only opens Case Preview - nothing is reserved until "Submit Case".'
		),
		parameters=[PatientSlotQuerySerializer], responses=AppointmentSlotSerializer(many=True),
		examples=[OpenApiExample('Slots', response_only=True, value=[
			{'id': 318, 'starts_at': '2026-10-18T08:00:00+05:30', 'time_display': '08:00 AM', 'remaining_capacity': 2},
			{'id': 319, 'starts_at': '2026-10-18T08:15:00+05:30', 'time_display': '08:15 AM', 'remaining_capacity': 1},
		])],
	)
	def get(self, request):
		query = PatientSlotQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		data = query.validated_data
		return Response(self.get_serializer(free_slots_for_date(data['date'], data.get('speciality_id')), many=True).data)


class SlotDatesView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = SlotDateSerializer
	pagination_class = None

	@extend_schema(
		tags=['Mobile scheduling'], summary='Schedule Appointment: date strip (Today and the next days)',
		description='Returns one entry per day starting today with the number of free times, so the app can grey out days with none.',
		parameters=[SlotDatesQuerySerializer], responses=SlotDateSerializer(many=True),
		examples=[OpenApiExample('Date strip', response_only=True, value=[
			{'date': '2026-10-16', 'day_label': 'Today', 'day_number': 16, 'available_slot_count': 6},
			{'date': '2026-10-17', 'day_label': 'Sat', 'day_number': 17, 'available_slot_count': 0},
			{'date': '2026-10-18', 'day_label': 'Sun', 'day_number': 18, 'available_slot_count': 24},
		])],
	)
	def get(self, request):
		query = SlotDatesQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		days = query.validated_data.get('days') or 7
		today = timezone.localdate()
		counts = {}
		start = local_datetime(today, time(0))
		slots = bookable_slots(query.validated_data.get('speciality_id')).filter(starts_at__lt=start + timedelta(days=days))
		for slot in slots:
			if slot.occupied >= slot.capacity or not in_booking_hours(slot.starts_at):
				continue
			day = timezone.localtime(slot.starts_at).date()
			counts.setdefault(day, set()).add(slot.starts_at)
		result = []
		for offset in range(days):
			day = today + timedelta(days=offset)
			result.append({
				'date': day, 'day_label': 'Today' if offset == 0 else day.strftime('%a'),
				'day_number': day.day, 'available_slot_count': len(counts.get(day, ())),
			})
		return Response(self.get_serializer(result, many=True).data)


class AppointmentListCreateView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentRequestSerializer

	@extend_schema(
		tags=['Mobile scheduling'], summary='Submit Case: reserve the selected slot',
		description=(
			'Call from Case Preview after the patient ticks "I confirm the information provided above is correct." '
			'`information_confirmed` must be true. If the exact slot was just taken but another doctor is free at the same time, '
			'that slot is used instead. Fee is server-set: the general physician fee of the step 1 country_code (default INR 200), or the INR speciality fee. Repeating the same request returns the existing appointment. '
			'Next: create a payment order for the returned appointment (Checkout).'
		),
		request=AppointmentRequestSerializer, responses={201: AppointmentSerializer, 200: AppointmentSerializer},
		examples=[
			OpenApiExample('Submit case', request_only=True, value={'consultation_id': 42, 'slot_id': 318, 'information_confirmed': True}),
			OpenApiExample('Appointment created', response_only=True, status_codes=['201'], value=APPOINTMENT_EXAMPLE),
			OpenApiExample('Same request repeated: existing appointment', response_only=True, status_codes=['200'], value=APPOINTMENT_EXAMPLE),
		],
	)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		with transaction.atomic():
			consultation = get_object_or_404(Consultation.objects.select_for_update(), pk=data['consultation_id'], patient=request.user)
			existing = Appointment.objects.filter(consultation=consultation).first()
			if existing:
				if existing.slot_id != data['slot_id'] and (not existing.slot or existing.slot_time != _slot_time(data['slot_id'])):
					raise serializers.ValidationError('This consultation already has an appointment.')
				return Response(AppointmentSerializer(existing).data)
			if consultation.status != Consultation.Status.DRAFT or not consultation.history_completed:
				raise serializers.ValidationError('Complete the draft health-history step before scheduling.')
			if not all([consultation.patient_name, consultation.patient_age is not None, consultation.patient_gender, consultation.patient_phone]):
				raise serializers.ValidationError('Complete patient details before scheduling.')
			selected = get_object_or_404(AppointmentSlot, pk=data['slot_id'], is_active=True)
			if selected.starts_at <= timezone.now() or not in_booking_hours(selected.starts_at):
				raise serializers.ValidationError('Select a future slot between 08:00 and 23:59 India time.')
			if consultation.speciality_id and not consultation.speciality.is_active:
				raise serializers.ValidationError('This speciality is not available right now. Please choose another.')
			slot = lock_free_slot(selected.starts_at, preferred_id=selected.pk, speciality_id=consultation.speciality_id)
			if slot is None:
				raise serializers.ValidationError('This slot is no longer available. Please choose another time.')
			now = timezone.now()
			consultation.status = Consultation.Status.REQUESTED
			consultation.fee_charged = consultation.expected_fee
			consultation.currency = consultation.expected_currency
			consultation.scheduled_at = slot.starts_at
			consultation.information_confirmed_at = now
			consultation.save(update_fields=['status', 'fee_charged', 'currency', 'scheduled_at', 'information_confirmed_at'])
			appointment = Appointment.objects.create(
				consultation=consultation, patient=request.user, slot=slot, slot_time=slot.starts_at,
				status=Appointment.Status.AWAITING_PAYMENT,
			)
		return Response(AppointmentSerializer(appointment).data, status=201)

	@extend_schema(tags=['Mobile scheduling'], summary='My appointments', responses=AppointmentSerializer(many=True))
	def get(self, request):
		queryset = Appointment.objects.filter(patient=request.user).select_related('consultation', 'doctor__doctor_profile').order_by('-created_at')
		page = self.paginate_queryset(queryset)
		return self.get_paginated_response(AppointmentSerializer(page, many=True).data)


def _slot_time(slot_id):
	return AppointmentSlot.objects.filter(pk=slot_id).values_list('starts_at', flat=True).first()


class AppointmentDetailView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSerializer

	@extend_schema(
		tags=['Mobile scheduling'], summary='Checkout / "Finding Your Doctor": appointment summary and status',
		description=(
			'Checkout shows `appointment_number`, `schedule_date`, `schedule_time` and `amount`. After payment, poll this: '
			'`finding_doctor` = payment successful and a doctor is being matched; `confirmed` adds `doctor_name`.'
		),
		examples=[OpenApiExample('Finding doctor', response_only=True, value={
			**APPOINTMENT_EXAMPLE, 'status': 'finding_doctor', 'status_label': 'Finding doctor', 'payment_status': 'success',
		})],
	)
	def get(self, request, appointment_id):
		appointment = get_object_or_404(Appointment.objects.select_related('consultation', 'doctor__doctor_profile'), pk=appointment_id, patient=request.user)
		return Response(self.get_serializer(appointment).data)


class AssignDoctorView(generics.GenericAPIView):
	permission_classes = [IsAdminUser]
	serializer_class = DoctorAssignmentSerializer

	@extend_schema(
		tags=['Staff matching'], summary='Staff only: assign a verified doctor to a paid appointment',
		description=(
			"The doctor must be a general physician for general bookings, or of the booking's speciality with "
			"consultation_fee and currency equal to the fee paid. "
			"If the doctor differs from the slot's doctor, the booking moves to that doctor's free slot at the same time."
		),
		responses=AppointmentSerializer,
		examples=[OpenApiExample('Assign', request_only=True, value={'doctor_id': 7})],
	)
	def post(self, request, appointment_id):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		with transaction.atomic():
			appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id)
			if appointment.status != Appointment.Status.FINDING_DOCTOR:
				raise serializers.ValidationError('Only paid appointments awaiting matching can be assigned.')
			if not Payment.objects.filter(consultation=appointment.consultation, status=Payment.Status.SUCCESS).exists():
				raise serializers.ValidationError('Confirmed payment is required.')
			consultation = appointment.consultation
			doctors = DoctorProfile.objects.select_for_update().filter(
				is_active=True, user__is_active=True, user__role='doctor', verification_status='verified',
				speciality_id=consultation.speciality_id,
			)
			if consultation.speciality_id:
				# General physician fees are fixed per country, so only specialists must match the fee paid.
				doctors = doctors.filter(consultation_fee=consultation.fee_charged, currency=consultation.currency)
			profile = get_object_or_404(doctors, user_id=serializer.validated_data['doctor_id'])
			if Appointment.objects.filter(doctor=profile.user, slot_time=appointment.slot_time).exclude(pk=appointment.pk).exclude(status=Appointment.Status.CANCELLED).exists():
				raise serializers.ValidationError('Doctor already has an appointment at this time.')
			update_fields = ['doctor']
			current = appointment.slot
			if current is not None and current.doctor_id is not None and current.doctor_id != profile.user_id:
				target = AppointmentSlot.objects.select_for_update().filter(
					doctor=profile.user, starts_at=appointment.slot_time, is_active=True,
				).first()
				if target is None or target.appointments.exclude(status=Appointment.Status.CANCELLED).count() >= target.capacity:
					raise serializers.ValidationError('This doctor has no free slot at the appointment time.')
				appointment.slot = target
				update_fields.append('slot')
			appointment.doctor = profile.user
			update_fields += appointment.set_status(Appointment.Status.CONFIRMED)
			appointment.save(update_fields=update_fields)
			appointment.consultation.doctor = profile.user
			appointment.consultation.save(update_fields=['doctor'])
			notify_appointment(appointment, Notification.Kind.DOCTOR_ASSIGNED)
		return Response(AppointmentSerializer(appointment).data)
