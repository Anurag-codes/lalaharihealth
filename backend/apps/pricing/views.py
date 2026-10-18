from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import PricingQuerySerializer, PricingSerializer
from .service import pricing_payload, resolve_pricing

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
            'Specialist (Book Specialist) bookings are always charged in INR at the speciality fee.\n\n'
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
