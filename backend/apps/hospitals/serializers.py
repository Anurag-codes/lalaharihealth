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


class HospitalApplicationSubmissionSerializer(HospitalApplicationSerializer):
    """Documents the multipart request: the form fields plus up to five files named `documents`."""

    documents = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text='Optional supporting documents; submit at most five files.',
    )

    class Meta(HospitalApplicationSerializer.Meta):
        fields = [name for name in HospitalApplicationSerializer.Meta.fields if name not in {'id', 'is_priority', 'status', 'created_at'}]
        read_only_fields = []
