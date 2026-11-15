from django.db.models import Q

from apps.accounts.models import User, VerifiedIdentity
from apps.consultations.models import Consultation

from .models import FamilyMember


def beneficiary_filter(user):
    phones = set()
    indian_numbers = set()
    if user.is_active and user.role == User.Role.PATIENT and not user.is_staff and not user.is_superuser:
        for phone in VerifiedIdentity.objects.filter(
            user=user, role=User.Role.PATIENT, kind=VerifiedIdentity.Kind.PHONE,
            retired_at__isnull=True,
        ).values_list('value', flat=True):
            phones.add(phone)
            if phone.startswith('+'):
                if len(phone[1:]) > 10:
                    phones.add(phone[1:])
                if phone.startswith('+91') and len(phone) == 13:
                    indian_numbers.add(phone[3:])
    phone_filter = Q(patient_phone__in=phones) | Q(
        patient_phone__in=indian_numbers, country_code__in=['', 'IN'],
    )
    # Use the sealed booking snapshot, not an editable family profile or an unverified account phone.
    return ~Q(status=Consultation.Status.DRAFT) & Q(
        patient_relation__in=FamilyMember.Relation.values,
        appointment__isnull=False,
    ) & phone_filter


def accessible_consultations(user):
    return Consultation.objects.filter(Q(patient=user) | beneficiary_filter(user))


def accessible_appointments(user):
    from apps.appointments.models import Appointment

    shared = Consultation.objects.filter(beneficiary_filter(user))
    return Appointment.objects.filter(Q(patient=user) | Q(consultation__in=shared))


def is_beneficiary_view(consultation, user):
    return user is not None and user.role == User.Role.PATIENT and consultation.patient_id != user.pk
