"""Read models for the staff console. Each serializer builds plain values from preloaded rows; DRF fields format them."""
from django.utils import timezone
from rest_framework import serializers

from apps.consultations.models import Consultation
from apps.consultations.serializers import relation_label
from apps.payments.models import Payment
from .assignment import (
    CALL_LOCKED, CONSULTATION_LOCKED, LOCKED_CONSULTATION_STATUSES, VIDEO_LOCKED, call_started,
)
from .availability import display_date, display_time
from .models import Appointment

ASSIGNABLE = (Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED)
CLOSED = (Appointment.Status.COMPLETED, Appointment.Status.CANCELLED)
GENERAL_CATEGORY = 'General Physician'


def person_name(user):
    return user.get_full_name() if user else ''


def doctor_name(user):
    return f'Dr. {user.get_full_name() or user.username}' if user else ''


def currency_symbols():
    from apps.pricing.models import CountryPricing

    symbols = dict(CountryPricing.objects.values_list('currency', 'currency_symbol'))
    symbols.setdefault('INR', '\u20b9')
    return symbols


def amount_display(amount, currency, symbols):
    from apps.pricing.service import format_amount

    return format_amount(amount, symbols.get(currency) or f'{currency} ')


def loaded_payment(consultation):
    return getattr(consultation, 'payment', None)


def loaded_video_room(appointment):
    return getattr(appointment, 'video_room', None)


def lock_reason(appointment):
    """Why staff cannot assign/reschedule now, from preloaded rows. The assignment API re-checks under row locks."""
    consultation = appointment.consultation
    if appointment.status not in ASSIGNABLE:
        return 'Only paid or approved free appointments awaiting a doctor, or confirmed appointments, can be assigned.'
    payment = loaded_payment(consultation)
    if not appointment.is_free_consultation and (payment is None or payment.status != Payment.Status.SUCCESS):
        return 'Confirmed payment is required.'
    if appointment.status == Appointment.Status.CONFIRMED:
        if consultation.status in LOCKED_CONSULTATION_STATUSES:
            return CONSULTATION_LOCKED
        if any(call_started(call) for call in appointment.calls.all()):
            return CALL_LOCKED
        room = loaded_video_room(appointment)
        if room is not None and room.room_id:
            return VIDEO_LOCKED
    return None


def can_edit_patient(appointment):
    return appointment.status not in CLOSED and appointment.consultation.status not in (
        Consultation.Status.COMPLETED, Consultation.Status.CANCELLED,
    )


class StaffPersonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)


class StaffBookerSerializer(StaffPersonSerializer):
    email = serializers.CharField(allow_blank=True)


class StaffCategorySerializer(serializers.Serializer):
    speciality_id = serializers.IntegerField(allow_null=True, help_text='null = General Physician')
    name = serializers.CharField()
    title = serializers.CharField()


class StaffDoctorRefSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='Doctor user ID; send as doctor_id when assigning')
    name = serializers.CharField()
    specialization = serializers.CharField(allow_blank=True)


STATUS_HELP = 'pending, awaiting_payment, finding_doctor, confirmed, completed or cancelled'


class StaffAppointmentSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(allow_blank=True)
    free_consultation_doctor = serializers.IntegerField(allow_null=True)
    id = serializers.IntegerField()
    appointment_number = serializers.CharField()
    status = serializers.CharField(help_text=STATUS_HELP)
    status_label = serializers.CharField()
    slot_time = serializers.DateTimeField()
    schedule_date = serializers.DateField(help_text='India date')
    schedule_time = serializers.CharField(help_text='e.g. 10:00 AM')
    date_display = serializers.CharField(help_text='e.g. 16 Nov 2026')
    patient_name = serializers.CharField(allow_blank=True)
    patient_phone = serializers.CharField(allow_blank=True)
    patient_relation = serializers.CharField(help_text='self, spouse, son ... relative to the booker')
    patient_relation_label = serializers.CharField()
    booker = StaffPersonSerializer(help_text='Account that booked and paid')
    category = StaffCategorySerializer()
    mode = serializers.CharField()
    mode_label = serializers.CharField()
    doctor = StaffDoctorRefSerializer(allow_null=True)
    payment_status = serializers.CharField(help_text='not_required (free coupon), not_started, pending, success, failed or refunded')
    amount = serializers.IntegerField(help_text='Whole currency units')
    currency = serializers.CharField()
    amount_display = serializers.CharField()
    created_at = serializers.DateTimeField()
    is_overdue = serializers.BooleanField(help_text='Still waiting for a doctor after its time has passed')
    can_assign = serializers.BooleanField(help_text='Advisory: the assign API re-checks everything')
    lock_reason = serializers.CharField(allow_null=True)
    can_edit_patient = serializers.BooleanField()
    needs_completion_confirmation = serializers.BooleanField()

    def symbols(self):
        if 'symbols' not in self.context:
            self.context['symbols'] = currency_symbols()
        return self.context['symbols']

    def build(self, appointment):
        consultation = appointment.consultation
        speciality = consultation.speciality
        payment = loaded_payment(consultation)
        doctor = appointment.doctor
        profile = getattr(doctor, 'doctor_profile', None) if doctor else None
        reason = lock_reason(appointment)
        return {
            'id': appointment.pk, 'appointment_number': f'APT-{appointment.pk:05d}',
            'status': appointment.status, 'status_label': appointment.get_status_display(),
            'slot_time': appointment.slot_time, 'schedule_date': timezone.localtime(appointment.slot_time).date(),
            'schedule_time': display_time(appointment.slot_time), 'date_display': display_date(appointment.slot_time),
            'patient_name': consultation.patient_name, 'patient_phone': consultation.patient_phone,
            'patient_relation': consultation.patient_relation,
            'patient_relation_label': relation_label(consultation.patient_relation),
            'booker': self.booker_data(appointment.patient),
            'category': {
                'speciality_id': speciality.pk if speciality else None,
                'name': speciality.name if speciality else GENERAL_CATEGORY, 'title': consultation.title,
            },
            'mode': consultation.mode, 'mode_label': consultation.get_mode_display(),
            'doctor': {
                'id': doctor.pk, 'name': doctor_name(doctor), 'specialization': profile.specialization if profile else '',
            } if doctor else None,
            'payment_status': 'not_required' if appointment.is_free_consultation else (payment.status if payment else 'not_started'),
            'coupon_code': appointment.coupon_code, 'free_consultation_doctor': appointment.free_consultation_doctor_id,
            'amount': consultation.fee_charged, 'currency': consultation.currency,
            'amount_display': amount_display(consultation.fee_charged, consultation.currency, self.symbols()),
            'created_at': appointment.created_at,
            'is_overdue': appointment.status == Appointment.Status.FINDING_DOCTOR and appointment.slot_time <= timezone.now(),
            'can_assign': reason is None, 'lock_reason': reason,
            'can_edit_patient': can_edit_patient(appointment),
            'needs_completion_confirmation': (
                appointment.status == Appointment.Status.COMPLETED and appointment.completion_confirmed_at is None
            ),
        }

    def booker_data(self, user):
        return {'id': user.pk, 'name': person_name(user), 'phone': user.phone_number}

    def to_representation(self, appointment):
        return super().to_representation(self.build(appointment))


class StaffPaymentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    method = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField()
    gateway_order_id = serializers.CharField(allow_null=True)
    transaction_id = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class StaffTimelineSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField()
    information_confirmed_at = serializers.DateTimeField(allow_null=True)
    paid_at = serializers.DateTimeField(allow_null=True)
    doctor_assigned_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    completion_confirmed_at = serializers.DateTimeField(allow_null=True)
    completion_confirmed_by = serializers.CharField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)


class StaffDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    original_name = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    download_path = serializers.CharField(help_text='Staff-authenticated download path')


class StaffCallSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    mode = serializers.CharField(allow_blank=True)
    provider = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    status_label = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    duration_seconds = serializers.IntegerField(allow_null=True)
    end_reason = serializers.CharField(allow_blank=True)


