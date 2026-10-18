"""Home screen and "My Cases" (booking tracker) for the patient app."""
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_field
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.views import IsPatient, NoStoreResponseMixin
from apps.appointments.availability import SLOT_MINUTES, display_date, display_time
from apps.appointments.models import Appointment
from apps.consultations.models import Consultation
from apps.consultations.serializers import relation_label
from apps.doctors.models import Speciality
from apps.doctors.serializers import SpecialitySerializer
from apps.notifications.models import Notification
from apps.pricing.serializers import PricingQuerySerializer
from apps.pricing.service import format_amount, resolve_pricing

DEFAULT_GREETING_NAME = 'LalaHari Health Member'
ACTIVE_STAGES = ('draft', 'awaiting_payment', 'finding_doctor', 'confirmed')
CLOSED_STAGES = ('completed', 'cancelled')
STAGE_LABELS = {
    'draft': 'Draft', 'awaiting_payment': 'Awaiting payment', 'finding_doctor': 'Finding doctor',
    'confirmed': 'Confirmed', 'completed': 'Completed', 'cancelled': 'Cancelled',
}
TRACKER_STEPS = [
    ('submitted', 'Case submitted'), ('paid', 'Payment done'),
    ('doctor_assigned', 'Doctor assigned'), ('completed', 'Consultation completed'),
]


def doctor_name(appointment):
    if appointment is None or appointment.status not in {Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED}:
        return None
    doctor = appointment.doctor
    return f'Dr. {doctor.get_full_name() or doctor.username}' if doctor else None


def doctor_specialization(appointment):
    if doctor_name(appointment) is None:
        return None
    profile = getattr(appointment.doctor, 'doctor_profile', None)
    return profile.specialization if profile else None


def case_stage(consultation, appointment):
    if consultation.status == Consultation.Status.CANCELLED or (appointment and appointment.status == Appointment.Status.CANCELLED):
        return 'cancelled'
    if consultation.status == Consultation.Status.COMPLETED or (appointment and appointment.status == Appointment.Status.COMPLETED):
        return 'completed'
    if appointment is None:
        return 'draft'
    if appointment.status in {Appointment.Status.PENDING, Appointment.Status.AWAITING_PAYMENT}:
        return 'awaiting_payment'
    return appointment.status


def next_action(consultation, stage):
    if stage == 'draft':
        return 'select_slot' if consultation.history_completed else 'complete_history'
    return {
        'awaiting_payment': 'pay', 'finding_doctor': 'wait_for_doctor',
        'confirmed': 'join_consultation', 'completed': 'view_record',
    }.get(stage)


def tracker(consultation, appointment, stage):
    reached = {
        'submitted': appointment is not None,
        'paid': stage in {'finding_doctor', 'confirmed', 'completed'},
        'doctor_assigned': stage in {'confirmed', 'completed'},
        'completed': stage == 'completed',
    }
    timestamps = {
        'submitted': consultation.information_confirmed_at,
        'paid': appointment.paid_at if appointment else None,
        'doctor_assigned': appointment.doctor_assigned_at if appointment else None,
        'completed': appointment.completed_at if appointment else None,
    }
    return [
        {'key': key, 'label': label, 'done': bool(reached[key] or timestamps[key]), 'at': timestamps[key]}
        for key, label in TRACKER_STEPS
    ]


def case_queryset(user):
    return (
        Consultation.objects.filter(patient=user)
        .select_related('speciality', 'appointment__doctor__doctor_profile')
        .order_by('-created_at')
    )


def stage_filter(stages):
    """ORM filter matching case_stage() for the given stages."""
    cancelled = Q(status=Consultation.Status.CANCELLED) | Q(appointment__status=Appointment.Status.CANCELLED)
    completed = ~cancelled & (Q(status=Consultation.Status.COMPLETED) | Q(appointment__status=Appointment.Status.COMPLETED))
    closed = cancelled | completed
    parts = {
        'cancelled': cancelled,
        'completed': completed,
        'draft': ~closed & Q(appointment__isnull=True),
        'awaiting_payment': ~closed & Q(appointment__status__in=[Appointment.Status.PENDING, Appointment.Status.AWAITING_PAYMENT]),
        'finding_doctor': ~closed & Q(appointment__status=Appointment.Status.FINDING_DOCTOR),
        'confirmed': ~closed & Q(appointment__status=Appointment.Status.CONFIRMED),
    }
    query = Q(pk__in=[])
    for stage in stages:
        query |= parts[stage]
    return query


class TrackerStepSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=[key for key, _ in TRACKER_STEPS])
    label = serializers.CharField()
    done = serializers.BooleanField()
    at = serializers.DateTimeField(allow_null=True)


class CaseScheduleSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    date = serializers.CharField(help_text='e.g. "18 Oct 2026"')
    time = serializers.CharField(help_text='e.g. "10:00 AM"')


class CaseSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField(source='pk')
    appointment_id = serializers.SerializerMethodField()
    appointment_number = serializers.SerializerMethodField()
    title = serializers.CharField(help_text='"General Consultation" or the speciality title')
    chief_complaint = serializers.SerializerMethodField()
    speciality = serializers.SerializerMethodField()
    patient_name = serializers.CharField()
    patient_relation = serializers.CharField()
    patient_relation_label = serializers.SerializerMethodField()
    mode = serializers.CharField()
    mode_label = serializers.SerializerMethodField(help_text='Always "Online"')
    schedule = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField(help_text='Shown once a doctor is confirmed')
    doctor_specialization = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField(help_text='Whole currency units')
    currency = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    next_action = serializers.SerializerMethodField(
        help_text='complete_history, select_slot, pay, wait_for_doctor, join_consultation, view_record or null',
    )
    tracker = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def _appointment(self, obj):
        return getattr(obj, 'appointment', None)

    def get_appointment_id(self, obj) -> int | None:
        appointment = self._appointment(obj)
        return appointment.pk if appointment else None

    def get_appointment_number(self, obj) -> str | None:
        appointment = self._appointment(obj)
        return f'APT-{appointment.pk:05d}' if appointment else None

    def get_chief_complaint(self, obj) -> str:
        return obj.chief_complaint or obj.title

    def get_speciality(self, obj) -> str | None:
        return obj.speciality.name if obj.speciality_id else None

    def get_patient_relation_label(self, obj) -> str:
        return relation_label(obj.patient_relation)

    def get_mode_label(self, obj) -> str:
        return 'Online'

    @extend_schema_field(CaseScheduleSerializer(allow_null=True))
    def get_schedule(self, obj):
        appointment = self._appointment(obj)
        starts_at = appointment.slot_time if appointment else None
        if starts_at is None:
            return None
        return {'starts_at': starts_at, 'date': display_date(starts_at), 'time': display_time(starts_at)}

    def get_doctor_name(self, obj) -> str | None:
        return doctor_name(self._appointment(obj))

    def get_doctor_specialization(self, obj) -> str | None:
        return doctor_specialization(self._appointment(obj))

    def get_amount(self, obj) -> int:
        return obj.fee_charged if self._appointment(obj) else obj.expected_fee

    def get_currency(self, obj) -> str:
        return obj.currency if self._appointment(obj) else obj.expected_currency

    def get_stage(self, obj) -> str:
        return case_stage(obj, self._appointment(obj))

    def get_status_label(self, obj) -> str:
        return STAGE_LABELS[self.get_stage(obj)]

    def get_next_action(self, obj) -> str | None:
        return next_action(obj, self.get_stage(obj))

    @extend_schema_field(TrackerStepSerializer(many=True))
    def get_tracker(self, obj):
        return tracker(obj, self._appointment(obj), self.get_stage(obj))


class UpcomingAppointmentSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField()
    consultation_id = serializers.IntegerField()
    title = serializers.CharField(help_text='"General Consultation", "Skin Consultation", ...')
    patient_name = serializers.CharField()
    doctor_name = serializers.CharField(allow_null=True, help_text='null while a doctor is being matched')
    doctor_specialization = serializers.CharField(allow_null=True)
    starts_at = serializers.DateTimeField()
    day = serializers.CharField(help_text='Date badge day, e.g. "18"')
    month = serializers.CharField(help_text='Date badge month, e.g. "OCT"')
    time = serializers.CharField(help_text='e.g. "10:00 AM"')
    mode = serializers.CharField()
    mode_label = serializers.CharField(help_text='Always "Online"')
    status = serializers.CharField(help_text='finding_doctor or confirmed')
    status_label = serializers.CharField()


class GeneralCareSerializer(serializers.Serializer):
    title = serializers.CharField()
    country_code = serializers.CharField(help_text='Send as country_code in booking step 1')
    fee = serializers.IntegerField(help_text='Whole currency units')
    currency = serializers.CharField()
    fee_display = serializers.CharField(help_text='e.g. "\u20b9200" or "$10"')
    match_within_minutes = serializers.IntegerField(help_text='"Matched within 30 minutes"')


class HomeSerializer(serializers.Serializer):
    greeting_name = serializers.CharField()
    photo_url = serializers.URLField(allow_null=True)
    preferred_language = serializers.CharField(help_text='en or hi (the EN toggle). Change with PATCH /api/v1/patients/profile/')
    unread_notification_count = serializers.IntegerField(help_text='Show the red dot on the bell when > 0')
    support_phone = serializers.CharField(help_text='"Prefer to book by call?"')
    general_care = GeneralCareSerializer()
    specialities = SpecialitySerializer(many=True, help_text='"Expert Care" card. Empty list = hide Book Specialist')
    upcoming_appointments = UpcomingAppointmentSerializer(many=True)
    active_case_count = serializers.IntegerField(help_text='Badge for "My Cases"')


