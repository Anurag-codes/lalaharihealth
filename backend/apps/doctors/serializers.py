from rest_framework import serializers

from apps.treatments.models import TreatmentSystem

from .models import DoctorApplication, DoctorApplicationDocument


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
    consultation_fee = serializers.IntegerField(min_value=200, max_value=2000)
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
            'treatment_systems',
            'city',
            'message',
            'is_priority',
            'status',
            'created_at',
            'documents',
        ]
        read_only_fields = ['id', 'is_priority', 'status', 'created_at', 'documents']

    def validate(self, attrs):
        category = attrs.get('consultation_category')
        fee = attrs.get('consultation_fee')

        if category == DoctorApplication.ConsultationCategory.GENERAL and fee != 200:
            raise serializers.ValidationError({
                'consultation_fee': 'General Physician / General Doctor consultations are fixed at ₹200.'
            })

        if category == DoctorApplication.ConsultationCategory.SPECIALIST and (fee < 200 or fee > 2000 or fee % 100):
            raise serializers.ValidationError({
                'consultation_fee': 'Specialist consultation fees must be between ₹200 and ₹2,000 in ₹100 steps.'
            })

        return attrs
