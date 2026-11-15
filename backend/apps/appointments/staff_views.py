"""Staff console APIs: queues, appointment details, eligible doctors and doctor day schedules.

Assigning/rescheduling and completion confirmation use the existing staff endpoints
POST /api/v1/appointments/{id}/assign-doctor/ and /confirm-completion/.
"""
import re
from datetime import time, timedelta

from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.staff_views import IsStaffUser
from apps.accounts.views import NoStoreResponseMixin
from apps.consultations.models import Consultation, ConsultationDocument
from apps.doctors.models import DoctorProfile
from .assignment import FREED_STATUSES, appointment_assignment_doctors
from .availability import DAY_START, LAST_SLOT_START, SLOT_MINUTES, booking_time_error, display_time, local_datetime
from .models import Appointment, AppointmentCall, AppointmentSlot
from .staff_serializers import (
    StaffAppointmentDetailSerializer, StaffAppointmentQuerySerializer, StaffAppointmentSerializer,
    StaffDoctorChoiceQuerySerializer, StaffDoctorChoicesSerializer, StaffDoctorQuerySerializer,
    StaffDoctorScheduleSerializer, StaffDoctorSerializer, StaffPatientUpdateSerializer, StaffScheduleQuerySerializer,
    StaffSummarySerializer, can_edit_patient, doctor_name,
)

TAG = 'Staff console'
PAID_STATUSES = (Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED)
UNPAID_STATUSES = (Appointment.Status.PENDING, Appointment.Status.AWAITING_PAYMENT)
TIME_ORDERED_QUEUES = ('needs_doctor', 'overdue', 'today', 'upcoming')

ITEM_EXAMPLE = {
    'booker_account_deleted': False, 'doctor_account_deleted': False,
    'coupon_code': '', 'free_consultation_doctor': None,
    'id': 18, 'appointment_number': 'APT-00018', 'status': 'finding_doctor', 'status_label': 'Finding doctor',
    'slot_time': '2026-11-16T10:00:00+05:30', 'schedule_date': '2026-11-16', 'schedule_time': '10:00 AM',
    'date_display': '16 Nov 2026', 'patient_name': 'Priya Sharma', 'patient_phone': '+919876543211',
    'patient_relation': 'spouse', 'patient_relation_label': 'Spouse',
    'booker': {'id': 12, 'name': 'Rahul Sharma', 'phone': '+919876543210'},
    'category': {'speciality_id': None, 'name': 'General Physician', 'title': 'General Consultation'},
    'mode': 'video', 'mode_label': 'Video Call', 'doctor': None, 'payment_status': 'success',
    'amount': 200, 'currency': 'INR', 'amount_display': '\u20b9200', 'created_at': '2026-11-15T09:12:00+05:30',
    'is_overdue': False, 'can_assign': True, 'lock_reason': None, 'can_edit_patient': True,
    'needs_completion_confirmation': False,
}
DETAIL_EXAMPLE = {
    **ITEM_EXAMPLE,
    'booker': {**ITEM_EXAMPLE['booker'], 'email': 'rahul@example.com'},
    'consultation_id': 42, 'consultation_status': 'requested', 'chief_complaint': 'Fever - Viral Fever',
    'condition_details': 'High fever since Friday', 'symptoms': 'Fever, body ache', 'duration_display': '3 Days',
    'ongoing_medication': False, 'treatment_details': '', 'patient_age': 33, 'patient_gender': 'female',
    'patient_gender_label': 'Female', 'family_member_id': 4,
    'payment': {
        'id': 9, 'status': 'success', 'method': 'upi', 'amount': 200, 'currency': 'INR',
        'gateway_order_id': 'order_example', 'transaction_id': 'pay_example', 'created_at': '2026-11-15T09:13:00+05:30',
    },
    'timeline': {
        'created_at': '2026-11-15T09:12:00+05:30', 'information_confirmed_at': '2026-11-15T09:12:00+05:30',
        'paid_at': '2026-11-15T09:14:00+05:30', 'doctor_assigned_at': None, 'completed_at': None,
        'completion_confirmed_at': None, 'completion_confirmed_by': None, 'cancelled_at': None,
    },
    'documents': [{
        'id': 3, 'original_name': 'blood_report.pdf', 'uploaded_at': '2026-11-15T09:10:00+05:30',
        'download_path': '/api/v1/staff/appointments/18/documents/3/download/',
    }],
    'calls': [], 'video_room_provisioned': False,
}
DOCTOR_CHOICE_EXAMPLE = {
    'id': 7, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician', 'speciality_name': None,
    'experience_years': 8, 'phone': '+919800000007', 'is_current': False, 'is_available': True,
    'has_open_slot': True, 'conflict': None, 'appointments_that_day': 2,
}
DOCTOR_EXAMPLE = {
    'id': 7, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician', 'speciality': None,
    'phone': '+919800000007', 'experience_years': 8, 'city': 'Delhi', 'upcoming_appointments': 3,
}


