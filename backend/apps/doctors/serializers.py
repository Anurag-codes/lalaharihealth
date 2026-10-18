from rest_framework import serializers

from apps.treatments.models import TreatmentSystem

from .models import Speciality, DoctorApplication, DoctorApplicationDocument


class DoctorApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorApplicationDocument
        fields = ['id', 'file', 'uploaded_at']


class DoctorApplicationSubmissionSerializer(serializers.Serializer):
    """Request body for the public doctor application endpoint."""

    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=15)
    qualification = serializers.CharField(max_length=255)
    experience_years = serializers.IntegerField(min_value=0)
    specialization = serializers.CharField(max_length=150)
    consultation_category = serializers.ChoiceField(choices=DoctorApplication.ConsultationCategory.choices)
    consultation_fee = serializers.IntegerField(
        min_value=1, help_text='General: the country general fee. Specialist: within the country range and step (GET /api/v1/pricing/).',
    )
    country_code = serializers.RegexField(
        r'^[A-Za-z]{2}$', required=False,
        help_text='country_code from GET /api/v1/pricing/ for the doctor\'s location. Omit for India (INR).',
    )
    treatment_systems = serializers.ListField(
        child=serializers.ChoiceField(choices=TreatmentSystem.choices),
        allow_empty=False,
    )
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    documents = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        max_length=5,
        help_text='Optional supporting documents; submit at most five files.',
    )


class DoctorApplicationSerializer(serializers.ModelSerializer):
    treatment_systems = serializers.ListField(
        child=serializers.ChoiceField(choices=TreatmentSystem.choices),
        allow_empty=False,
    )
    documents = DoctorApplicationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = DoctorApplication
        fields = [
            'id',
            'full_name',
            'email',
            'phone_number',
            'qualification',
            'experience_years',
            'specialization',
            'consultation_category',
            'consultation_fee',
            'country_code',
            'currency',
            'treatment_systems',
            'city',
            'message',
            'is_priority',
            'status',
            'created_at',
            'documents',
        ]
        read_only_fields = ['id', 'is_priority', 'status', 'created_at', 'documents', 'currency']
        extra_kwargs = {'country_code': {'required': False}}

    def validate_country_code(self, value):
        from apps.pricing.service import active_pricing

        value = value.upper()
        if active_pricing(value) is None:
            raise serializers.ValidationError('Pricing is not available for this country.')
        return value

    def validate(self, attrs):
        from apps.pricing.service import default_pricing, format_amount, pricing_for

        category = attrs.get('consultation_category')
        fee = attrs.get('consultation_fee')
        pricing = pricing_for(attrs['country_code']) if attrs.get('country_code') else default_pricing()
        attrs['country_code'] = pricing.country_code
        attrs['currency'] = pricing.currency
        money = lambda amount: format_amount(amount, pricing.currency_symbol)  # noqa: E731

        if category == DoctorApplication.ConsultationCategory.GENERAL and fee != pricing.general_fee:
            raise serializers.ValidationError({
                'consultation_fee': f'General Physician / General Doctor consultations are fixed at {money(pricing.general_fee)}.'
            })

        low, high, step = pricing.specialist_fee_min, pricing.specialist_fee_max, pricing.specialist_fee_step
        if category == DoctorApplication.ConsultationCategory.SPECIALIST and (fee < low or fee > high or (fee - low) % step):
            raise serializers.ValidationError({
                'consultation_fee': (
                    f'Specialist consultation fees must be between {money(low)} and {money(high)} in {money(step)} steps.'
                )
            })

        return attrs


class SpecialitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True, help_text='Consultation title shown on cards, e.g. "Skin Consultation"')
    fee = serializers.IntegerField(read_only=True, help_text='INR rupees per consultation (all countries)')
    currency = serializers.SerializerMethodField()
    fee_display = serializers.SerializerMethodField(help_text='e.g. "\u20b9400"')

    class Meta:
        model = Speciality
        fields = ['id', 'name', 'slug', 'short_name', 'title', 'description', 'fee', 'currency', 'fee_display']
        read_only_fields = fields

    def get_currency(self, obj) -> str:
        return 'INR'

    def get_fee_display(self, obj) -> str:
        from apps.pricing.service import format_amount

        return format_amount(obj.fee, '\u20b9')
