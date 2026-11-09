"""Doctor mobile app: day schedule, appointment details, completion, call logs and earnings."""
import json
from datetime import time, timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.views import NoStoreResponseMixin
from apps.consultations.models import Consultation
from apps.consultations.doctor_views import IsVerifiedDoctor
from .availability import SLOT_MINUTES, display_date, display_time, local_datetime
from .completion import complete_appointment
from .earnings import PERIODS, doctor_earnings
from .models import Appointment, AppointmentCall

TAG = 'Doctor app: appointments'
AUTH = ' Verified doctors only (403 while Pending Review).'
SCHEDULE_STATUSES = (Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED)
CALL_STATUSES = SCHEDULE_STATUSES
MAX_CALL_METADATA_BYTES = 5000


def ends_at(appointment):
    return appointment.slot_time + timedelta(minutes=SLOT_MINUTES)


def join_opens_at(appointment):
    return appointment.slot_time - timedelta(minutes=settings.CONSULTATION_JOIN_EARLY_MINUTES)


def can_join(appointment):
    return appointment.status == Appointment.Status.CONFIRMED and timezone.now() >= join_opens_at(appointment)


def doctor_appointments(user):
    return Appointment.objects.filter(doctor=user, status__in=SCHEDULE_STATUSES).select_related('consultation', 'patient')


class DoctorScheduleItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    appointment_number = serializers.CharField(help_text='Booking ID, e.g. APT-00018')
    consultation_id = serializers.IntegerField()
    patient_name = serializers.CharField()
    title = serializers.CharField(help_text='e.g. General Consultation or Skin Consultation')
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(help_text='Every appointment is 15 minutes')
    time_display = serializers.CharField(help_text='e.g. 10:30 AM - 10:45 AM')
    mode = serializers.ChoiceField(choices=Consultation.Mode.choices)
    mode_label = serializers.CharField()
    status = serializers.ChoiceField(choices=[(status.value, status.label) for status in SCHEDULE_STATUSES])
    can_join = serializers.BooleanField(
        help_text='true from 5 minutes before the start until you mark the appointment completed',
    )

    def to_representation(self, appointment):
        consultation = appointment.consultation
        return super().to_representation({
            'id': appointment.pk, 'appointment_number': f'APT-{appointment.pk:05d}', 'consultation_id': consultation.pk,
            'patient_name': consultation.patient_name, 'title': consultation.title,
            'starts_at': appointment.slot_time, 'ends_at': ends_at(appointment),
            'time_display': f'{display_time(appointment.slot_time)} - {display_time(ends_at(appointment))}',
            'mode': consultation.mode, 'mode_label': consultation.get_mode_display(), 'status': appointment.status,
            'can_join': can_join(appointment),
        })


