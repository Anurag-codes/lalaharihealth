"""Doctor app sign-up: create the profile and copy the matching For Doctors form entry into it."""
import logging
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.db.models import Q

from apps.treatments.models import TreatmentSystem

from .models import DoctorApplication, DoctorDocument, DoctorProfile, Speciality

logger = logging.getLogger(__name__)

GENERAL_PHYSICIAN = 'General Physician'


INDIA_CALLING_CODE = '91'


def phone_digits(raw):
    """Digits of a typed phone number without the international (00) or trunk (0) prefix."""
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('00'):
        return digits[2:]
    if digits.startswith('0'):
        return digits[1:]
    return digits


def same_phone(typed, e164, country_code='IN'):
    """A form number matches a verified E.164 number only when it is the same full number.
    A 10-digit number without country code is read as Indian (+91), and only for Indian applications."""
    digits, verified = phone_digits(typed), e164.lstrip('+')
    if len(digits) == 10:
        return (country_code or 'IN').upper() == 'IN' and verified == INDIA_CALLING_CODE + digits
    return len(digits) > 10 and digits == verified


def matching_application(e164):
    """Newest For Doctors form entry (any status) whose phone is this verified number."""
    if not e164:
        return None
    applications = DoctorApplication.objects.exclude(phone_number='').order_by('-created_at', '-id')
    for application in applications.iterator():
        if same_phone(application.phone_number, e164, application.country_code):
            return application
    return None


def find_speciality(name):
    name = (name or '').strip()
    if not name:
        return None
    query = Q(name__iexact=name) | Q(short_name__iexact=name) | Q(slug__iexact=name)
    return Speciality.objects.filter(query, is_active=True).order_by('display_order', 'name').first()


def split_name(full_name):
    name = re.sub(r'^\s*dr\.?\s+', '', full_name or '', flags=re.IGNORECASE).strip()
    first, _, last = name.partition(' ')
    return first[:150], last.strip()[:150]


def copy_file(source, target, name):
    """Copy an uploaded file into another field/storage. Missing files are skipped."""
    try:
        with source.open('rb') as handle:
            target.save(name, ContentFile(handle.read()), save=False)
        return True
    except (OSError, ValueError):
        logger.warning('Could not copy %s while importing a doctor application.', source.name)
        return False


def import_application(profile, application):
    user = profile.user
    if not (user.first_name or user.last_name):
        user.first_name, user.last_name = split_name(application.full_name)
    if not user.city and application.city:
        user.city = application.city[:100]
    if not user.email and application.email:
        user.email = application.email
    user.save(update_fields=['first_name', 'last_name', 'city', 'email'])

    speciality = None
    if application.consultation_category == DoctorApplication.ConsultationCategory.SPECIALIST:
        speciality = find_speciality(application.specialization)
    profile.application = application
    profile.speciality = speciality
    profile.specialization = (
        speciality.name if speciality else (application.specialization or GENERAL_PHYSICIAN)
    )[:150]
    profile.qualification = application.qualification[:255]
    profile.experience_years = application.experience_years or 0
    profile.city = application.city[:100]
    valid_systems = set(TreatmentSystem.values)
    profile.systems_practiced = ','.join(
        system for system in application.treatment_systems or [] if system in valid_systems
    )[:255]
    profile.consultation_fee = application.consultation_fee or 0
    profile.currency = application.currency or 'INR'
    if application.photo:
        copy_file(application.photo, profile.profile_photo, application.photo.name)
    profile.save()

    for document in application.documents.all():
        imported = DoctorDocument(
            doctor=profile, document_type=DoctorDocument.DocumentType.OTHER,
            original_name=Path(document.file.name).name[:255],
        )
        if copy_file(document.file, imported.file, imported.original_name):
            imported.save()


def ensure_doctor_profile(user):
    """Profile for a doctor signing in to the app; new profiles import their form entry and await staff verification."""
    profile, created = DoctorProfile.objects.get_or_create(
        user=user, defaults={'specialization': GENERAL_PHYSICIAN},
    )
    if created:
        application = matching_application(user.phone_number)
        if application is not None:
            import_application(profile, application)
    return profile


def onboarding_status(profile):
    user = profile.user
    profile_completed = bool(
        (user.first_name or user.last_name) and profile.age and profile.gender
        and profile.registration_number and profile.qualification
    )
    certificate = any(
        document.document_type == DoctorDocument.DocumentType.MEDICAL_REGISTRATION for document in profile.documents.all()
    )
    availability = profile.availability_windows.exists()
    if not (profile_completed and certificate):
        next_step = 'profile'
    elif not availability:
        next_step = 'availability'
    else:
        next_step = 'done'
    return {
        'profile_completed': profile_completed,
        'registration_certificate_uploaded': certificate,
        'availability_set': availability,
        'is_complete': next_step == 'done',
        'next_step': next_step,
    }
