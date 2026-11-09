from datetime import timedelta

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
from apps.notifications.service import notify_appointment, notify_doctor
from apps.payments.models import Payment
from .availability import booking_times_for_date
from .models import Appointment, AppointmentSlot
from .serializers import (
	AppointmentRequestSerializer, AppointmentSerializer, AppointmentSlotSerializer,
	DoctorAssignmentSerializer, SlotDateSerializer, SlotDatesQuerySerializer, SlotQuerySerializer,
)

FREED_STATUSES = (Appointment.Status.CANCELLED, Appointment.Status.COMPLETED)

APPOINTMENT_EXAMPLE = {
	'id': 12345, 'appointment_number': 'APT-12345', 'consultation': 42, 'slot': None,
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
		tags=['Mobile scheduling'], summary='Schedule Appointment: selectable times for a date',
		description=(
			'Every 15-minute time from 08:00 AM to 11:45 PM India time on that date, for any category. Past times are left out; '
			'dates before today or more than 30 days ahead return an empty list. The patient only picks a preferred time - '
			'no doctor is chosen; staff assign a doctor after payment. '
			'Tapping "Request Appointment" only opens Case Preview with this `starts_at` - nothing is reserved until "Submit Case".'
		),
		parameters=[SlotQuerySerializer], responses=AppointmentSlotSerializer(many=True),
		examples=[OpenApiExample('Times', response_only=True, value=[
			{'starts_at': '2026-10-18T08:00:00+05:30', 'time_display': '08:00 AM'},
			{'starts_at': '2026-10-18T08:15:00+05:30', 'time_display': '08:15 AM'},
			{'starts_at': '2026-10-18T08:30:00+05:30', 'time_display': '08:30 AM'},
		])],
	)
	def get(self, request):
		query = SlotQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		times = booking_times_for_date(query.validated_data['date'])
		return Response(self.get_serializer([{'starts_at': starts_at} for starts_at in times], many=True).data)


class SlotDatesView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = SlotDateSerializer
	pagination_class = None

	@extend_schema(
		tags=['Mobile scheduling'], summary='Schedule Appointment: date strip (Today and the next days)',
		description=(
			'One entry per day starting today with the number of selectable times (64 for a full day, fewer today as times pass), '
			'so the app can grey out days with none.'
		),
		parameters=[SlotDatesQuerySerializer], responses=SlotDateSerializer(many=True),
		examples=[OpenApiExample('Date strip', response_only=True, value=[
			{'date': '2026-10-16', 'day_label': 'Today', 'day_number': 16, 'available_slot_count': 18},
			{'date': '2026-10-17', 'day_label': 'Sat', 'day_number': 17, 'available_slot_count': 64},
			{'date': '2026-10-18', 'day_label': 'Sun', 'day_number': 18, 'available_slot_count': 64},
		])],
	)
	def get(self, request):
		query = SlotDatesQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		days = query.validated_data.get('days') or 7
		today = timezone.localdate()
		result = []
		for offset in range(days):
			day = today + timedelta(days=offset)
			result.append({
				'date': day, 'day_label': 'Today' if offset == 0 else day.strftime('%a'),
				'day_number': day.day, 'available_slot_count': len(booking_times_for_date(day)),
			})
		return Response(self.get_serializer(result, many=True).data)


