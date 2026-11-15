"""Yearly subscription: unlimited general physician consultations for the buyer themself (not family members)."""
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from apps.pricing.service import format_amount
from .models import Subscription

RENEWAL_WINDOW_DAYS = 30


def is_coverable(consultation):
    """General physician consultation for the account holder themself."""
    return (
        consultation.speciality_id is None and consultation.family_member_id is None
        and consultation.patient_relation == 'self'
    )


def covering_subscription(user, at):
    return Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, starts_at__lte=at, ends_at__gt=at,
    ).order_by('starts_at').first()


def subscription_for_booking(consultation, starts_at):
    if not is_coverable(consultation):
        return None
    return covering_subscription(consultation.patient, starts_at)


def active_until(user, now=None):
    """End of paid cover (renewals stack, so this includes a renewal already bought)."""
    now = now or timezone.now()
    return Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, ends_at__gt=now,
    ).aggregate(end=Max('ends_at'))['end']


def purchase_block_reason(user, pricing, now=None):
    now = now or timezone.now()
    if not pricing.subscription_fee:
        return 'The yearly plan is not available right now.'
    until = active_until(user, now)
    if until and until - now > timedelta(days=RENEWAL_WINDOW_DAYS):
        local = timezone.localtime(until)
        return f'Your plan is active until {local:%d %b %Y}. You can renew in its last {RENEWAL_WINDOW_DAYS} days.'
    return None


def plan_payload(user, pricing):
    now = timezone.now()
    fee = pricing.subscription_fee
    return {
        'available': bool(fee), 'country_code': pricing.country_code,
        'amount': fee or None, 'currency': pricing.currency if fee else None,
        'amount_display': format_amount(fee, pricing.currency_symbol) if fee else None,
        'valid_days': Subscription.VALID_DAYS,
        'is_active': covering_subscription(user, now) is not None,
        'active_until': active_until(user, now),
        'can_purchase': purchase_block_reason(user, pricing, now) is None,
    }
