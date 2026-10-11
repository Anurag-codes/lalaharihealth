from datetime import time

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.payments.models import Payment
from .models import Appointment, AppointmentSlot
from .serializers import (
	AppointmentRequestSerializer, AppointmentSerializer, AppointmentSlotSerializer,
	DoctorAssignmentSerializer, SlotQuerySerializer,
)


class SlotsView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSlotSerializer

	@extend_schema(tags=['Mobile scheduling'], summary='Step 4: available slots for an India-local date', parameters=[SlotQuerySerializer], responses=AppointmentSlotSerializer(many=True))
	def get(self, request):
		query = SlotQuerySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		selected_date = query.validated_data['date']
		slots = AppointmentSlot.objects.filter(is_active=True, starts_at__gt=timezone.now(), starts_at__date=selected_date)
		available = []
		for slot in slots:
			if timezone.localtime(slot.starts_at).time() < time(8):
				continue
			occupied = slot.appointments.exclude(status=Appointment.Status.CANCELLED).count()
			slot.remaining_capacity = max(slot.capacity - occupied, 0)
			if slot.remaining_capacity:
				available.append(slot)
		return Response(self.get_serializer(available, many=True).data)


class AppointmentListCreateView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentRequestSerializer

	@extend_schema(tags=['Mobile scheduling'], summary='Reserve a slot after completing patient details and history', description='Uploads are optional. Fee is server-set to INR 200 for this general consultation flow. Repeating the same draft/slot returns the existing appointment; no second reservation is created. Pending reservations consume capacity until staff cancel them.', responses={201: AppointmentSerializer, 200: AppointmentSerializer})
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		with transaction.atomic():
			consultation = get_object_or_404(Consultation.objects.select_for_update(), pk=data['consultation_id'], patient=request.user)
			existing = Appointment.objects.filter(consultation=consultation).first()
			if existing:
				if existing.slot_id != data['slot_id']:
					raise serializers.ValidationError('This consultation already has an appointment.')
				return Response(AppointmentSerializer(existing).data)
			if consultation.status != Consultation.Status.DRAFT or not consultation.history_completed:
				raise serializers.ValidationError('Complete the draft health-history step before scheduling.')
			if not all([consultation.patient_name, consultation.patient_age is not None, consultation.patient_gender, consultation.patient_phone]):
				raise serializers.ValidationError('Complete patient details before scheduling.')
			slot = get_object_or_404(AppointmentSlot.objects.select_for_update(), pk=data['slot_id'], is_active=True)
			if slot.starts_at <= timezone.now() or timezone.localtime(slot.starts_at).time() < time(8):
				raise serializers.ValidationError('Select a future slot between 08:00 and 23:59 India time.')
			occupied = slot.appointments.exclude(status=Appointment.Status.CANCELLED).count()
			if occupied >= slot.capacity:
				raise serializers.ValidationError('This slot is no longer available. Refresh available slots.')
			consultation.status = Consultation.Status.REQUESTED
			consultation.fee_charged = 200
			consultation.scheduled_at = slot.starts_at
			consultation.save(update_fields=['status', 'fee_charged', 'scheduled_at'])
			appointment = Appointment.objects.create(
				consultation=consultation, patient=request.user, slot=slot, slot_time=slot.starts_at,
				status=Appointment.Status.AWAITING_PAYMENT,
			)
		return Response(AppointmentSerializer(appointment).data, status=201)

	@extend_schema(tags=['Mobile scheduling'], responses=AppointmentSerializer(many=True))
	def get(self, request):
		queryset = Appointment.objects.filter(patient=request.user).select_related('consultation').order_by('-created_at')
		page = self.paginate_queryset(queryset)
		return self.get_paginated_response(AppointmentSerializer(page, many=True).data)


class AppointmentDetailView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AppointmentSerializer

	@extend_schema(tags=['Mobile scheduling'], summary='Poll appointment summary, payment and doctor-matching status')
	def get(self, request, appointment_id):
		appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user)
		return Response(self.get_serializer(appointment).data)


class AssignDoctorView(generics.GenericAPIView):
	permission_classes = [IsAdminUser]
	serializer_class = DoctorAssignmentSerializer

	@extend_schema(tags=['Staff matching'], summary='Staff only: assign a verified doctor to a paid appointment', responses=AppointmentSerializer)
	def post(self, request, appointment_id):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		with transaction.atomic():
			appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=appointment_id)
			if appointment.status != Appointment.Status.FINDING_DOCTOR:
				raise serializers.ValidationError('Only paid appointments awaiting matching can be assigned.')
			if not Payment.objects.filter(consultation=appointment.consultation, status=Payment.Status.SUCCESS).exists():
				raise serializers.ValidationError('Confirmed payment is required.')
			profile = get_object_or_404(
				DoctorProfile.objects.select_for_update(), user_id=serializer.validated_data['doctor_id'], is_active=True,
				user__is_active=True, user__role='doctor', verification_status='verified',
				consultation_fee=appointment.consultation.fee_charged,
			)
			if Appointment.objects.filter(doctor=profile.user, slot_time=appointment.slot_time).exclude(status=Appointment.Status.CANCELLED).exists():
				raise serializers.ValidationError('Doctor already has an appointment at this time.')
			appointment.doctor = profile.user
			appointment.status = Appointment.Status.CONFIRMED
			appointment.save(update_fields=['doctor', 'status'])
			appointment.consultation.doctor = profile.user
			appointment.consultation.save(update_fields=['doctor'])
		return Response(AppointmentSerializer(appointment).data)