class StaffAppointmentDetailSerializer(StaffAppointmentSerializer):
    booker = StaffBookerSerializer(help_text='Account that booked and paid')
    consultation_id = serializers.IntegerField()
    consultation_status = serializers.CharField()
    chief_complaint = serializers.CharField(allow_blank=True)
    condition_details = serializers.CharField(allow_blank=True)
    symptoms = serializers.CharField(allow_blank=True)
    duration_display = serializers.CharField(allow_blank=True, help_text='e.g. 5 Days')
    ongoing_medication = serializers.BooleanField(allow_null=True)
    treatment_details = serializers.CharField(allow_blank=True)
    patient_age = serializers.IntegerField(allow_null=True)
    patient_gender = serializers.CharField(allow_blank=True)
    patient_gender_label = serializers.CharField(allow_blank=True)
    family_member_id = serializers.IntegerField(allow_null=True)
    payment = StaffPaymentSerializer(allow_null=True)
    timeline = StaffTimelineSerializer()
    documents = StaffDocumentSerializer(many=True)
    calls = StaffCallSerializer(many=True)
    video_room_provisioned = serializers.BooleanField(
        help_text='true once 100ms join credentials were issued; doctor/time are then locked',
    )

    def booker_data(self, user):
        return {**super().booker_data(user), 'email': user.email}

    def build(self, appointment):
        data = super().build(appointment)
        consultation = appointment.consultation
        payment = loaded_payment(consultation)
        room = loaded_video_room(appointment)
        duration = ''
        if consultation.duration_value:
            duration = f'{consultation.duration_value} {consultation.get_duration_unit_display()}'
        confirmed_by = appointment.completion_confirmed_by
        data.update({
            'consultation_id': consultation.pk, 'consultation_status': consultation.status,
            'chief_complaint': consultation.chief_complaint or consultation.title,
            'condition_details': consultation.condition_details, 'symptoms': consultation.symptoms,
            'duration_display': duration, 'ongoing_medication': consultation.ongoing_medication,
            'treatment_details': consultation.treatment_details,
            'patient_age': consultation.patient_age, 'patient_gender': consultation.patient_gender,
            'patient_gender_label': consultation.get_patient_gender_display() if consultation.patient_gender else '',
            'family_member_id': consultation.family_member_id,
            'payment': {
                'id': payment.pk, 'status': payment.status, 'method': payment.method, 'amount': payment.amount,
                'currency': payment.currency, 'gateway_order_id': payment.gateway_order_id,
                'transaction_id': payment.transaction_id, 'created_at': payment.created_at,
            } if payment else None,
            'timeline': {
                'created_at': appointment.created_at,
                'information_confirmed_at': consultation.information_confirmed_at,
                'paid_at': appointment.paid_at, 'doctor_assigned_at': appointment.doctor_assigned_at,
                'completed_at': appointment.completed_at, 'completion_confirmed_at': appointment.completion_confirmed_at,
                'completion_confirmed_by': (person_name(confirmed_by) or confirmed_by.username) if confirmed_by else None,
                'cancelled_at': appointment.cancelled_at,
            },
            'documents': [{
                'id': document.pk, 'original_name': document.original_name, 'uploaded_at': document.uploaded_at,
                'download_path': f'/api/v1/staff/appointments/{appointment.pk}/documents/{document.pk}/download/',
            } for document in consultation.documents.all()],
            'calls': [{
                'id': call.pk, 'mode': call.mode, 'provider': call.provider, 'status': call.status,
                'status_label': call.get_status_display(), 'started_at': call.started_at, 'ended_at': call.ended_at,
                'duration_seconds': call.duration_seconds, 'end_reason': call.end_reason,
            } for call in appointment.calls.all()],
            'video_room_provisioned': bool(room is not None and room.room_id),
        })
        return data


class StaffAppointmentQuerySerializer(serializers.Serializer):
    QUEUES = ('needs_doctor', 'overdue', 'today', 'awaiting_payment', 'completion_pending', 'upcoming')
    ORDERINGS = ('slot_time', '-slot_time', 'created_at', '-created_at')

    q = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text='APT number, patient, phone, booker or doctor name')
    queue = serializers.ChoiceField(choices=QUEUES, required=False, help_text=(
        'needs_doctor = paid, waiting for a doctor; overdue = waiting after its time passed; today = today\'s paid '
        'appointments; awaiting_payment; completion_pending = doctor marked completed, staff not yet confirmed; '
        'upcoming = confirmed and not yet over'
    ))
    status = serializers.ChoiceField(choices=Appointment.Status.choices, required=False)
    date_from = serializers.DateField(required=False, help_text='India date, inclusive')
    date_to = serializers.DateField(required=False, help_text='India date, inclusive')
    doctor_id = serializers.IntegerField(required=False, min_value=1)
    speciality = serializers.RegexField(r'^(general|\d+)$', required=False, help_text='Speciality id, or "general"')
    ordering = serializers.ChoiceField(choices=ORDERINGS, required=False, help_text=(
        'Default: slot_time for needs_doctor, overdue, today and upcoming queues; -slot_time otherwise'
    ))

    def validate(self, attrs):
        if attrs.get('date_from') and attrs.get('date_to') and attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError({'date_to': 'Must be on or after date_from.'})
        return attrs


