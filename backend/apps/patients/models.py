from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
    """Extended profile for a user with role=patient."""

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='patient_profile', on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    city = models.CharField(max_length=100, blank=True)
    medical_history = models.TextField(blank=True, help_text='Known conditions, allergies, ongoing medication')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
