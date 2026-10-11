from django.conf import settings
from django.db import models

from apps.core.storage import private_document_storage
from apps.treatments.models import Condition, TreatmentSystem


class Consultation(models.Model):
    """A patient's request for guidance, from symptom submission to doctor advice."""

    class Mode(models.TextChoices):
        CHAT = 'chat', 'Chat'
        AUDIO = 'audio', 'Audio Call'
        VIDEO = 'video', 'Video Call'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
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
    patient_name = models.CharField(max_length=150, blank=True)
    patient_age = models.PositiveSmallIntegerField(null=True, blank=True)
    patient_gender = models.CharField(
        max_length=20,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say')],
        blank=True,
    )
    patient_phone = models.CharField(max_length=16, blank=True)
    symptoms = models.TextField(blank=True)
    duration_value = models.PositiveIntegerField(null=True, blank=True)
    duration_unit = models.CharField(
        max_length=10,
        choices=[('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years')],
        blank=True,
    )
    ongoing_medication = models.BooleanField(null=True, blank=True)
    treatment_details = models.TextField(blank=True)
    history_completed = models.BooleanField(default=False)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CHAT)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    fee_charged = models.PositiveIntegerField(default=0, help_text='Fee in INR')
    recommended_system = models.CharField(max_length=20, choices=TreatmentSystem.choices, blank=True)
    doctor_notes = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Consultation #{self.pk} - {self.patient}'


class ConsultationDocument(models.Model):
    consultation = models.ForeignKey(Consultation, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(storage=private_document_storage, upload_to='consultations/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