class StaffSummarySerializer(serializers.Serializer):
    today_date = serializers.DateField()
    needs_doctor = serializers.IntegerField()
    overdue = serializers.IntegerField()
    today_count = serializers.IntegerField()
    awaiting_payment = serializers.IntegerField()
    completion_pending = serializers.IntegerField()
    upcoming_confirmed = serializers.IntegerField()


class StaffPatientUpdateSerializer(serializers.Serializer):
    patient_name = serializers.CharField(max_length=150, required=False)
    patient_age = serializers.IntegerField(min_value=0, max_value=120, required=False)
    patient_gender = serializers.ChoiceField(choices=Consultation._meta.get_field('patient_gender').choices, required=False)

    def validate(self, attrs):
        extra = sorted(set(self.initial_data) - set(self.fields)) if hasattr(self.initial_data, 'keys') else []
        if extra:
            raise serializers.ValidationError({
                field: 'This field cannot be changed here.' for field in extra
            })
        if not attrs:
            raise serializers.ValidationError('Send at least one of patient_name, patient_age or patient_gender.')
        return attrs


class StaffDoctorChoiceQuerySerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField(required=False, help_text='Time to check availability at; default the appointment time')


class StaffConflictSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField()
    appointment_number = serializers.CharField()


class StaffDoctorChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='Doctor user ID; send as doctor_id')
    name = serializers.CharField()
    specialization = serializers.CharField(allow_blank=True)
    speciality_name = serializers.CharField(allow_null=True)
    experience_years = serializers.IntegerField()
    phone = serializers.CharField(allow_blank=True)
    is_current = serializers.BooleanField(help_text='Already assigned to this appointment')
    is_available = serializers.BooleanField(help_text='No other unfinished appointment at starts_at')
    has_open_slot = serializers.BooleanField(help_text='Doctor opened an availability slot at starts_at in the doctor app')
    conflict = StaffConflictSerializer(allow_null=True)
    appointments_that_day = serializers.IntegerField(help_text='Non-cancelled appointments on that India date')


class StaffDoctorChoicesSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    results = StaffDoctorChoiceSerializer(many=True)


class StaffDoctorQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=100)
    speciality = serializers.RegexField(r'^(general|\d+)$', required=False, help_text='Speciality id, or "general"')


class StaffSpecialityRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class StaffDoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='Doctor user ID')
    name = serializers.CharField()
    specialization = serializers.CharField(allow_blank=True)
    speciality = StaffSpecialityRefSerializer(allow_null=True, help_text='null = General Physician')
    phone = serializers.CharField(allow_blank=True)
    experience_years = serializers.IntegerField()
    city = serializers.CharField(allow_blank=True)
    upcoming_appointments = serializers.IntegerField(help_text='Confirmed appointments that have not started yet')


class StaffScheduleQuerySerializer(serializers.Serializer):
    date = serializers.DateField(help_text='India date, YYYY-MM-DD')


class StaffScheduleAppointmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    appointment_number = serializers.CharField()
    status = serializers.CharField(help_text=STATUS_HELP)
    patient_name = serializers.CharField(allow_blank=True)


class StaffScheduleTimeSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    time_display = serializers.CharField()
    is_past = serializers.BooleanField()
    slot_open = serializers.BooleanField(help_text='Doctor opened an availability slot at this time')
    slot_id = serializers.IntegerField(allow_null=True)
    appointment = StaffScheduleAppointmentSerializer(allow_null=True)


class StaffDoctorScheduleSerializer(serializers.Serializer):
    doctor = StaffDoctorRefSerializer()
    date = serializers.DateField()
    times = StaffScheduleTimeSerializer(many=True, help_text='96 entries, 00:00 to 23:45 India time')
