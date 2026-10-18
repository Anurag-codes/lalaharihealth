"""Country pricing lookup: location -> country -> general physician fee in local currency."""
import logging
import threading
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .models import CountryPricing

logger = logging.getLogger(__name__)

DOCTOR_SHARE_PERCENT = 75
PLATFORM_FEE_PERCENT = 100 - DOCTOR_SHARE_PERCENT

# ISO 4217 minor-unit exponents that differ from 2 (Razorpay amounts are in the smallest unit).
ZERO_DECIMAL_CURRENCIES = {'BIF', 'CLP', 'DJF', 'GNF', 'ISK', 'JPY', 'KMF', 'KRW', 'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF', 'XOF', 'XPF'}
THREE_DECIMAL_CURRENCIES = {'BHD', 'IQD', 'JOD', 'KWD', 'LYD', 'OMR', 'TND'}

# Used only if the database has no default row (e.g. before migrations ran).
FALLBACK = CountryPricing(
    country_code='IN', country_name='India', currency='INR', currency_symbol='\u20b9', general_fee=200,
    specialist_fee_min=200, specialist_fee_max=2000, specialist_fee_step=100, is_default=True, is_active=True,
)


def minor_unit_factor(currency):
    if currency in ZERO_DECIMAL_CURRENCIES:
        return 1
    if currency in THREE_DECIMAL_CURRENCIES:
        return 1000
    return 100


def to_minor_units(amount, currency):
    return int(amount) * minor_unit_factor(currency)


def format_amount(amount, symbol):
    amount = Decimal(amount)
    text = f'{amount:,.0f}' if amount == amount.to_integral_value() else f'{amount:,.2f}'
    # Letter symbols such as "AED" read better with a space.
    return f'{symbol} {text}' if symbol[-1:].isalpha() else f'{symbol}{text}'


def doctor_payout(fee):
    return (Decimal(fee) * DOCTOR_SHARE_PERCENT / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def default_pricing():
    return CountryPricing.objects.filter(is_default=True).first() or FALLBACK


def active_pricing(country_code):
    if not country_code:
        return None
    return CountryPricing.objects.filter(country_code=country_code.upper(), is_active=True).first()


def pricing_for(country_code):
    """Active pricing for this country, else the default (India)."""
    return active_pricing(country_code) or default_pricing()


_geocoder_lock = threading.Lock()


def country_from_coordinates(latitude, longitude):
    """Offline reverse geocoding (GeoNames data bundled with reverse_geocode). Coordinates are never stored or sent out."""
    try:
        import reverse_geocode
    except ImportError:  # pragma: no cover - dependency is in requirements.txt
        logger.error('reverse_geocode is not installed; location pricing falls back to the default country.')
        return None
    with _geocoder_lock:
        result = reverse_geocode.get((float(latitude), float(longitude)))
    return (result or {}).get('country_code') or None


@dataclass
class PricingResult:
    pricing: CountryPricing
    detected_country_code: str | None
    source: str  # location, country or default


def resolve_pricing(country_code=None, latitude=None, longitude=None):
    detected, source = None, 'default'
    if latitude is not None and longitude is not None:
        detected, source = country_from_coordinates(latitude, longitude), 'location'
    elif country_code:
        detected, source = country_code.upper(), 'country'
    pricing = active_pricing(detected)
    if pricing is None:
        return PricingResult(default_pricing(), detected, 'default')
    return PricingResult(pricing, detected, source)


def pricing_payload(result):
    pricing = result.pricing
    symbol = pricing.currency_symbol
    payout = doctor_payout(pricing.general_fee)
    return {
        'country_code': pricing.country_code,
        'country_name': pricing.country_name,
        'detected_country_code': result.detected_country_code,
        'source': result.source,
        'is_fallback': result.source == 'default',
        'currency': pricing.currency,
        'currency_symbol': symbol,
        'general_fee': pricing.general_fee,
        'general_fee_display': format_amount(pricing.general_fee, symbol),
        'doctor_share_percent': DOCTOR_SHARE_PERCENT,
        'platform_fee_percent': PLATFORM_FEE_PERCENT,
        'general_doctor_payout': str(payout),
        'general_doctor_payout_display': format_amount(payout, symbol),
        'specialist_fee_min': pricing.specialist_fee_min,
        'specialist_fee_max': pricing.specialist_fee_max,
        'specialist_fee_step': pricing.specialist_fee_step,
        'specialist_fee_range_display': (
            f'{format_amount(pricing.specialist_fee_min, symbol)}\u2013{format_amount(pricing.specialist_fee_max, symbol)}'
        ),
    }