class AppointmentCallSerializer(serializers.ModelSerializer):
    mode = serializers.ChoiceField(choices=Consultation.Mode.choices, required=False, allow_blank=True)
    duration_minutes = serializers.SerializerMethodField(help_text='duration_seconds rounded up to whole minutes')

    class Meta:
        model = AppointmentCall
        fields = [
            'id', 'mode', 'provider', 'external_call_id', 'started_at', 'ended_at', 'duration_seconds',
            'duration_minutes', 'end_reason', 'metadata', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'duration_minutes', 'created_at', 'updated_at']

    def get_duration_minutes(self, obj) -> int | None:
        if obj.duration_seconds is None:
            return None
        return -(-obj.duration_seconds // 60)

    def validate_metadata(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Send a JSON object.')
        if len(json.dumps(value)) > MAX_CALL_METADATA_BYTES:
            raise serializers.ValidationError('Metadata is too large.')
        return value

    def validate(self, attrs):
        unsupported = set(self.initial_data) - set(self.fields)
        if unsupported:
            raise serializers.ValidationError({field: 'Unknown field.' for field in sorted(unsupported)})
        started = attrs.get('started_at', getattr(self.instance, 'started_at', None))
        ended = attrs.get('ended_at', getattr(self.instance, 'ended_at', None))
        if started and ended:
            if ended < started:
                raise serializers.ValidationError({'ended_at': 'Call end must be after its start.'})
            if 'duration_seconds' not in attrs and ('started_at' in attrs or 'ended_at' in attrs):
                attrs['duration_seconds'] = int((ended - started).total_seconds())
        return attrs


class AppointmentPatientSerializer(serializers.Serializer):
    name = serializers.CharField()
    age = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField(help_text='male, female, other, prefer_not_to_say or empty')
    gender_label = serializers.CharField()
    phone_number = serializers.CharField(help_text='Number to call the patient on')


class DoctorAppointmentDetailSerializer(DoctorScheduleItemSerializer):
    date_display = serializers.CharField(help_text='e.g. 18 Oct 2026')
    fee = serializers.IntegerField(help_text='Amount the patient paid, whole currency units')
    currency = serializers.CharField()
    fee_display = serializers.CharField()
    patient = AppointmentPatientSerializer()
    chief_complaint = serializers.CharField(help_text='Disease - type - variant chosen by the patient')
    condition_details = serializers.CharField(help_text='Symptoms / reason in the patient\'s words')
    symptoms = serializers.CharField()
    duration_value = serializers.IntegerField(allow_null=True)
    duration_unit = serializers.CharField()
    ongoing_medication = serializers.BooleanField(allow_null=True)
    treatment_details = serializers.CharField()
    join_opens_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    completion_confirmed = serializers.BooleanField(help_text='true once our staff confirmed the completed consultation')
    calls = AppointmentCallSerializer(many=True)

    def to_representation(self, appointment):
        from apps.notifications.service import money

        consultation = appointment.consultation
        data = DoctorScheduleItemSerializer(appointment).data
        gender_choices = dict(consultation._meta.get_field('patient_gender').choices)
        data.update({
            'date_display': display_date(appointment.slot_time),
            'fee': consultation.fee_charged, 'currency': consultation.currency,
            'fee_display': money(consultation.fee_charged, consultation.currency),
            'patient': {
                'name': consultation.patient_name, 'age': consultation.patient_age,
                'gender': consultation.patient_gender, 'gender_label': gender_choices.get(consultation.patient_gender, ''),
                'phone_number': consultation.patient_phone or appointment.patient.phone_number,
            },
            'chief_complaint': consultation.chief_complaint, 'condition_details': consultation.condition_details,
            'symptoms': consultation.symptoms, 'duration_value': consultation.duration_value,
            'duration_unit': consultation.duration_unit, 'ongoing_medication': consultation.ongoing_medication,
            'treatment_details': consultation.treatment_details,
            'join_opens_at': serializers.DateTimeField().to_representation(join_opens_at(appointment)),
            'completed_at': serializers.DateTimeField().to_representation(appointment.completed_at) if appointment.completed_at else None,
            'completion_confirmed': appointment.completion_confirmed_at is not None,
            'calls': AppointmentCallSerializer(appointment.calls.all(), many=True).data,
        })
        return data


class DoctorAppointmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['completed'], help_text='Only "completed" can be set by the doctor')


class ScheduleQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False, help_text='YYYY-MM-DD, India time. Default today.')


class EarningsQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=PERIODS, default='daily')
    date = serializers.DateField(required=False, help_text='Any day inside the period. Default today. Use previous_date / next_date for the arrows.')


class ChartBucketSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.IntegerField()
    count = serializers.IntegerField()


class ModeEarningsSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=Consultation.Mode.choices)
    label = serializers.CharField()
    amount = serializers.IntegerField()
    amount_display = serializers.CharField()
    count = serializers.IntegerField()
    share_percent = serializers.FloatField(help_text='Share of total_earned, for the bar width')


class OtherCurrencySerializer(serializers.Serializer):
    currency = serializers.CharField()
    amount = serializers.IntegerField()
    count = serializers.IntegerField()


class EarningsSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=PERIODS)
    label = serializers.CharField(help_text='e.g. "18 Oct 2026", "October 2026" or "FY 2026-27"')
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_current = serializers.BooleanField()
    previous_date = serializers.DateField()
    next_date = serializers.DateField(allow_null=True, help_text='null when the next period is in the future (disable the arrow)')
    currency = serializers.CharField()
    total_earned = serializers.IntegerField()
    total_earned_display = serializers.CharField()
    consultations_count = serializers.IntegerField()
    average_per_consultation = serializers.IntegerField()
    average_display = serializers.CharField()
    chart = ChartBucketSerializer(many=True, help_text='daily: 12 two-hour buckets; monthly: one per day; financial_year: Apr to Mar')
    by_mode = ModeEarningsSerializer(many=True)
    other_currencies = OtherCurrencySerializer(many=True, help_text='Completed consultations paid in other currencies (not in the INR totals)')


