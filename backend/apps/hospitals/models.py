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
