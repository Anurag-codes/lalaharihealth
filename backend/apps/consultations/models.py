from django.conf import settings
from django.db import models

from apps.core.storage import private_document_storage
from apps.patients.models import FamilyMember
from apps.treatments.models import Condition, ConditionType, ConditionVariant, TreatmentSystem


GENERAL_CONSULTATION_TITLE = 'General Consultation'


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
    speciality = models.ForeignKey(
        'doctors.Speciality', related_name='consultations', on_delete=models.PROTECT, null=True, blank=True,
        help_text='Empty for a general physician consultation.',
    )
    condition = models.ForeignKey(Condition, related_name='consultations', on_delete=models.SET_NULL, null=True)
    condition_type = models.ForeignKey(
        ConditionType, related_name='consultations', on_delete=models.SET_NULL, null=True, blank=True,
    )
    condition_variant = models.ForeignKey(
        ConditionVariant, related_name='consultations', on_delete=models.SET_NULL, null=True, blank=True,
    )
    # Snapshot of the selected dropdown names, kept if admin later renames or removes an option.
    chief_complaint = models.CharField(max_length=500, blank=True)
    condition_details = models.TextField(blank=True)
    information_confirmed_at = models.DateTimeField(null=True, blank=True)
    family_member = models.ForeignKey(
        FamilyMember, related_name='consultations', on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Empty when the account holder booked for themselves.',
    )
    # Snapshot kept so records still show "Spouse"/"Son" after a family member is removed.
    patient_relation = models.CharField(max_length=15, default='self')
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
    fee_charged = models.PositiveIntegerField(default=0, help_text='Fee in whole units of currency')
    currency = models.CharField(max_length=3, default='INR', help_text='Currency of fee_charged')
    country_code = models.CharField(
        max_length=2, blank=True, help_text='Pricing country chosen at booking (blank = default, India)',
    )
    recommended_system = models.CharField(max_length=20, choices=TreatmentSystem.choices, blank=True)
    doctor_notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    record_updated_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Consultation #{self.pk} - {self.patient}'

    @property
    def title(self):
        return self.speciality.title if self.speciality_id else GENERAL_CONSULTATION_TITLE

    @property
    def pricing(self):
        from apps.pricing.service import pricing_for

        return pricing_for(self.country_code)

    @property
    def expected_fee(self):
        """Speciality fee (always INR) or the general physician fee of the booking country."""
        return self.speciality.fee if self.speciality_id else self.pricing.general_fee

    @property
    def expected_currency(self):
        return 'INR' if self.speciality_id else self.pricing.currency


class ConsultationDocument(models.Model):
    consultation = models.ForeignKey(Consultation, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(storage=private_document_storage, upload_to='consultations/%Y/%m/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PrescriptionItem(models.Model):
    class Timing(models.TextChoices):
        MORNING = 'morning', 'Morning'
        AFTERNOON = 'afternoon', 'Afternoon'
        EVENING = 'evening', 'Evening'
        NIGHT = 'night', 'Night'

    class FoodRelation(models.TextChoices):
        BEFORE_FOOD = 'before_food', 'Before food'
        AFTER_FOOD = 'after_food', 'After food'
        WITH_FOOD = 'with_food', 'With food'
        ANY_TIME = 'any_time', 'Any time'

    consultation = models.ForeignKey(Consultation, related_name='prescription_items', on_delete=models.CASCADE)
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text='For example: 1 tablet, 10 ml')
    timings = models.JSONField(default=list, help_text='One or more of morning, afternoon, evening, night')
    food_relation = models.CharField(max_length=15, choices=FoodRelation.choices)
    duration_days = models.PositiveSmallIntegerField()
    instructions = models.CharField(max_length=500, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.medicine_name
