from django.conf import settings
from django.db import models

from apps.consultations.models import Consultation


class Appointment(models.Model):
    """A scheduled slot for a consultation."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    consultation = models.OneToOneField(Consultation, related_name='appointment', on_delete=models.CASCADE)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='appointments_as_patient', on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='appointments_as_doctor', on_delete=models.CASCADE
    )
    slot_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_time']

    def __str__(self):
        return f'Appointment #{self.pk} at {self.slot_time}'
