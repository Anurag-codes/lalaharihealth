"""Doctor app Earnings screen: what patients paid for the doctor's completed consultations, by day, month or financial year."""
import calendar
from datetime import date, time, timedelta

from django.utils import timezone

from apps.consultations.models import Consultation

from .availability import local_datetime
from .models import Appointment

MAIN_CURRENCY = 'INR'
MAIN_SYMBOL = '\u20b9'
PERIODS = ('daily', 'monthly', 'financial_year')
FY_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]


def rupees(amount):
    from apps.pricing.service import format_amount

    return format_amount(amount, MAIN_SYMBOL)


def add_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def period_bounds(period, day):
    """(first day, day after the last day, label, previous period date, next period date)."""
    if period == 'daily':
        return day, day + timedelta(days=1), day.strftime('%d %b %Y'), day - timedelta(days=1), day + timedelta(days=1)
    if period == 'monthly':
        start = day.replace(day=1)
        return start, add_months(start, 1), start.strftime('%B %Y'), add_months(start, -1), add_months(start, 1)
    start_year = day.year if day.month >= 4 else day.year - 1
    start = date(start_year, 4, 1)
    end = date(start_year + 1, 4, 1)
    label = f'FY {start_year}-{str(start_year + 1)[-2:]}'
    return start, end, label, date(start_year - 1, 4, 1), end


def bucket_labels(period, start):
    if period == 'daily':
        return [time(hour).strftime('%I %p').lstrip('0') for hour in range(0, 24, 2)]
    if period == 'monthly':
        return [str(day) for day in range(1, calendar.monthrange(start.year, start.month)[1] + 1)]
    return [calendar.month_abbr[month] for month in FY_MONTHS]


def bucket_index(period, local):
    if period == 'daily':
        return local.hour // 2
    if period == 'monthly':
        return local.day - 1
    return FY_MONTHS.index(local.month)


def doctor_earnings(user, period, day):
    today = timezone.localdate()
    start, end, label, previous_day, next_day = period_bounds(period, day)
    appointments = Appointment.objects.filter(
        doctor=user, status=Appointment.Status.COMPLETED,
        slot_time__gte=local_datetime(start, time(0)), slot_time__lt=local_datetime(end, time(0)),
    ).select_related('consultation')

    labels = bucket_labels(period, start)
    chart = [{'label': text, 'amount': 0, 'count': 0} for text in labels]
    modes = {mode: {'mode': mode, 'label': text, 'amount': 0, 'count': 0} for mode, text in reversed(Consultation.Mode.choices)}
    other = {}
    total = count = 0
    for appointment in appointments:
        consultation = appointment.consultation
        amount = consultation.fee_charged
        if consultation.currency != MAIN_CURRENCY:
            entry = other.setdefault(consultation.currency, {'currency': consultation.currency, 'amount': 0, 'count': 0})
            entry['amount'] += amount
            entry['count'] += 1
            continue
        total += amount
        count += 1
        bucket = chart[bucket_index(period, timezone.localtime(appointment.slot_time))]
        bucket['amount'] += amount
        bucket['count'] += 1
        if consultation.mode in modes:
            modes[consultation.mode]['amount'] += amount
            modes[consultation.mode]['count'] += 1

    by_mode = []
    for entry in modes.values():
        share = round(entry['amount'] * 100 / total, 1) if total else 0.0
        by_mode.append({**entry, 'amount_display': rupees(entry['amount']), 'share_percent': share})
    average = round(total / count) if count else 0
    return {
        'period': period, 'label': label, 'start_date': start, 'end_date': end - timedelta(days=1),
        'is_current': start <= today < end, 'previous_date': previous_day,
        'next_date': next_day if next_day <= today else None,
        'currency': MAIN_CURRENCY, 'total_earned': total, 'total_earned_display': rupees(total),
        'consultations_count': count, 'average_per_consultation': average, 'average_display': rupees(average),
        'chart': chart, 'by_mode': by_mode, 'other_currencies': sorted(other.values(), key=lambda item: item['currency']),
    }
