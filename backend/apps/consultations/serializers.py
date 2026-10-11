from pathlib import Path

from rest_framework import serializers

from .models import Consultation, ConsultationDocument


class PatientDetailsSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(max_length=150)
    patient_age = serializers.IntegerField(min_value=0, max_value=120)
    patient_gender = serializers.ChoiceField(choices=Consultation._meta.get_field('patient_gender').choices)
    patient_phone = serializers.RegexField(r'^\+?[0-9]{10,15}$', max_length=16)

    class Meta:
        model = Consultation
        fields = ['patient_name', 'patient_age', 'patient_gender', 'patient_phone', 'mode']


class HistorySerializer(serializers.ModelSerializer):
    duration_value = serializers.IntegerField(min_value=1, max_value=10000, required=True)
    duration_unit = serializers.ChoiceField(choices=Consultation._meta.get_field('duration_unit').choices)
    ongoing_medication = serializers.BooleanField(required=True)
    treatment_details = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    symptoms = serializers.CharField(max_length=10000, required=False, allow_blank=True)

    class Meta:
        model = Consultation
        fields = ['condition', 'symptoms', 'duration_value', 'duration_unit', 'ongoing_medication', 'treatment_details']

    def validate_condition(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError('Select an active condition.')
        return value


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Maximum file size is 10 MB.')
        signatures = {
            '.pdf': [b'%PDF-'], '.png': [b'\x89PNG\r\n\x1a\n'],
            '.jpg': [b'\xff\xd8\xff'], '.jpeg': [b'\xff\xd8\xff'],
        }
        extension = Path(value.name).suffix.lower()
        header = value.read(8)
        value.seek(0)
        if extension not in signatures or not any(header.startswith(signature) for signature in signatures[extension]):
            raise serializers.ValidationError('Upload a valid PDF, PNG or JPG file.')
        return value


class DocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationDocument
        fields = ['id', 'original_name', 'uploaded_at', 'download_url']

    def get_download_url(self, obj) -> str:
        request = self.context['request']
        return request.build_absolute_uri(f'/api/v1/consultations/{obj.consultation_id}/documents/{obj.pk}/download/')


class ConsultationSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient_name', 'patient_age', 'patient_gender', 'patient_phone', 'mode',
            'condition', 'symptoms', 'duration_value', 'duration_unit', 'ongoing_medication',
            'treatment_details', 'history_completed', 'status', 'fee_charged', 'scheduled_at',
            'documents', 'created_at',
        ]
        read_only_fields = fields