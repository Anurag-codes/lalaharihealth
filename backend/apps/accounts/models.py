from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """Custom user shared by patients, doctors and staff, distinguished by role."""

    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR = 'doctor', 'Doctor'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    phone_number = models.CharField(max_length=16, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class VerifiedIdentity(models.Model):
    class Kind(models.TextChoices):
        EMAIL = 'email', 'Email'
        PHONE = 'phone', 'Phone'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verified_identities')
    kind = models.CharField(max_length=5, choices=Kind.choices)
    value = models.CharField(max_length=254)
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['kind', 'value'], name='unique_verified_contact'),
            models.UniqueConstraint(fields=['user', 'kind'], name='one_contact_kind_per_user'),
        ]


class EmailOtpChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    code_digest = models.CharField(max_length=64)
    link_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    delivered_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['email', 'created_at'])]


class AuthRateLimit(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    next_allowed_at = models.DateTimeField(null=True, blank=True)


class UsedFirebaseToken(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)
