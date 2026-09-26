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
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    qualification = serializers.CharField(max_length=255)
    experience_years = serializers.IntegerField(min_value=0)
    specialization = serializers.CharField(max_length=150)
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
            'treatment_systems',
            'city',
            'message',
            'is_priority',
            'status',
            'created_at',
            'documents',
        ]
        read_only_fields = ['id', 'is_priority', 'status', 'created_at', 'documents']