UPCOMING_EXAMPLE = {
    'appointment_id': 19, 'consultation_id': 42, 'title': 'General Consultation', 'patient_name': 'Rahul Sharma',
    'doctor_name': 'Dr. Ananya Sharma', 'doctor_specialization': 'General Physician',
    'starts_at': '2026-10-18T10:00:00+05:30', 'day': '18', 'month': 'OCT', 'time': '10:00 AM',
    'mode': 'video', 'mode_label': 'Online', 'status': 'confirmed', 'status_label': 'Confirmed',
}
HOME_EXAMPLE = {
    'greeting_name': 'Rahul Sharma', 'photo_url': 'https://api.lalaharihealth.com/api/v1/patients/profile/photo/',
    'preferred_language': 'en', 'unread_notification_count': 2, 'support_phone': '+911800123456',
    'general_care': {
        'title': 'General Consultation', 'country_code': 'IN', 'fee': 200, 'currency': 'INR', 'fee_display': '\u20b9200',
        'match_within_minutes': 30,
    },
    'specialities': [
        {'id': 1, 'name': 'Cardiology', 'slug': 'cardiology', 'short_name': 'Cardio', 'title': 'Cardiology Consultation',
         'description': 'Heart and blood pressure', 'fee': 500, 'currency': 'INR', 'fee_display': '\u20b9500'},
        {'id': 3, 'name': 'Dermatology', 'slug': 'dermatology', 'short_name': 'Derma', 'title': 'Skin Consultation',
         'description': 'Skin, hair and nails', 'fee': 400, 'currency': 'INR', 'fee_display': '\u20b9400'},
    ],
    'upcoming_appointments': [
        UPCOMING_EXAMPLE,
        {**UPCOMING_EXAMPLE, 'appointment_id': 23, 'consultation_id': 47, 'title': 'Skin Consultation',
         'doctor_name': 'Dr. Vikram Mehta', 'doctor_specialization': 'Dermatologist',
         'starts_at': '2026-10-21T16:30:00+05:30', 'day': '21', 'time': '04:30 PM'},
    ],
    'active_case_count': 3,
}
CASE_EXAMPLE = {
    'consultation_id': 42, 'appointment_id': 19, 'appointment_number': 'APT-00019', 'title': 'General Consultation',
    'chief_complaint': 'Headache - Cluster Headache - Chronic', 'speciality': None,
    'patient_name': 'Rahul Sharma', 'patient_relation': 'self', 'patient_relation_label': 'You',
    'mode': 'video', 'mode_label': 'Online',
    'schedule': {'starts_at': '2026-10-18T10:00:00+05:30', 'date': '18 Oct 2026', 'time': '10:00 AM'},
    'doctor_name': None, 'doctor_specialization': None, 'amount': 200, 'currency': 'INR',
    'stage': 'finding_doctor', 'status_label': 'Finding doctor', 'next_action': 'wait_for_doctor',
    'tracker': [
        {'key': 'submitted', 'label': 'Case submitted', 'done': True, 'at': '2026-10-16T18:20:00+05:30'},
        {'key': 'paid', 'label': 'Payment done', 'done': True, 'at': '2026-10-16T18:22:41+05:30'},
        {'key': 'doctor_assigned', 'label': 'Doctor assigned', 'done': False, 'at': None},
        {'key': 'completed', 'label': 'Consultation completed', 'done': False, 'at': None},
    ],
    'created_at': '2026-10-16T18:05:00+05:30',
}
DRAFT_CASE_EXAMPLE = {
    **CASE_EXAMPLE, 'consultation_id': 47, 'appointment_id': None, 'appointment_number': None,
    'title': 'Skin Consultation', 'chief_complaint': 'Skin Consultation', 'speciality': 'Dermatology', 'schedule': None,
    'amount': 400, 'stage': 'draft', 'status_label': 'Draft', 'next_action': 'complete_history',
    'tracker': [{**step, 'done': False, 'at': None} for step in CASE_EXAMPLE['tracker']],
}


