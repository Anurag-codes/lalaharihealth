from collections import OrderedDict
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.doctors.models import DoctorProfile
from .models import Appointment, AppointmentSlot

SLOT_MINUTES = 15
DAY_START = time(8, 0)
LAST_SLOT_START = time(23, 45)
BOOKING_WINDOW_DAYS = 30


def local_datetime(day, at):
    return timezone.make_aware(datetime.combine(day, at), timezone.get_current_timezone())


def bookable_slots(speciality_id=None):
    """Active future slots of verified doctors of this speciality (None = general physicians).

    Legacy staff-created shared slots (no doctor) count only for general bookings.
    """
    verified = DoctorProfile.objects.filter(
        is_active=True, verification_status=DoctorProfile.VerificationStatus.VERIFIED,
        user__is_active=True, user__role='doctor', speciality_id=speciality_id,
    ).values('user_id')
    doctors = Q(doctor_id__in=verified)
    if speciality_id is None:
        doctors |= Q(doctor__isnull=True)
    return (
        AppointmentSlot.objects.filter(is_active=True, starts_at__gt=timezone.now())
        .filter(doctors)
        .annotate(occupied=Count('appointments', filter=~Q(appointments__status=Appointment.Status.CANCELLED)))
    )


def in_booking_hours(starts_at):
    return timezone.localtime(starts_at).time() >= DAY_START


def free_slots_for_date(day, speciality_id=None):
    """Group free slots by start time. Returns a list of dicts ordered by time."""
    start = local_datetime(day, time(0))
    grouped = OrderedDict()
    for slot in bookable_slots(speciality_id).filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1)).order_by('starts_at', 'id'):
        remaining = max(slot.capacity - slot.occupied, 0)
        if not remaining or not in_booking_hours(slot.starts_at):
            continue
        entry = grouped.setdefault(slot.starts_at, {'id': slot.pk, 'starts_at': slot.starts_at, 'remaining_capacity': 0})
        entry['remaining_capacity'] += remaining
    return list(grouped.values())


def lock_free_slot(starts_at, preferred_id=None, speciality_id=None):
    """Lock and return a slot with free capacity at this exact time, preferring the one the app selected."""
    candidates = (
        AppointmentSlot.objects.select_for_update()
        .filter(pk__in=bookable_slots(speciality_id).filter(starts_at=starts_at).values('pk'))
        .order_by('starts_at', 'id')
    )
    ordered = sorted(candidates, key=lambda slot: slot.pk != preferred_id)
    for slot in ordered:
        occupied = slot.appointments.exclude(status=Appointment.Status.CANCELLED).count()
        if occupied < slot.capacity:
            return slot
    return None


def display_time(value):
    return timezone.localtime(value).strftime('%I:%M %p')


def display_date(value):
    return timezone.localtime(value).strftime('%d %b %Y')
