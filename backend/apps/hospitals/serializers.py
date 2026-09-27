from rest_framework import serializers

from .models import HospitalApplication, HospitalApplicationDocument


class HospitalApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalApplicationDocument
        fields = ['id', 'file', 'uploaded_at']


class HospitalApplicationSerializer(serializers.ModelSerializer):
    documents = HospitalApplicationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = HospitalApplication
        fields = [
            'id',
            'facility_name',
            'contact_person_name',
            'email',
            'phone_number',
            'city',
            'address',
            'specialties',
            'bed_count',
            'message',
            'is_priority',
            'status',
            'created_at',
            'documents',
        ]
        read_only_fields = ['id', 'is_priority', 'status', 'created_at', 'documents']