class AppointmentListCreateView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentRequestSerializer

	@extend_schema(
		tags=['Mobile scheduling'], summary='Submit Case: create the appointment at the chosen time',
		description=(
			'Call from Case Preview after the patient ticks "I confirm the information provided above is correct." '
			'`information_confirmed` must be true. `starts_at` is the time picked on Schedule Appointment: a future 15-minute '
			'time from 08:00 AM to 11:45 PM India time within 30 days. No doctor is chosen here.\n\n'
			'The fee is fixed and server-set (same as `GET /api/v1/pricing/consultation-fee/`): the general physician fee of the '
			'step 1 country_code (default INR 200), or for a speciality the INR mode of its verified doctors\' fees. It is locked '
			'now and does not change later. Repeating the same request returns the existing appointment.\n\n'
			'Next: create a payment order for the returned appointment (Checkout). After payment the status is `finding_doctor` '
			'until staff assign a doctor (`confirmed`).'
		),
		request=AppointmentRequestSerializer, responses={201: AppointmentSerializer, 200: AppointmentSerializer},
		examples=[
			OpenApiExample(
				'Submit case', request_only=True,
				value={'consultation_id': 42, 'starts_at': '2026-10-18T10:00:00+05:30', 'information_confirmed': True},
			),
			OpenApiExample('Appointment created', response_only=True, status_codes=['201'], value=APPOINTMENT_EXAMPLE),
			OpenApiExample('Same request repeated: existing appointment', response_only=True, status_codes=['200'], value=APPOINTMENT_EXAMPLE),
		],
	)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		starts_at = data['starts_at']
		with transaction.atomic():
			consultation = get_object_or_404(Consultation.objects.select_for_update(), pk=data['consultation_id'], patient=request.user)
			existing = Appointment.objects.filter(consultation=consultation).first()
			if existing:
				if existing.slot_time != starts_at:
					raise serializers.ValidationError('This consultation already has an appointment.')
				return Response(AppointmentSerializer(existing).data)
			if consultation.status != Consultation.Status.DRAFT or not consultation.history_completed:
				raise serializers.ValidationError('Complete the draft health-history step before scheduling.')
			if not all([consultation.patient_name, consultation.patient_age is not None, consultation.patient_gender, consultation.patient_phone]):
				raise serializers.ValidationError('Complete patient details before scheduling.')
			if consultation.speciality_id and not consultation.speciality.is_active:
				raise serializers.ValidationError('This speciality is not available right now. Please choose another.')
			now = timezone.now()
			consultation.status = Consultation.Status.REQUESTED
			consultation.fee_charged = consultation.expected_fee
			consultation.currency = consultation.expected_currency
			consultation.scheduled_at = starts_at
			consultation.information_confirmed_at = now
			consultation.save(update_fields=['status', 'fee_charged', 'currency', 'scheduled_at', 'information_confirmed_at'])
			appointment = Appointment.objects.create(
				consultation=consultation, patient=request.user, slot=None, slot_time=starts_at,
				status=Appointment.Status.AWAITING_PAYMENT,
			)
		return Response(AppointmentSerializer(appointment).data, status=201)

	@extend_schema(tags=['Mobile scheduling'], summary='My appointments', responses=AppointmentSerializer(many=True))
	def get(self, request):
		queryset = Appointment.objects.filter(patient=request.user).select_related('consultation', 'doctor__doctor_profile').order_by('-created_at')
		page = self.paginate_queryset(queryset)
		return self.get_paginated_response(AppointmentSerializer(page, many=True).data)


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
			"The doctor must be active and verified, and a general physician for general bookings or of the booking's "
			"speciality. The doctor's own consultation_fee does not matter: the patient paid the fixed category fee. "
			'400 if the doctor already has another unfinished appointment at the same time; once that consultation is completed the '
			'doctor can be assigned another patient at that time. The doctor gets a "New appointment" notification. If the doctor opened an availability slot '
			'at that time in the doctor app, it is linked (shown as booked there).'
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
			profile = get_object_or_404(doctors, user_id=serializer.validated_data['doctor_id'])
			# A doctor sees one patient per 15-minute time; once that consultation is completed the doctor can take another.
			if Appointment.objects.filter(doctor=profile.user, slot_time=appointment.slot_time).exclude(pk=appointment.pk).exclude(status__in=FREED_STATUSES).exists():
				raise serializers.ValidationError('Doctor already has an appointment at this time.')
			# Link the doctor's own free slot at this time, if any, so the doctor app shows it as booked.
			slot = AppointmentSlot.objects.select_for_update().filter(
				doctor=profile.user, starts_at=appointment.slot_time, is_active=True,
			).first()
			if slot is not None and slot.appointments.exclude(pk=appointment.pk).exclude(status__in=FREED_STATUSES).count() >= slot.capacity:
				slot = None
			appointment.slot = slot
			appointment.doctor = profile.user
			update_fields = ['doctor', 'slot'] + appointment.set_status(Appointment.Status.CONFIRMED)
			appointment.save(update_fields=update_fields)
			appointment.consultation.doctor = profile.user
			appointment.consultation.save(update_fields=['doctor'])
			notify_appointment(appointment, Notification.Kind.DOCTOR_ASSIGNED)
			notify_doctor(appointment, Notification.Kind.APPOINTMENT_ASSIGNED)
		return Response(AppointmentSerializer(appointment).data)


class ConfirmCompletionView(generics.GenericAPIView):
	permission_classes = [IsAdminUser]
	serializer_class = AppointmentSerializer

	@extend_schema(
		tags=['Staff matching'], summary='Staff only: confirm a consultation the doctor marked completed',
		description='Records which staff member confirmed it and when (shown to the doctor as `completion_confirmed`). 400 unless the appointment is completed; repeating it is harmless.',
		request=None, responses=AppointmentSerializer,
		examples=[OpenApiExample('Confirmed', response_only=True, value={**APPOINTMENT_EXAMPLE, 'status': 'completed', 'status_label': 'Completed', 'doctor': 7, 'doctor_name': 'Dr. Ananya Sharma', 'doctor_specialization': 'General Physician', 'payment_status': 'success'})],
	)
	def post(self, request, appointment_id):
		with transaction.atomic():
			appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id)
			if appointment.status != Appointment.Status.COMPLETED:
				raise serializers.ValidationError('Only completed consultations can be confirmed.')
			if appointment.completion_confirmed_at is None:
				appointment.completion_confirmed_at = timezone.now()
				appointment.completion_confirmed_by = request.user
				appointment.save(update_fields=['completion_confirmed_at', 'completion_confirmed_by'])
		return Response(AppointmentSerializer(appointment).data)
