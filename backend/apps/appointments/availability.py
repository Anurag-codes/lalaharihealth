from datetime import datetime, time, timedelta

from django.utils import timezone

SLOT_MINUTES = 15
DAY_START = time(8, 0)
LAST_SLOT_START = time(23, 45)
BOOKING_WINDOW_DAYS = 30


def local_datetime(day, at):
    return timezone.make_aware(datetime.combine(day, at), timezone.get_current_timezone())


def in_booking_window(day):
    today = timezone.localdate()
    return today <= day and (day - today).days <= BOOKING_WINDOW_DAYS


def booking_times_for_date(day):
    """Every future 15-minute start time from 08:00 to 23:45 India time on this date (patients pick a time, not a doctor)."""
    if not in_booking_window(day):
        return []
    now = timezone.now()
    first = DAY_START.hour * 60 + DAY_START.minute
    last = LAST_SLOT_START.hour * 60 + LAST_SLOT_START.minute
    times = (local_datetime(day, time(minutes // 60, minutes % 60)) for minutes in range(first, last + 1, SLOT_MINUTES))
    return [starts_at for starts_at in times if starts_at > now]


def booking_time_error(starts_at):
    """Why this preferred appointment time cannot be booked, or None if it can."""
    local = timezone.localtime(starts_at)
    if local.second or local.microsecond or local.minute % SLOT_MINUTES:
        return 'Choose a 15-minute time, e.g. 10:00 or 10:15.'
    if not DAY_START <= local.time() <= LAST_SLOT_START:
        return 'Choose a time between 08:00 AM and 11:45 PM India time.'
    if starts_at <= timezone.now():
        return 'This time has passed. Please choose a future time.'
    if not in_booking_window(local.date()):
        return f'Choose a date within the next {BOOKING_WINDOW_DAYS} days.'
    return None


def display_time(value):
    return timezone.localtime(value).strftime('%I:%M %p')


def display_date(value):
    return timezone.localtime(value).strftime('%d %b %Y')