def upcoming_appointments(user, limit=10):
    # Keep a consultation on the list until its 15-minute slot has ended.
    since = timezone.now() - timedelta(minutes=SLOT_MINUTES)
    appointments = (
        Appointment.objects.filter(
            patient=user, slot_time__gt=since,
            status__in=[Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED],
        )
        .select_related('consultation__speciality', 'doctor__doctor_profile')
        .order_by('slot_time')[:limit]
    )
    items = []
    for appointment in appointments:
        consultation = appointment.consultation
        local = timezone.localtime(appointment.slot_time)
        items.append({
            'appointment_id': appointment.pk, 'consultation_id': consultation.pk, 'title': consultation.title,
            'patient_name': consultation.patient_name,
            'doctor_name': doctor_name(appointment), 'doctor_specialization': doctor_specialization(appointment),
            'starts_at': appointment.slot_time, 'day': local.strftime('%d'), 'month': local.strftime('%b').upper(),
            'time': display_time(appointment.slot_time), 'mode': consultation.mode, 'mode_label': 'Online',
            'status': appointment.status, 'status_label': appointment.get_status_display(),
        })
    return items


class PatientHomeView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = HomeSerializer

    @extend_schema(
        tags=['Home'], summary='Home screen data',
        description=(
            'Everything on the home screen in one call: Welcome Back name and photo, app language, bell red dot, '
            'General Physician card (fee in local currency for the lat/lng or country sent, else India \u20b9200; '
            '30-minute match target), Expert Care specialities, the support number for '
            '"Prefer to book by call?", upcoming appointments (paid bookings that are finding a doctor or confirmed, '
            'soonest first, up to 10) and the My Cases badge. "How it works" and the trust badges are static app content. '
            'photo_url needs the same Authorization header to download.'
        ),
        parameters=[PricingQuerySerializer],
        examples=[OpenApiExample('Home', value=HOME_EXAMPLE, response_only=True)],
    )
    def get(self, request):
        from .views import patient_profile

        query = PricingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        pricing = resolve_pricing(query.validated_data.get('country'), query.validated_data.get('lat'), query.validated_data.get('lng')).pricing

        user = request.user
        profile = patient_profile(user)
        photo_url = request.build_absolute_uri('/api/v1/patients/profile/photo/') if profile.profile_photo else None
        data = {
            'greeting_name': user.get_full_name() or DEFAULT_GREETING_NAME,
            'photo_url': photo_url,
            'preferred_language': profile.preferred_language,
            'unread_notification_count': Notification.objects.filter(user=user, read_at__isnull=True).count(),
            'support_phone': settings.SUPPORT_PHONE_NUMBER,
            'general_care': {
                'title': 'General Consultation', 'country_code': pricing.country_code, 'fee': pricing.general_fee,
                'currency': pricing.currency, 'fee_display': format_amount(pricing.general_fee, pricing.currency_symbol),
                'match_within_minutes': settings.DOCTOR_MATCH_TARGET_MINUTES,
            },
            'specialities': list(Speciality.objects.filter(is_active=True).order_by('display_order', 'name')),
            'upcoming_appointments': upcoming_appointments(user),
            'active_case_count': case_queryset(user).filter(stage_filter(ACTIVE_STAGES)).count(),
        }
        return Response(self.get_serializer(data).data)


class CaseListView(NoStoreResponseMixin, generics.ListAPIView):
    permission_classes = [IsPatient]
    serializer_class = CaseSerializer

    def get_queryset(self):
        queryset = case_queryset(self.request.user)
        group = self.request.query_params.get('status', '').strip()
        if group == 'active':
            queryset = queryset.filter(stage_filter(ACTIVE_STAGES))
        elif group == 'closed':
            queryset = queryset.filter(stage_filter(CLOSED_STAGES))
        elif group:
            raise serializers.ValidationError({'status': ['Use active or closed.']})
        return queryset

    @extend_schema(
        tags=['My Cases'], summary='My Cases: every booking with its progress tracker',
        description=(
            'All bookings for you and your family, newest first, including drafts. `stage` is one of draft, '
            'awaiting_payment, finding_doctor, confirmed, completed, cancelled. `next_action` tells the app where the '
            'case card button goes: complete_history (Step 2), select_slot (Schedule Appointment), pay (checkout), '
            'wait_for_doctor, join_consultation, view_record (Medical Records detail). '
            '`tracker` is the 4-step progress bar. Paginated (20 per page).'
        ),
        parameters=[OpenApiParameter(
            'status', str, required=False, enum=['active', 'closed'],
            description='active = draft to confirmed; closed = completed or cancelled. Omit for all.',
        )],
        examples=[OpenApiExample('My Cases page', response_only=True, value={
            'count': 2, 'next': None, 'previous': None, 'results': [DRAFT_CASE_EXAMPLE, CASE_EXAMPLE],
        })],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CaseDetailView(NoStoreResponseMixin, generics.RetrieveAPIView):
    permission_classes = [IsPatient]
    serializer_class = CaseSerializer
    lookup_url_kwarg = 'consultation_id'

    def get_queryset(self):
        return case_queryset(self.request.user)

    @extend_schema(
        tags=['My Cases'], summary='One case with its tracker',
        examples=[OpenApiExample('Case finding a doctor', value=CASE_EXAMPLE, response_only=True)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