SCHEDULE_ITEM_EXAMPLE = {
    'id': 18, 'appointment_number': 'APT-00018', 'consultation_id': 41, 'patient_name': 'Rahul Sharma',
    'title': 'General Consultation', 'starts_at': '2026-10-18T10:30:00+05:30', 'ends_at': '2026-10-18T10:45:00+05:30',
    'time_display': '10:30 AM - 10:45 AM', 'mode': 'video', 'mode_label': 'Video Call', 'status': 'confirmed', 'can_join': True,
}
CALL_EXAMPLE = {
    'id': 5, 'mode': 'video', 'provider': 'agora', 'external_call_id': 'apt-18-room', 'started_at': '2026-10-18T10:31:00+05:30',
    'ended_at': '2026-10-18T10:43:30+05:30', 'duration_seconds': 750, 'duration_minutes': 13, 'end_reason': 'doctor_ended',
    'metadata': {'network': 'wifi'}, 'created_at': '2026-10-18T10:31:00+05:30', 'updated_at': '2026-10-18T10:43:31+05:30',
}
DETAIL_EXAMPLE = {
    **SCHEDULE_ITEM_EXAMPLE, 'date_display': '18 Oct 2026', 'fee': 200, 'currency': 'INR', 'fee_display': '\u20b9200',
    'patient': {'name': 'Rahul Sharma', 'age': 35, 'gender': 'male', 'gender_label': 'Male', 'phone_number': '+919876543210'},
    'chief_complaint': 'Fever - Viral Fever', 'condition_details': 'Fever and sore throat since 3 days',
    'symptoms': 'Fever and sore throat since 3 days', 'duration_value': 3, 'duration_unit': 'days',
    'ongoing_medication': False, 'treatment_details': '', 'join_opens_at': '2026-10-18T10:25:00+05:30',
    'completed_at': None, 'completion_confirmed': False, 'calls': [],
}
COMPLETED_EXAMPLE = {
    **DETAIL_EXAMPLE, 'status': 'completed', 'can_join': False, 'completed_at': '2026-10-18T10:44:00+05:30', 'calls': [CALL_EXAMPLE],
}


def mode_entry(mode, label, amount, count, share):
    return {'mode': mode, 'label': label, 'amount': amount, 'amount_display': f'\u20b9{amount:,}', 'count': count, 'share_percent': share}


EARNINGS_EXAMPLE = {
    'period': 'monthly', 'label': 'October 2026', 'start_date': '2026-10-01', 'end_date': '2026-10-31', 'is_current': True,
    'previous_date': '2026-09-01', 'next_date': None, 'currency': 'INR', 'total_earned': 4600,
    'total_earned_display': '\u20b94,600', 'consultations_count': 20, 'average_per_consultation': 230, 'average_display': '\u20b9230',
    'chart': [{'label': '1', 'amount': 400, 'count': 2}, {'label': '2', 'amount': 0, 'count': 0}],
    'by_mode': [
        mode_entry('video', 'Video Call', 3000, 13, 65.2), mode_entry('audio', 'Audio Call', 1200, 5, 26.1),
        mode_entry('chat', 'Chat', 400, 2, 8.7),
    ],
    'other_currencies': [],
}


class DoctorScheduleView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = DoctorScheduleItemSerializer
    pagination_class = None

    @extend_schema(
        tags=[TAG], summary='Home timeline: my appointments on a date',
        description=(
            'Confirmed and completed appointments assigned to you on `date` (India time), earliest first. Use the arrows to '
            'change `date`. Open GET /api/v1/doctors/me/appointments/{id}/ on tap.' + AUTH
        ),
        parameters=[ScheduleQuerySerializer], responses=DoctorScheduleItemSerializer(many=True),
        examples=[OpenApiExample('Day', response_only=True, value=[
            SCHEDULE_ITEM_EXAMPLE,
            {**SCHEDULE_ITEM_EXAMPLE, 'id': 19, 'appointment_number': 'APT-00019', 'consultation_id': 44, 'patient_name': 'Priya Verma',
             'starts_at': '2026-10-18T12:00:00+05:30', 'ends_at': '2026-10-18T12:15:00+05:30', 'time_display': '12:00 PM - 12:15 PM',
             'mode': 'audio', 'mode_label': 'Audio Call', 'can_join': False},
        ])],
    )
    def get(self, request):
        query = ScheduleQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data.get('date') or timezone.localdate()
        start = local_datetime(day, time(0))
        appointments = doctor_appointments(request.user).filter(
            slot_time__gte=start, slot_time__lt=local_datetime(day + timedelta(days=1), time(0)),
        ).order_by('slot_time', 'id')
        return Response(DoctorScheduleItemSerializer(appointments, many=True).data)


