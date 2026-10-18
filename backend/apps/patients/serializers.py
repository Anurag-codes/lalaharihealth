from datetime import date
from pathlib import Path

from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from .models import FamilyMember, PatientProfile, years_since

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_SIGNATURES = {'.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}


def validate_birth_date(value):
    if value > date.today():
        raise serializers.ValidationError('Date of birth cannot be in the future.')
    if years_since(value) > 120:
        raise serializers.ValidationError('Enter a valid date of birth.')
    return value


class LanguageOptionSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class PatientProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', max_length=150, required=False, allow_blank=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    is_email_verified = serializers.BooleanField(source='user.is_email_verified', read_only=True)
    is_phone_verified = serializers.BooleanField(source='user.is_phone_verified', read_only=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=PatientProfile.Gender.choices, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True, validators=[validate_birth_date])
    age = serializers.SerializerMethodField()
    preferred_language = serializers.ChoiceField(choices=PatientProfile.Language.choices, required=False)
    preferred_language_label = serializers.CharField(source='get_preferred_language_display', read_only=True)
    available_languages = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    membership_label = serializers.SerializerMethodField()
    family_member_count = serializers.SerializerMethodField()
    medical_record_count = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    def get_age(self, obj) -> int | None:
        return years_since(obj.date_of_birth)

    @extend_schema_field(LanguageOptionSerializer(many=True))
    def get_available_languages(self, obj):
        return [{'code': code, 'label': label} for code, label in PatientProfile.Language.choices]

    def get_photo_url(self, obj) -> str | None:
        if not obj.profile_photo:
            return None
        return self.context['request'].build_absolute_uri('/api/v1/patients/profile/photo/')

    def get_membership_label(self, obj) -> str:
        return 'LalaHari Health Beneficiary'

    def get_family_member_count(self, obj) -> int:
        return obj.user.family_members.count()

    def get_medical_record_count(self, obj) -> int:
        return obj.user.consultations_as_patient.exclude(status='draft').count()

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        if user_data:
            instance.user.save(update_fields=list(user_data))
        if 'city' in validated_data:
            instance.user.city = validated_data['city']
            instance.user.save(update_fields=['city'])
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class ProfilePhotoUploadSerializer(serializers.Serializer):
    photo = serializers.ImageField(help_text='PNG or JPG, up to 5 MB.')

    def validate_photo(self, value):
        if value.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError('Maximum photo size is 5 MB.')
        extension = Path(value.name).suffix.lower()
        header = value.read(8)
        value.seek(0)
        if extension not in PHOTO_SIGNATURES or not header.startswith(PHOTO_SIGNATURES[extension]):
            raise serializers.ValidationError('Upload a valid PNG or JPG photo.')
        try:
            with Image.open(value) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise serializers.ValidationError('Upload a valid PNG or JPG photo.') from None
        finally:
            value.seek(0)
        return value


class FamilyMemberSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    relation_label = serializers.CharField(source='get_relation_display', read_only=True)
    gender_label = serializers.CharField(source='get_gender_display', read_only=True)
    date_of_birth = serializers.DateField(validators=[validate_birth_date])
    phone_number = serializers.RegexField(r'^\+?[0-9]{10,15}$', max_length=16, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=150, trim_whitespace=True)

    class Meta:
        model = FamilyMember
        fields = [
            'id', 'full_name', 'relation', 'relation_label', 'date_of_birth', 'age', 'gender', 'gender_label',
            'phone_number', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'age', 'relation_label', 'gender_label', 'created_at', 'updated_at']


class BookingPatientSerializer(serializers.Serializer):
    family_member_id = serializers.IntegerField(allow_null=True, help_text='Send as family_member_id in step 1; null = Myself')
    name = serializers.CharField(allow_blank=True)
    age = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField(allow_blank=True)
    gender_label = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    relation = serializers.CharField()
    relation_label = serializers.CharField(help_text='"Myself", "Spouse", "Son" ...')
    subtitle = serializers.CharField(help_text='Ready-made card line, e.g. "Myself · 25 years · Male"')
    details_complete = serializers.BooleanField(
        help_text='False for Myself when name/age/gender/phone is unknown: show the Patient Details form instead.',
    )
