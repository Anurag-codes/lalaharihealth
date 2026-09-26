from django.conf import settings
from django.db import models

from apps.treatments.models import Condition, TreatmentSystem


class Consultation(models.Model):
    """A patient's request for guidance, from symptom submission to doctor advice."""

    class Mode(models.TextChoices):
        CHAT = 'chat', 'Chat'
        AUDIO = 'audio', 'Audio Call'
        VIDEO = 'video', 'Video Call'

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        ONGOING = 'ongoing', 'Ongoing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='consultations_as_patient', on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='consultations_as_doctor', on_delete=models.SET_NULL, null=True
    )
    condition = models.ForeignKey(Condition, related_name='consultations', on_delete=models.SET_NULL, null=True)
    symptoms = models.TextField()
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CHAT)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.REQUESTED)
    fee_charged = models.PositiveIntegerField(default=0, help_text='Fee in INR')
    recommended_system = models.CharField(max_length=20, choices=TreatmentSystem.choices, blank=True)
    doctor_notes = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Consultation #{self.pk} - {self.patient}'