def staff_appointments():
    return Appointment.objects.select_related(
        'consultation__speciality', 'consultation__payment', 'patient', 'doctor__doctor_profile', 'video_room',
        'completion_confirmed_by',
    ).prefetch_related(
        Prefetch('calls', queryset=AppointmentCall.objects.order_by('created_at', 'id')),
        Prefetch('consultation__documents', queryset=ConsultationDocument.objects.order_by('uploaded_at', 'id')),
    )


def india_day_bounds(day):
    start = local_datetime(day, time(0))
    return start, start + timedelta(days=1)


def search_filter(text):
    text = text.strip()
    query = Q(pk__in=[])
    match = re.fullmatch(r'(?i)(?:apt-?)?0*(\d{1,9})', text)
    if match:
        query |= Q(pk=int(match.group(1)))
    digits = re.sub(r'[\s()+-]', '', text)
    for term in {text, digits} - {''}:
        query |= (
            Q(consultation__patient_name__icontains=term) | Q(consultation__patient_phone__icontains=term)
            | Q(patient__phone_number__icontains=term) | Q(patient__first_name__icontains=term)
            | Q(patient__last_name__icontains=term) | Q(doctor__first_name__icontains=term)
            | Q(doctor__last_name__icontains=term)
        )
    return query


def speciality_filter(value, field):
    return Q(**{f'{field}__isnull': True}) if value == 'general' else Q(**{f'{field}_id': int(value)})


class StaffSummaryView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffSummarySerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: dashboard counts',
        description='Counts behind each queue of GET /api/v1/staff/appointments/?queue=. India dates.',
        examples=[OpenApiExample('Counts', response_only=True, value={
            'today_date': '2026-11-15', 'needs_doctor': 4, 'overdue': 1, 'today_count': 9,
            'awaiting_payment': 2, 'completion_pending': 3, 'upcoming_confirmed': 12,
        })],
    )
    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()
        start, end = india_day_bounds(today)
        counts = Appointment.objects.aggregate(
            needs_doctor=Count('pk', filter=Q(status=Appointment.Status.FINDING_DOCTOR)),
            overdue=Count('pk', filter=Q(status=Appointment.Status.FINDING_DOCTOR, slot_time__lte=now)),
            today_count=Count('pk', filter=Q(status__in=PAID_STATUSES, slot_time__gte=start, slot_time__lt=end)),
            awaiting_payment=Count('pk', filter=Q(status__in=UNPAID_STATUSES)),
            completion_pending=Count('pk', filter=Q(status=Appointment.Status.COMPLETED, completion_confirmed_at__isnull=True)),
            upcoming_confirmed=Count('pk', filter=Q(
                status=Appointment.Status.CONFIRMED, slot_time__gt=now - timedelta(minutes=SLOT_MINUTES),
            )),
        )
        return Response(self.get_serializer({'today_date': today, **counts}).data)


