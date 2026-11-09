from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.consultations.models import Consultation


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
    """A call or chat session the doctor app ran for an appointment. The app handles calling; every field is optional."""

    appointment = models.ForeignKey(Appointment, related_name='calls', on_delete=models.CASCADE)
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
