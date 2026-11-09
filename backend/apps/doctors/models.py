import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from apps.core.storage import private_document_storage
from apps.treatments.models import TreatmentSystem


def doctor_photo_path(instance, filename):
    """Random public file name so doctor photos cannot be guessed before they are shown on the website."""
    extension = Path(filename).suffix.lower()[:5]
    return f'doctors/photos/{uuid.uuid4().hex}{extension}'


class Speciality(models.Model):
    """Specialist category patients can book from "Book Specialist". Doctors without one are general physicians."""

    name = models.CharField(max_length=100, unique=True, help_text='e.g. Dermatology')
    slug = models.SlugField(max_length=120, unique=True)
    short_name = models.CharField(max_length=40, blank=True, help_text='Compact label, e.g. Derma')
    consultation_title = models.CharField(
        max_length=120, blank=True, help_text='Shown on appointment cards, e.g. "Skin Consultation". Default: "<name> Consultation".',
    )
    description = models.CharField(max_length=255, blank=True)
    fee = models.PositiveIntegerField(help_text='Consultation fee in INR charged to the patient')
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'specialities'

    def __str__(self):
        return self.name

    @property
    def title(self):
        return self.consultation_title or f'{self.name} Consultation'


class DoctorProfile(models.Model):
    """Extended profile + verification/KYC state for a user with role=doctor."""

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='doctor_profile', on_delete=models.CASCADE)
    application = models.ForeignKey(
        'DoctorApplication', related_name='doctor_profiles', on_delete=models.SET_NULL, null=True, blank=True,
        help_text='For Doctors form entry whose details were copied when this doctor first signed in to the app.',
    )
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    specialization = models.CharField(max_length=150, blank=True)
    speciality = models.ForeignKey(
        Speciality, related_name='doctors', on_delete=models.PROTECT, null=True, blank=True,
        help_text='Empty for general physicians. Specialists are matched only to bookings of this speciality.',
    )
    systems_practiced = models.CharField(
        max_length=255, blank=True,
        help_text='Comma separated TreatmentSystem values this doctor consults on',
    )
    qualification = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(
        max_length=100, unique=True, null=True, blank=True, help_text='Medical Council registration number',
    )
    experience_years = models.PositiveSmallIntegerField(default=0)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to=doctor_photo_path, blank=True, null=True)
    consultation_fee = models.PositiveIntegerField(default=0, help_text='Fee in whole units of currency')
    currency = models.CharField(max_length=3, default='INR')
    languages_spoken = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Dr. {self.user.get_full_name() or self.user.username}'

    @property
    def is_verified(self):
        return self.is_active and self.verification_status == self.VerificationStatus.VERIFIED


class DoctorAvailability(models.Model):
    """One weekly time window when our care team can reach the doctor, e.g. Monday 07:00-10:00."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, 'Mon'
        TUESDAY = 1, 'Tue'
        WEDNESDAY = 2, 'Wed'
        THURSDAY = 3, 'Thu'
        FRIDAY = 4, 'Fri'
        SATURDAY = 5, 'Sat'
        SUNDAY = 6, 'Sun'

    doctor = models.ForeignKey(DoctorProfile, related_name='availability_windows', on_delete=models.CASCADE)
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['weekday', 'start_time']
        verbose_name_plural = 'doctor availability'
        constraints = [
            models.CheckConstraint(condition=models.Q(start_time__lt=models.F('end_time')), name='availability_starts_before_end'),
            models.UniqueConstraint(fields=['doctor', 'weekday', 'start_time'], name='unique_availability_window_start'),
        ]

    def __str__(self):
        return f'{self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}'


class DoctorDocument(models.Model):
    """KYC / degree / registration proof uploaded during onboarding."""

    class DocumentType(models.TextChoices):
        DEGREE_CERTIFICATE = 'degree_certificate', 'Degree Certificate'
        MEDICAL_REGISTRATION = 'medical_registration', 'Medical Council Registration'
        GOVERNMENT_ID = 'government_id', 'Government ID'
        OTHER = 'other', 'Other'

    doctor = models.ForeignKey(DoctorProfile, related_name='documents', on_delete=models.CASCADE)
    document_type = models.CharField(max_length=25, choices=DocumentType.choices)
    file = models.FileField(storage=private_document_storage, upload_to='doctors/documents/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at', 'id']

    def __str__(self):
        return f'{self.doctor} - {self.get_document_type_display()}'


def doctor_application_photo_path(instance, filename):
    """Random public file name so photos of unapproved applicants cannot be guessed."""
    extension = Path(filename).suffix.lower()[:5]
    return f'doctor_applications/photos/{uuid.uuid4().hex}{extension}'


class DoctorApplication(models.Model):
    """Pre-launch interest/lead-capture form submitted from the public 'For Doctors' page.

    This is intentionally decoupled from `DoctorProfile`/`User` so doctors can register
    interest before accounts, login and the full onboarding flow exist. Applications get
    converted into real `DoctorProfile` records by the team once onboarding opens.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        CONTACTED = 'contacted', 'Contacted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class ConsultationCategory(models.TextChoices):
        GENERAL = 'general', 'General Physician / General Doctor'
        SPECIALIST = 'specialist', 'Specialist'

    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    qualification = models.CharField(max_length=255, blank=True, help_text='e.g. MBBS, BAMS, MD (Ayurveda)')
    experience_years = models.PositiveSmallIntegerField(blank=True, null=True)
    specialization = models.CharField(max_length=150, blank=True)
    consultation_category = models.CharField(
        max_length=12,
        choices=ConsultationCategory.choices,
        blank=True,
        default='',
    )
    consultation_fee = models.PositiveIntegerField(blank=True, null=True, help_text='Consultation fee in whole units of currency')
    country_code = models.CharField(max_length=2, default='IN', help_text='Pricing country used to validate the fee')
    currency = models.CharField(max_length=3, default='INR')
    treatment_systems = models.JSONField(default=list, blank=True, help_text='Selected TreatmentSystem values')
    city = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to=doctor_application_photo_path, blank=True,
        help_text='Optional profile photo. Shown on the website once the application is approved.',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_priority = models.BooleanField(default=True, help_text='Pre-launch registrants get priority status')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.specialization})'


class DoctorApplicationDocument(models.Model):
    """Optional supporting certificate/degree/ID uploaded with a DoctorApplication."""

    application = models.ForeignKey(DoctorApplication, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to='doctor_applications/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Document for {self.application.full_name}'