class StaffAppointmentListView(NoStoreResponseMixin, generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffAppointmentSerializer

    def get_queryset(self):
        query = StaffAppointmentQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        now = timezone.now()
        queryset = staff_appointments()
        queue = params.get('queue')
        if queue == 'needs_doctor':
            queryset = queryset.filter(status=Appointment.Status.FINDING_DOCTOR)
        elif queue == 'overdue':
            queryset = queryset.filter(status=Appointment.Status.FINDING_DOCTOR, slot_time__lte=now)
        elif queue == 'today':
            start, end = india_day_bounds(timezone.localdate())
            queryset = queryset.filter(status__in=PAID_STATUSES, slot_time__gte=start, slot_time__lt=end)
        elif queue == 'awaiting_payment':
            queryset = queryset.filter(status__in=UNPAID_STATUSES)
        elif queue == 'completion_pending':
            queryset = queryset.filter(status=Appointment.Status.COMPLETED, completion_confirmed_at__isnull=True)
        elif queue == 'upcoming':
            queryset = queryset.filter(
                status=Appointment.Status.CONFIRMED, slot_time__gt=now - timedelta(minutes=SLOT_MINUTES),
            )
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('date_from'):
            queryset = queryset.filter(slot_time__gte=india_day_bounds(params['date_from'])[0])
        if params.get('date_to'):
            queryset = queryset.filter(slot_time__lt=india_day_bounds(params['date_to'])[1])
        if params.get('doctor_id'):
            queryset = queryset.filter(doctor_id=params['doctor_id'])
        if params.get('speciality'):
            queryset = queryset.filter(speciality_filter(params['speciality'], 'consultation__speciality'))
        if params.get('q', '').strip():
            queryset = queryset.filter(search_filter(params['q']))
        ordering = params.get('ordering') or ('slot_time' if queue in TIME_ORDERED_QUEUES else '-slot_time')
        return queryset.order_by(ordering, 'id' if not ordering.startswith('-') else '-id')

    @extend_schema(
        tags=[TAG], summary='Staff console: appointments with queues, filters and search',
        description=(
            'Paginated (20 per page, ?page=). Combine queue, status, India date range, doctor, speciality and search. '
            '`can_assign`/`lock_reason` tell whether doctor/time can still be changed through '
            'POST /api/v1/appointments/{id}/assign-doctor/ (which re-checks under database locks).'
        ),
        parameters=[StaffAppointmentQuerySerializer],
        examples=[OpenApiExample('Needs a doctor', response_only=True, value={
            'count': 1, 'next': None, 'previous': None, 'results': [ITEM_EXAMPLE],
        })],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class StaffAppointmentDetailView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffAppointmentDetailSerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: full appointment, case, payment, documents and calls',
        examples=[OpenApiExample('Appointment', response_only=True, value=DETAIL_EXAMPLE)],
        description='Everything staff need before assigning a doctor. Documents download through download_path with staff authentication.',
    )
    def get(self, request, appointment_id):
        appointment = get_object_or_404(staff_appointments(), pk=appointment_id)
        return Response(self.get_serializer(appointment).data)


class StaffPatientUpdateView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffPatientUpdateSerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: correct the patient name, age or gender of a booking',
        description=(
            'Changes only this booking\'s patient snapshot, not the account or family profile. The phone cannot be '
            'changed here because it decides which family member can see the booking in their own app. '
            '400 once the appointment or consultation is completed or cancelled. Returns the updated appointment.'
        ),
        request=StaffPatientUpdateSerializer, responses={200: StaffAppointmentDetailSerializer},
        examples=[
            OpenApiExample('Fix name and age', request_only=True, value={'patient_name': 'Priya Sharma', 'patient_age': 34}),
            OpenApiExample('Updated', response_only=True, value={**DETAIL_EXAMPLE, 'patient_age': 34}),
        ],
    )
    def patch(self, request, appointment_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            snapshot = get_object_or_404(Appointment.objects.only('consultation_id'), pk=appointment_id)
            consultation = Consultation.objects.select_for_update().get(pk=snapshot.consultation_id)
            appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
            appointment.consultation = consultation
            if not can_edit_patient(appointment):
                raise serializers.ValidationError('Patient details of completed or cancelled appointments cannot be changed.')
            for field, value in serializer.validated_data.items():
                setattr(consultation, field, value.strip() if isinstance(value, str) else value)
            if not consultation.patient_name:
                raise serializers.ValidationError({'patient_name': 'This field may not be blank.'})
            consultation.save(update_fields=list(serializer.validated_data))
        appointment = get_object_or_404(staff_appointments(), pk=appointment_id)
        return Response(StaffAppointmentDetailSerializer(appointment).data)


class StaffDoctorChoicesView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffDoctorChoicesSerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: doctors who can take this appointment, with availability',
        description=(
            'Active, verified doctors of the booking category (general physicians for general bookings), current doctor '
            'first, then free doctors. `is_available` is false when the doctor has another unfinished appointment at '
            'starts_at (shown in `conflict`). A starts_at must be a future 15-minute time within 30 days.'
        ),
        parameters=[StaffDoctorChoiceQuerySerializer],
        examples=[OpenApiExample('Doctors', response_only=True, value={
            'starts_at': '2026-11-16T10:00:00+05:30', 'results': [DOCTOR_CHOICE_EXAMPLE],
        })],
    )
    def get(self, request, appointment_id):
        query = StaffDoctorChoiceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        appointment = get_object_or_404(Appointment.objects.select_related('consultation'), pk=appointment_id)
        starts_at = query.validated_data.get('starts_at')
        if starts_at is None:
            starts_at = appointment.slot_time
        else:
            error = booking_time_error(starts_at)
            if error:
                raise serializers.ValidationError({'starts_at': [error]})
        profiles = list(appointment_assignment_doctors(appointment).select_related('user', 'speciality'))
        doctor_ids = [profile.user_id for profile in profiles]
        conflicts = {
            row.doctor_id: row for row in Appointment.objects.filter(doctor_id__in=doctor_ids, slot_time=starts_at)
            .exclude(pk=appointment.pk).exclude(status__in=FREED_STATUSES).only('id', 'doctor_id')
        }
        open_slots = set(AppointmentSlot.objects.filter(
            doctor_id__in=doctor_ids, starts_at=starts_at, is_active=True,
        ).values_list('doctor_id', flat=True))
        start, end = india_day_bounds(timezone.localtime(starts_at).date())
        day_counts = dict(Appointment.objects.filter(
            doctor_id__in=doctor_ids, slot_time__gte=start, slot_time__lt=end,
        ).exclude(status=Appointment.Status.CANCELLED).values('doctor_id').annotate(total=Count('pk')).values_list('doctor_id', 'total'))
        results = []
        for profile in profiles:
            conflict = conflicts.get(profile.user_id)
            results.append({
                'id': profile.user_id, 'name': doctor_name(profile.user), 'specialization': profile.specialization,
                'speciality_name': profile.speciality.name if profile.speciality_id else None,
                'experience_years': profile.experience_years, 'phone': profile.user.phone_number,
                'is_current': profile.user_id == appointment.doctor_id, 'is_available': conflict is None,
                'has_open_slot': profile.user_id in open_slots,
                'conflict': {'appointment_id': conflict.pk, 'appointment_number': f'APT-{conflict.pk:05d}'} if conflict else None,
                'appointments_that_day': day_counts.get(profile.user_id, 0),
            })
        results.sort(key=lambda row: (not row['is_current'], not row['is_available'], not row['has_open_slot'], row['name'].lower()))
        return Response(self.get_serializer({'starts_at': starts_at, 'results': results}).data)


