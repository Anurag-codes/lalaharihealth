from rest_framework import serializers


class PricingQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90, required=False, help_text='Device/browser latitude')
    lng = serializers.FloatField(min_value=-180, max_value=180, required=False, help_text='Device/browser longitude')
    country = serializers.RegexField(
        r'^[A-Za-z]{2}$', required=False, help_text='ISO country code, e.g. US. Ignored when lat/lng are sent.',
    )

    def validate(self, attrs):
        if ('lat' in attrs) != ('lng' in attrs):
            raise serializers.ValidationError('Send both lat and lng, or neither.')
        return attrs


class PricingSerializer(serializers.Serializer):
    country_code = serializers.CharField(help_text='Country whose prices are shown. Send this as country_code in booking step 1.')
    country_name = serializers.CharField()
    detected_country_code = serializers.CharField(allow_null=True, help_text='Country found from the location or query; null if none')
    source = serializers.ChoiceField(
        choices=['location', 'country', 'default'],
        help_text='default = location unknown or that country has no pricing yet, so India prices are shown',
    )
    is_fallback = serializers.BooleanField()
    currency = serializers.CharField(help_text='ISO 4217, e.g. INR, USD')
    currency_symbol = serializers.CharField()
    general_fee = serializers.IntegerField(help_text='General physician consultation fee, whole currency units')
    general_fee_display = serializers.CharField(help_text='e.g. "\u20b9200", "$10", "AED 40"')
    doctor_share_percent = serializers.IntegerField()
    platform_fee_percent = serializers.IntegerField()
    general_doctor_payout = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=True)
    general_doctor_payout_display = serializers.CharField()
    specialist_fee_min = serializers.IntegerField()
    specialist_fee_max = serializers.IntegerField()
    specialist_fee_step = serializers.IntegerField()
    specialist_fee_range_display = serializers.CharField()


class ConsultationFeeQuerySerializer(serializers.Serializer):
    category = serializers.CharField(
        max_length=120,
        help_text='"general" for a general physician, or a speciality id or slug from GET /api/v1/doctors/specialities/',
    )
    country = serializers.RegexField(
        r'^[A-Za-z]{2}$', required=False,
        help_text='ISO country code for general bookings (the country_code from GET /api/v1/pricing/). Default India. '
        'Ignored for specialities, which are always INR.',
    )


class ConsultationFeeSerializer(serializers.Serializer):
    category = serializers.CharField(help_text='"general" or the speciality slug')
    speciality_id = serializers.IntegerField(allow_null=True, help_text='null for general')
    speciality_name = serializers.CharField(allow_null=True)
    consultation_title = serializers.CharField(help_text='"General Consultation" or e.g. "Skin Consultation"')
    country_code = serializers.CharField(help_text='Country whose general fee applies; IN for specialities')
    fee = serializers.IntegerField(help_text='Fixed amount charged, whole currency units')
    currency = serializers.CharField(help_text='ISO 4217, e.g. INR, USD')
    currency_symbol = serializers.CharField()
    fee_display = serializers.CharField(help_text='e.g. "\u20b9200", "$10"')
    source = serializers.ChoiceField(
        choices=['general_fee', 'mode', 'speciality_fee'],
        help_text='general_fee = country general physician fee; mode = most common fee of the verified doctors of this '
        'speciality (highest on a tie); speciality_fee = no verified doctors yet, so the fee stored on the speciality',
    )
