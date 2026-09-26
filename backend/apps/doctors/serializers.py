from rest_framework import serializers

from apps.treatments.models import TreatmentSystem

from .models import DoctorApplication, DoctorApplicationDocument


class DoctorApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorApplicationDocument
        fields = ['id', 'file', 'uploaded_at']


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
