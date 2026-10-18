from datetime import date

from django.conf import settings
from django.db import models

from apps.core.storage import private_document_storage


def years_since(born, today=None):
    if not born:
        return None
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class PatientProfile(models.Model):
    """Extended profile for a user with role=patient."""

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    class Language(models.TextChoices):
        ENGLISH = 'en', 'English'
        HINDI = 'hi', 'हिन्दी'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='patient_profile', on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    city = models.CharField(max_length=100, blank=True)
    medical_history = models.TextField(blank=True, help_text='Known conditions, allergies, ongoing medication')
    profile_photo = models.ImageField(storage=private_document_storage, upload_to='patients/photos/%Y/%m/', blank=True)
    preferred_language = models.CharField(max_length=5, choices=Language.choices, default=Language.ENGLISH)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class FamilyMember(models.Model):
    """A relative a patient can book consultations for."""

    class Relation(models.TextChoices):
        SPOUSE = 'spouse', 'Spouse'
        SON = 'son', 'Son'
        DAUGHTER = 'daughter', 'Daughter'
        FATHER = 'father', 'Father'
        MOTHER = 'mother', 'Mother'
        BROTHER = 'brother', 'Brother'
        SISTER = 'sister', 'Sister'
        GRANDFATHER = 'grandfather', 'Grandfather'
        GRANDMOTHER = 'grandmother', 'Grandmother'
        OTHER = 'other', 'Other'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='family_members', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    relation = models.CharField(max_length=15, choices=Relation.choices)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=PatientProfile.Gender.choices)
    phone_number = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']

    @property
    def age(self):
        return years_since(self.date_of_birth)

    def __str__(self):
        return f'{self.full_name} ({self.get_relation_display()})'
