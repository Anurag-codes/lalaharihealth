from django.conf import settings
from django.db import models

from apps.treatments.models import TreatmentSystem


class DoctorProfile(models.Model):
    """Extended profile + verification/KYC state for a user with role=doctor."""

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='doctor_profile', on_delete=models.CASCADE)
    specialization = models.CharField(max_length=150)
    systems_practiced = models.CharField(
        max_length=255,
        help_text='Comma separated TreatmentSystem values this doctor consults on',
    )
    qualification = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    experience_years = models.PositiveSmallIntegerField(default=0)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to='doctors/photos/', blank=True, null=True)
    consultation_fee = models.PositiveIntegerField(help_text='Fee in INR')
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


class DoctorDocument(models.Model):
    """KYC / degree / registration proof uploaded during onboarding."""

    class DocumentType(models.TextChoices):
        DEGREE_CERTIFICATE = 'degree_certificate', 'Degree Certificate'
        MEDICAL_REGISTRATION = 'medical_registration', 'Medical Council Registration'
        GOVERNMENT_ID = 'government_id', 'Government ID'
        OTHER = 'other', 'Other'

    doctor = models.ForeignKey(DoctorProfile, related_name='documents', on_delete=models.CASCADE)
    document_type = models.CharField(max_length=25, choices=DocumentType.choices)
    file = models.FileField(upload_to='doctors/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.doctor} - {self.get_document_type_display()}'


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

    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=15)
    qualification = models.CharField(max_length=255, help_text='e.g. MBBS, BAMS, MD (Ayurveda)')
    experience_years = models.PositiveSmallIntegerField()
    specialization = models.CharField(max_length=150)
    treatment_systems = models.JSONField(default=list, help_text='Selected TreatmentSystem values')
    city = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
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
