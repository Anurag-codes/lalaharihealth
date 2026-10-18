from rest_framework import serializers

from apps.treatments.models import TreatmentSystem

from .models import Speciality, DoctorApplication, DoctorApplicationDocument


MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_photo(photo):
    if photo is None:
        return photo
    if photo.size > MAX_PHOTO_BYTES:
        raise serializers.ValidationError('Photo must be 5 MB or smaller.')
    image = getattr(photo, 'image', None)
    if image is None or image.format not in PHOTO_FORMATS:
        raise serializers.ValidationError('Upload a JPG, PNG or WEBP photo.')
    return photo


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
    photo = serializers.ImageField(
        required=False,
        help_text='Optional profile photo (JPG, PNG or WEBP, up to 5 MB). Shown on the website after approval.',
    )
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
            'photo',
            'is_priority',
            'status',
            'created_at',
            'documents',
        ]
        read_only_fields = ['id', 'is_priority', 'status', 'created_at', 'documents', 'currency']
        extra_kwargs = {'country_code': {'required': False}}

    def validate_photo(self, value):
        return validate_photo(value)

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


class FeaturedDoctorSerializer(serializers.ModelSerializer):
    """Public card data for an approved doctor. Contact details and documents are never exposed."""

    name = serializers.CharField(source='full_name', read_only=True)
    treatment_systems = serializers.ListField(child=serializers.CharField(), read_only=True)
    fee_display = serializers.SerializerMethodField(help_text='Specialist fee with currency symbol, e.g. "\u20b9500"')
    photo_url = serializers.SerializerMethodField(help_text='Absolute photo URL, or null when no photo was uploaded')

    class Meta:
        model = DoctorApplication
        fields = [
            'id', 'name', 'qualification', 'specialization', 'experience_years', 'consultation_category',
            'treatment_systems', 'consultation_fee', 'currency', 'fee_display', 'photo_url',
        ]
        read_only_fields = fields

    def get_fee_display(self, obj) -> str:
        from apps.pricing.service import format_amount, pricing_for

        pricing = pricing_for(obj.country_code)
        symbol = pricing.currency_symbol if pricing.currency == obj.currency else obj.currency
        return format_amount(obj.consultation_fee, symbol)

    def get_photo_url(self, obj) -> str | None:
        if not obj.photo:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url


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
