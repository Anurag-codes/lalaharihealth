from datetime import time, timedelta

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.consultations.doctor_views import IsVerifiedDoctor
from .availability import LAST_SLOT_START, SLOT_MINUTES, local_datetime
from .models import Appointment, AppointmentSlot
from .serializers import DoctorAvailabilityResultSerializer, DoctorAvailabilitySerializer, DoctorSlotSerializer, SlotQuerySerializer

SLOT_EXAMPLE = {
    'id': 318, 'starts_at': '2026-10-18T19:00:00+05:30', 'date': '2026-10-18', 'time_display': '07:00 PM',
    'is_active': True, 'is_booked': False, 'appointment_id': None,
}


def doctor_slots(user):
    return AppointmentSlot.objects.filter(doctor=user).prefetch_related(
        Prefetch('appointments', queryset=Appointment.objects.only('id', 'status', 'slot_id')),
    ).order_by('starts_at')


class DoctorSlotListCreateView(generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = DoctorAvailabilitySerializer
    pagination_class = None

    @extend_schema(
        tags=['Doctor schedule'], summary='Doctor app: my time slots for a date',
        parameters=[SlotQuerySerializer], responses=DoctorSlotSerializer(many=True),
        examples=[OpenApiExample('My slots', response_only=True, value=[
            SLOT_EXAMPLE, {**SLOT_EXAMPLE, 'id': 319, 'starts_at': '2026-10-18T19:15:00+05:30', 'time_display': '07:15 PM', 'is_booked': True, 'appointment_id': 12345},
        ])],
    )
    def get(self, request):
        query = SlotQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start = local_datetime(query.validated_data['date'], time(0))
        slots = doctor_slots(request.user).filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1))
        return Response(DoctorSlotSerializer(slots, many=True).data)

    @extend_schema(
        tags=['Doctor schedule'], summary='Doctor app: open 15-minute slots from a chosen time',
        description=(
            'Creates 15-minute slots on `date` starting at `start_time` until `end_time` (or until 23:45, the last slot of the day). '
            'Patients see these in Schedule Appointment. Past times and slots that already exist are skipped. Verified doctors only.'
        ),
        request=DoctorAvailabilitySerializer, responses={201: DoctorAvailabilityResultSerializer},
        examples=[
            OpenApiExample('From 7 PM to end of day', request_only=True, value={'date': '2026-10-18', 'start_time': '19:00'}),
            OpenApiExample('Evening window', request_only=True, value={'date': '2026-10-18', 'start_time': '19:00', 'end_time': '21:00'}),
            OpenApiExample('Created', response_only=True, status_codes=['201'], value={'created_count': 8, 'slots': [SLOT_EXAMPLE]}),
        ],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        current = local_datetime(data['date'], data['start_time'])
        last = local_datetime(data['date'], LAST_SLOT_START)
        if data['end_time'] is not None:
            last = min(last, local_datetime(data['date'], data['end_time']) - timedelta(minutes=SLOT_MINUTES))
        now = timezone.now()
        created = []
        with transaction.atomic():
            existing = set(AppointmentSlot.objects.filter(
                doctor=request.user, starts_at__gte=current, starts_at__lte=last,
            ).values_list('starts_at', flat=True))
            reactivate = AppointmentSlot.objects.filter(
                doctor=request.user, starts_at__gte=max(current, now), starts_at__lte=last, is_active=False,
            )
            reactivated_ids = list(reactivate.values_list('pk', flat=True))
            reactivate.update(is_active=True)
            new_slots = []
            while current <= last:
                if current > now and current not in existing:
                    new_slots.append(AppointmentSlot(doctor=request.user, starts_at=current, capacity=1))
                current += timedelta(minutes=SLOT_MINUTES)
            created = AppointmentSlot.objects.bulk_create(new_slots)
        if not created and not reactivated_ids:
            raise serializers.ValidationError('No new future slots in this time range.')
        start = local_datetime(data['date'], data['start_time'])
        slots = doctor_slots(request.user).filter(starts_at__gte=start, starts_at__lte=last)
        return Response({'created_count': len(created) + len(reactivated_ids), 'slots': DoctorSlotSerializer(slots, many=True).data}, status=201)


class DoctorSlotDetailView(generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = DoctorSlotSerializer

    @extend_schema(tags=['Doctor schedule'], summary='Doctor app: remove one of my slots', description='Only slots without an active booking can be removed.', responses={204: None})
    def delete(self, request, slot_id):
        with transaction.atomic():
            slot = get_object_or_404(AppointmentSlot.objects.select_for_update(), pk=slot_id, doctor=request.user)
            appointments = slot.appointments.all()
            if appointments.exclude(status=Appointment.Status.CANCELLED).exists():
                raise serializers.ValidationError('This slot has a booking and cannot be removed.')
            if appointments.exists():
                slot.is_active = False
                slot.save(update_fields=['is_active'])
            else:
                slot.delete()
        return Response(status=204)
