from django.conf import settings
from django.db import models


class Announcement(models.Model):
    """Admin broadcast. Saved as a draft; the "Send" admin action delivers it to the inbox (and push)."""

    class Audience(models.TextChoices):
        PATIENTS = 'patients', 'Patients'
        DOCTORS = 'doctors', 'Doctors'
        ALL = 'all', 'Everyone'

    title = models.CharField(max_length=120)
    body = models.TextField(max_length=1000)
    title_hi = models.CharField(max_length=120, blank=True, help_text='Optional Hindi title for users who chose हिन्दी')
    body_hi = models.TextField(max_length=1000, blank=True)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.PATIENTS)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Notification(models.Model):
    """One inbox item shown under the bell icon."""

    class Kind(models.TextChoices):
        PAYMENT_SUCCESS = 'payment_success', 'Payment successful'
        DOCTOR_ASSIGNED = 'doctor_assigned', 'Doctor assigned'
        APPOINTMENT_REMINDER = 'appointment_reminder', 'Appointment reminder'
        CONSULTATION_COMPLETED = 'consultation_completed', 'Consultation completed'
        APPOINTMENT_CANCELLED = 'appointment_cancelled', 'Appointment cancelled'
        ANNOUNCEMENT = 'announcement', 'Announcement'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=1000)
    appointment = models.ForeignKey(
        'appointments.Appointment', related_name='notifications', on_delete=models.SET_NULL, null=True, blank=True,
    )
    consultation = models.ForeignKey(
        'consultations.Consultation', related_name='notifications', on_delete=models.SET_NULL, null=True, blank=True,
    )
    announcement = models.ForeignKey(Announcement, related_name='notifications', on_delete=models.SET_NULL, null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['user', 'read_at'], name='notification_user_unread')]

    def __str__(self):
        return f'{self.get_kind_display()} for {self.user}'


class DeviceToken(models.Model):
    """Firebase Cloud Messaging registration token of a signed-in app install."""

    class Platform(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='device_tokens', on_delete=models.CASCADE)
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.get_platform_display()} device of {self.user}'
