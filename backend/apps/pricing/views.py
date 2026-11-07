from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.doctors.models import Speciality
from .serializers import ConsultationFeeQuerySerializer, ConsultationFeeSerializer, PricingQuerySerializer, PricingSerializer
from .service import consultation_fee_payload, pricing_payload, resolve_pricing

GENERAL_FEE_EXAMPLE = {
    'category': 'general', 'speciality_id': None, 'speciality_name': None, 'consultation_title': 'General Consultation',
    'country_code': 'IN', 'fee': 200, 'currency': 'INR', 'currency_symbol': '\u20b9', 'fee_display': '\u20b9200',
    'source': 'general_fee',
}

INDIA_EXAMPLE = {
    'country_code': 'IN', 'country_name': 'India', 'detected_country_code': 'IN', 'source': 'location', 'is_fallback': False,
    'currency': 'INR', 'currency_symbol': '\u20b9', 'general_fee': 200, 'general_fee_display': '\u20b9200',
    'doctor_share_percent': 75, 'platform_fee_percent': 25,
    'general_doctor_payout': '150.00', 'general_doctor_payout_display': '\u20b9150',
    'specialist_fee_min': 200, 'specialist_fee_max': 2000, 'specialist_fee_step': 100,
    'specialist_fee_range_display': '\u20b9200\u2013\u20b92,000',
}
US_EXAMPLE = {
    'country_code': 'US', 'country_name': 'United States', 'detected_country_code': 'US', 'source': 'location',
    'is_fallback': False, 'currency': 'USD', 'currency_symbol': '$', 'general_fee': 10, 'general_fee_display': '$10',
    'doctor_share_percent': 75, 'platform_fee_percent': 25,
    'general_doctor_payout': '7.50', 'general_doctor_payout_display': '$7.50',
    'specialist_fee_min': 10, 'specialist_fee_max': 100, 'specialist_fee_step': 5,
    'specialist_fee_range_display': '$10\u2013$100',
}


class PricingView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PricingSerializer

    @extend_schema(
        tags=['Pricing'], summary='General physician price for the user\'s location',
        description=(
            'Public, no login. Send the device/browser location as `lat` and `lng` (the country is found offline on our '
            'server; coordinates are not stored), or an ISO `country` code. With neither, or when that country has no '
            'pricing yet, India prices are returned (`source: "default"`, \u20b9200).\n\n'
            'App: call on the home screen and before booking, show `general_fee_display`, and send `country_code` '
            'in `POST /api/v1/consultations/` so checkout charges this amount in this currency. '
            'Specialist (Book Specialist) bookings are always charged in INR at the speciality\'s fixed fee; get the exact '
            'fee of any category from `GET /api/v1/pricing/consultation-fee/?category=`.\n\n'
            'For-doctors page: `specialist_fee_min/max/step` is the fee range a specialist may choose, and '
            '`general_doctor_payout_display` is what a general doctor receives after the platform fee.'
        ),
        parameters=[PricingQuerySerializer],
        examples=[
            OpenApiExample('India (location in Delhi or no location)', value=INDIA_EXAMPLE, response_only=True),
            OpenApiExample('United States (location in New York)', value=US_EXAMPLE, response_only=True),
            OpenApiExample(
                'Country without pricing falls back to India', response_only=True,
                value={**INDIA_EXAMPLE, 'detected_country_code': 'BR', 'source': 'default', 'is_fallback': True},
            ),
        ],
    )
    def get(self, request):
        query = PricingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        result = resolve_pricing(data.get('country'), data.get('lat'), data.get('lng'))
        return Response(self.get_serializer(pricing_payload(result)).data)


class ConsultationFeeView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ConsultationFeeSerializer

    @extend_schema(
        tags=['Pricing'], summary='Fixed consultation fee for a category (general or a speciality)',
        description=(
            'Public, no login. Call before booking to show the price; the same amount is locked when the case is '
            'submitted (`POST /api/v1/appointments/`) and charged at checkout. No doctor is chosen by the patient: staff '
            'assign a verified doctor of this category after payment.\n\n'
            '- `category=general`: the general physician fee stored for the country (`country`, default India).\n'
            '- `category=<speciality id or slug>`: always INR. The mode (most common value) of the consultation fees of '
            'the active, verified doctors of that speciality; on a tie the highest tied fee. If the speciality has no '
            'verified doctors yet, the fee stored on the speciality (`source: "speciality_fee"`).\n\n'
            '400 if the category is unknown or inactive.'
        ),
        parameters=[ConsultationFeeQuerySerializer],
        examples=[
            OpenApiExample('General physician, India', response_only=True, value=GENERAL_FEE_EXAMPLE),
            OpenApiExample('General physician, United States (?country=US)', response_only=True, value={
                **GENERAL_FEE_EXAMPLE, 'country_code': 'US', 'fee': 10, 'currency': 'USD', 'currency_symbol': '$',
                'fee_display': '$10',
            }),
            OpenApiExample('Dermatology (mode of doctor fees)', response_only=True, value={
                'category': 'dermatology', 'speciality_id': 2, 'speciality_name': 'Dermatology',
                'consultation_title': 'Skin Consultation', 'country_code': 'IN', 'fee': 500, 'currency': 'INR',
                'currency_symbol': '\u20b9', 'fee_display': '\u20b9500', 'source': 'mode',
            }),
        ],
    )
    def get(self, request):
        query = ConsultationFeeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        category = query.validated_data['category'].strip().lower()
        if category == 'general':
            payload = consultation_fee_payload(country_code=query.validated_data.get('country'))
        else:
            lookup = {'pk': int(category)} if category.isdigit() else {'slug': category}
            speciality = Speciality.objects.filter(is_active=True, **lookup).first()
            if speciality is None:
                raise serializers.ValidationError({'category': ['Unknown category. Use "general" or an active speciality id or slug.']})
            payload = consultation_fee_payload(speciality)
        return Response(self.get_serializer(payload).data)
