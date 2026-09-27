from django.db import models

from apps.treatments.models import Condition


class Hospital(models.Model):
    """Partner hospitals we can refer patients to when allopathic treatment is required."""

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    specialties = models.CharField(max_length=255, help_text='Comma separated specialties')
    is_partner = models.BooleanField(default=False, help_text='Gets negotiated/discounted rates for our patients')
    partner_discount_percentage = models.PositiveSmallIntegerField(default=0)
    contact_phone = models.CharField(max_length=15, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class HospitalRecommendation(models.Model):
    """Suggested hospital for a specific condition, ranked by relevance/cost."""

    hospital = models.ForeignKey(Hospital, related_name='recommendations', on_delete=models.CASCADE)
    condition = models.ForeignKey(Condition, related_name='hospital_recommendations', on_delete=models.CASCADE)
    estimated_cost_min = models.PositiveIntegerField(help_text='Approx. minimum cost in INR')
    estimated_cost_max = models.PositiveIntegerField(help_text='Approx. maximum cost in INR')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['estimated_cost_min']

    def __str__(self):
        return f'{self.hospital.name} - {self.condition.name}'


class HospitalApplication(models.Model):
    """Pre-launch interest/lead-capture form submitted by a hospital or clinic.

    Mirrors `apps.doctors.models.DoctorApplication` — decoupled from `Hospital` so a
    facility can register interest before the partner-onboarding flow exists.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        CONTACTED = 'contacted', 'Contacted'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    facility_name = models.CharField(max_length=200)
    contact_person_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    specialties = models.CharField(max_length=255, blank=True, help_text='Comma separated specialties')
    bed_count = models.PositiveIntegerField(blank=True, null=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_priority = models.BooleanField(default=True, help_text='Pre-launch registrants get priority status')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.facility_name} ({self.city})'


class HospitalApplicationDocument(models.Model):
    """Optional supporting registration/empanelment proof uploaded with a HospitalApplication."""

    application = models.ForeignKey(HospitalApplication, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to='hospital_applications/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Document for {self.application.facility_name}'
