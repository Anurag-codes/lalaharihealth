from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user shared by patients, doctors and staff, distinguished by role."""

    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR = 'doctor', 'Doctor'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone_number = models.CharField(max_length=15, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