class DoctorAppointmentDetailView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = DoctorAppointmentDetailSerializer

    def appointment(self, appointment_id, lock=False):
        queryset = doctor_appointments(self.request.user).prefetch_related('calls')
        if lock:
            queryset = queryset.select_for_update(of=('self',))
        return get_object_or_404(queryset, pk=appointment_id)

    @extend_schema(
        tags=[TAG], summary='Appointment details',
        description=(
            'Date, time, mode, booking ID, fee paid, patient name, age, gender, phone and the reason / symptoms. '
            'Show "Join" while `can_join` is true; the app runs the call itself. Write the diagnosis and prescription '
            'with PUT /api/v1/doctors/me/consultations/{consultation_id}/record/.' + AUTH
        ),
        examples=[OpenApiExample('Upcoming video consultation', value=DETAIL_EXAMPLE, response_only=True)],
    )
    def get(self, request, appointment_id):
        return Response(DoctorAppointmentDetailSerializer(self.appointment(appointment_id)).data)

    @extend_schema(
        tags=[TAG], summary='Mark the consultation completed',
        description=(
            'Send `{"status": "completed"}` after the consultation. Allowed for confirmed appointments from 5 minutes before '
            'the start; repeating it is harmless. The patient is notified and our staff then confirm the completion. '
            'Completed consultations count in Earnings.' + AUTH
        ),
        request=DoctorAppointmentStatusSerializer, responses=DoctorAppointmentDetailSerializer,
        examples=[
            OpenApiExample('Complete', request_only=True, value={'status': 'completed'}),
            OpenApiExample('Completed', value=COMPLETED_EXAMPLE, response_only=True),
        ],
    )
    def patch(self, request, appointment_id):
        serializer = DoctorAppointmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            # Lock the consultation before the appointment, the same order as the record PUT, to avoid deadlocks.
            consultation_id = self.appointment(appointment_id).consultation_id
            Consultation.objects.select_for_update().filter(pk=consultation_id).first()
            appointment = self.appointment(appointment_id, lock=True)
            if appointment.status == Appointment.Status.CONFIRMED:
                if timezone.now() < join_opens_at(appointment):
                    raise serializers.ValidationError({'status': 'This consultation has not started yet.'})
                complete_appointment(appointment)
        return Response(DoctorAppointmentDetailSerializer(self.appointment(appointment_id)).data)


class DoctorAppointmentCallListView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = AppointmentCallSerializer

    @extend_schema(
        tags=[TAG], summary='Save call details',
        description=(
            'Optional. Store details of a call or chat the app ran for this appointment. Every field is optional, e.g. send '
            'provider and started_at when the call starts and PATCH ended_at when it ends. duration_seconds is calculated from '
            'started_at and ended_at when not sent. Allowed for confirmed or completed appointments.' + AUTH
        ),
        responses={201: AppointmentCallSerializer},
        examples=[
            OpenApiExample('Call started', request_only=True, value={
                'mode': 'video', 'provider': 'agora', 'external_call_id': 'apt-18-room', 'started_at': '2026-10-18T10:31:00+05:30',
            }),
            OpenApiExample('Saved', value={**CALL_EXAMPLE, 'ended_at': None, 'duration_seconds': None, 'duration_minutes': None,
                                           'end_reason': '', 'metadata': {}}, response_only=True, status_codes=['201']),
        ],
    )
    def post(self, request, appointment_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            appointment = get_object_or_404(
                doctor_appointments(request.user).select_for_update(of=('self',)), pk=appointment_id,
            )
            call = serializer.save(appointment=appointment, created_by=request.user)
        return Response(AppointmentCallSerializer(call).data, status=201)


class DoctorAppointmentCallDetailView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = AppointmentCallSerializer

    @extend_schema(
        tags=[TAG], summary='Update call details (e.g. when the call ends)',
        description='Send only changed fields.' + AUTH,
        examples=[
            OpenApiExample('Call ended', request_only=True, value={'ended_at': '2026-10-18T10:43:30+05:30', 'end_reason': 'doctor_ended'}),
            OpenApiExample('Updated', value=CALL_EXAMPLE, response_only=True),
        ],
    )
    def patch(self, request, appointment_id, call_id):
        with transaction.atomic():
            call = get_object_or_404(
                AppointmentCall.objects.select_for_update().filter(
                    appointment__doctor=request.user, appointment__status__in=CALL_STATUSES, appointment_id=appointment_id,
                ),
                pk=call_id,
            )
            serializer = self.get_serializer(call, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            call = serializer.save()
        return Response(AppointmentCallSerializer(call).data)


class DoctorEarningsView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = EarningsSerializer

    @extend_schema(
        tags=[TAG], summary='Earnings: daily, monthly or financial year',
        description=(
            'What patients paid for your completed consultations in the period (India time), with consultations done, average '
            'per consultation, a chart and the split by Video / Audio / Chat. Financial year is April to March. Use '
            '`previous_date` and `next_date` as `date` for the arrows.' + AUTH
        ),
        parameters=[EarningsQuerySerializer],
        examples=[OpenApiExample('This month', value=EARNINGS_EXAMPLE, response_only=True)],
    )
    def get(self, request):
        query = EarningsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        day = query.validated_data.get('date') or timezone.localdate()
        return Response(EarningsSerializer(doctor_earnings(request.user, query.validated_data['period'], day)).data)