def staff_doctor_profiles():
    return DoctorProfile.objects.filter(
        is_active=True, user__is_active=True, user__role=User.Role.DOCTOR, verification_status='verified',
    )


class StaffDoctorListView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffDoctorSerializer
    pagination_class = None

    @extend_schema(
        tags=[TAG], summary='Staff console: verified doctors by name',
        description='Active, verified doctors sorted by name. Not paginated. Filter by name/phone/specialization and speciality.',
        parameters=[StaffDoctorQuerySerializer], responses=StaffDoctorSerializer(many=True),
        examples=[OpenApiExample('Doctors', response_only=True, value=[DOCTOR_EXAMPLE])],
    )
    def get(self, request):
        query = StaffDoctorQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        now = timezone.now()
        profiles = staff_doctor_profiles().select_related('user', 'speciality').annotate(upcoming=Count(
            'user__appointments_as_doctor', filter=Q(
                user__appointments_as_doctor__status=Appointment.Status.CONFIRMED,
                user__appointments_as_doctor__slot_time__gt=now,
            ),
        ))
        if params.get('speciality'):
            profiles = profiles.filter(speciality_filter(params['speciality'], 'speciality'))
        text = params.get('q', '').strip()
        if text:
            profiles = profiles.filter(
                Q(user__first_name__icontains=text) | Q(user__last_name__icontains=text)
                | Q(user__phone_number__icontains=text) | Q(specialization__icontains=text),
            )
        rows = [{
            'id': profile.user_id, 'name': doctor_name(profile.user), 'specialization': profile.specialization,
            'speciality': {'id': profile.speciality_id, 'name': profile.speciality.name} if profile.speciality_id else None,
            'phone': profile.user.phone_number, 'experience_years': profile.experience_years, 'city': profile.city,
            'upcoming_appointments': profile.upcoming,
        } for profile in profiles]
        rows.sort(key=lambda row: row['name'].lower())
        return Response(self.get_serializer(rows, many=True).data)


