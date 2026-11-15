import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.consultations.models import Consultation


class FreeConsultationOffer(models.Model):
    coupon_code = models.CharField(
        max_length=40, unique=True, validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Use uppercase letters, numbers, hyphens or underscores.')],
    )
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    is_active = models.BooleanField(default=False)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True, help_text='Exclusive expiry. Empty means no automatic expiry.')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['is_active'], condition=models.Q(is_active=True), name='one_active_free_consultation_offer'),
            models.CheckConstraint(
                condition=models.Q(valid_from__isnull=True) | models.Q(valid_until__isnull=True) | models.Q(valid_until__gt=models.F('valid_from')),
                name='free_offer_valid_period',
            ),
        ]

    def clean(self):
        super().clean()
        from apps.doctors.models import DoctorProfile

        if self.doctor_id and not DoctorProfile.objects.filter(
            user_id=self.doctor_id, user__role='doctor', user__is_active=True, is_active=True,
            verification_status='verified', speciality__isnull=True,
        ).exists():
            raise ValidationError({'doctor': 'Choose an active, verified general physician.'})
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError({'valid_until': 'Expiry must be after the start.'})

    def __str__(self):
        return self.coupon_code


class AppointmentSlot(models.Model):
    """A bookable time. Doctor slots are 15 minutes and hold one patient each."""

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='appointment_slots', on_delete=models.CASCADE,
        null=True, blank=True, help_text='Empty for older staff-created shared slots.',
    )
    starts_at = models.DateTimeField()
    capacity = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['starts_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name='slot_capacity_positive'),
            models.UniqueConstraint(
                fields=['doctor', 'starts_at'], condition=models.Q(doctor__isnull=False), name='unique_doctor_slot_time',
            ),
            models.UniqueConstraint(
                fields=['starts_at'], condition=models.Q(doctor__isnull=True), name='unique_shared_slot_time',
            ),
        ]

    def __str__(self):
        return f'{self.starts_at} ({self.doctor or "shared"})'


class Appointment(models.Model):
    """A scheduled slot for a consultation."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'
        FINDING_DOCTOR = 'finding_doctor', 'Finding doctor'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    consultation = models.OneToOneField(Consultation, related_name='appointment', on_delete=models.CASCADE)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='appointments_as_patient', on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='appointments_as_doctor', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    slot = models.ForeignKey(AppointmentSlot, related_name='appointments', on_delete=models.PROTECT, null=True, blank=True)
    slot_time = models.DateTimeField()
    coupon_code = models.CharField(max_length=40, blank=True, editable=False)
    free_consultation_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.PROTECT, null=True, blank=True, editable=False,
        help_text='Doctor selected when a free coupon was redeemed. Staff cannot assign another doctor.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    doctor_assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_confirmed_at = models.DateTimeField(
        null=True, blank=True, help_text='When staff confirmed the consultation the doctor marked completed.',
    )
    completion_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_TIMESTAMPS = {
        Status.FINDING_DOCTOR: 'paid_at', Status.CONFIRMED: 'doctor_assigned_at',
        Status.COMPLETED: 'completed_at', Status.CANCELLED: 'cancelled_at',
    }

    class Meta:
        ordering = ['slot_time']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(coupon_code='', free_consultation_doctor__isnull=True)
                    | (~models.Q(coupon_code='') & models.Q(free_consultation_doctor__isnull=False))
                ),
                name='appointment_free_coupon_paired',
            ),
        ]

    @property
    def is_free_consultation(self):
        return bool(
            self.coupon_code and self.free_consultation_doctor_id
            and self.consultation.fee_charged == 0 and self.consultation.speciality_id is None
        )

    def set_status(self, status):
        """Change status, stamp when it happened and return the fields to save."""
        self.status = status
        fields = ['status']
        stamp = self.STATUS_TIMESTAMPS.get(status)
        if stamp:
            setattr(self, stamp, timezone.now())
            fields.append(stamp)
        return fields

    def __str__(self):
        return f'Appointment #{self.pk} at {self.slot_time}'


class AppointmentCall(models.Model):
    """An app-reported call or chat session, separate from consultation completion."""

    class Status(models.TextChoices):
        UNKNOWN = 'unknown', 'Not reported'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        MISSED = 'missed', 'Missed'
        CANCELLED = 'cancelled', 'Cancelled'

    TERMINAL_STATUSES = (Status.COMPLETED, Status.FAILED, Status.MISSED, Status.CANCELLED)

    appointment = models.ForeignKey(Appointment, related_name='calls', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UNKNOWN,
        help_text='SDK outcome reported by the assigned doctor app; not provider-verified or consultation completion.',
    )
    mode = models.CharField(max_length=10, choices=Consultation.Mode.choices, blank=True)
    provider = models.CharField(max_length=50, blank=True, help_text='Calling service used by the app, e.g. agora, zego, jitsi')
    external_call_id = models.CharField(max_length=255, blank=True, help_text="The provider's call, room or channel id")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    end_reason = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text='Any extra details the app wants to keep')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'Call #{self.pk} for appointment #{self.appointment_id}'


class AppointmentVideoRoom(models.Model):
    appointment = models.OneToOneField(Appointment, related_name='video_room', on_delete=models.CASCADE)
    provisioning_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    template_id = models.CharField(max_length=100, editable=False)
    room_id = models.CharField(max_length=100, unique=True, null=True, blank=True, editable=False)
    current_call = models.OneToOneField(
        AppointmentCall, related_name='managed_video_room', on_delete=models.SET_NULL,
        null=True, blank=True, editable=False,
    )

    @property
    def room_name(self):
        return f'consultation-{self.provisioning_id.hex}'
