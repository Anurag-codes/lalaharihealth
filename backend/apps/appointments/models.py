from django.conf import settings
from django.db import models

from apps.consultations.models import Consultation


class AppointmentSlot(models.Model):
    starts_at = models.DateTimeField(unique=True)
    capacity = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['starts_at']
        constraints = [models.CheckConstraint(condition=models.Q(capacity__gte=1), name='slot_capacity_positive')]

    def __str__(self):
        return str(self.starts_at)


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_time']

    def __str__(self):
        return f'Appointment #{self.pk} at {self.slot_time}'