class StaffDoctorScheduleView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffDoctorScheduleSerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: one doctor\'s day, every 15 minutes',
        description=(
            '96 times from 00:00 to 23:45 India time, each with the slot the doctor opened in the doctor app (if any) and the '
            'non-cancelled appointment at that time. Use it to pick a free time before assigning.'
        ),
        parameters=[StaffScheduleQuerySerializer],
        examples=[OpenApiExample('Day', response_only=True, value={
            'doctor': {'id': 7, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician'},
            'date': '2026-11-16',
            'times': [
                {'starts_at': '2026-11-16T00:00:00+05:30', 'time_display': '12:00 AM', 'is_past': False,
                 'slot_open': False, 'slot_id': None, 'appointment': None},
                {'starts_at': '2026-11-16T10:00:00+05:30', 'time_display': '10:00 AM', 'is_past': False,
                 'slot_open': True, 'slot_id': 318, 'appointment': {
                     'id': 18, 'appointment_number': 'APT-00018', 'status': 'confirmed', 'patient_name': 'Priya Sharma'}},
            ],
        })],
    )
    def get(self, request, doctor_id):
        query = StaffScheduleQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data['date']
        profile = get_object_or_404(DoctorProfile.objects.select_related('user'), user_id=doctor_id, user__role=User.Role.DOCTOR)
        start, end = india_day_bounds(day)
        slots = {
            slot.starts_at: slot for slot in AppointmentSlot.objects.filter(
                doctor_id=doctor_id, starts_at__gte=start, starts_at__lt=end, is_active=True,
            )
        }
        appointments = {}
        for appointment in Appointment.objects.filter(
            doctor_id=doctor_id, slot_time__gte=start, slot_time__lt=end,
        ).exclude(status=Appointment.Status.CANCELLED).select_related('consultation').order_by('created_at'):
            current = appointments.get(appointment.slot_time)
            # An unfinished appointment takes precedence over a completed one at the same time.
            if current is None or current.status == Appointment.Status.COMPLETED:
                appointments[appointment.slot_time] = appointment
        now = timezone.now()
        first = DAY_START.hour * 60 + DAY_START.minute
        last = LAST_SLOT_START.hour * 60 + LAST_SLOT_START.minute
        times = []
        for minutes in range(first, last + 1, SLOT_MINUTES):
            starts_at = local_datetime(day, time(minutes // 60, minutes % 60))
            slot = slots.get(starts_at)
            appointment = appointments.get(starts_at)
            times.append({
                'starts_at': starts_at, 'time_display': display_time(starts_at), 'is_past': starts_at <= now,
                'slot_open': slot is not None, 'slot_id': slot.pk if slot else None,
                'appointment': {
                    'id': appointment.pk, 'appointment_number': f'APT-{appointment.pk:05d}', 'status': appointment.status,
                    'patient_name': appointment.consultation.patient_name,
                } if appointment else None,
            })
        doctor = {'id': profile.user_id, 'name': doctor_name(profile.user), 'specialization': profile.specialization}
        return Response(self.get_serializer({'doctor': doctor, 'date': day, 'times': times}).data)


class StaffDocumentDownloadView(generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffAppointmentDetailSerializer

    @extend_schema(
        tags=[TAG], summary='Staff console: download a patient document of an appointment',
        description='Streams the private file as an attachment. Files are never public.',
        responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY},
    )
    def get(self, request, appointment_id, document_id):
        appointment = get_object_or_404(Appointment.objects.only('consultation_id'), pk=appointment_id)
        document = get_object_or_404(ConsultationDocument, pk=document_id, consultation_id=appointment.consultation_id)
        response = FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_name)
        response['Cache-Control'] = 'no-store'
        return response
