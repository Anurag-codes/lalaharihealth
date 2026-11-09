"""Doctor mobile app: profile, verification documents and weekly availability."""
from datetime import datetime
from pathlib import Path

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import DoctorAvailability, DoctorDocument, DoctorProfile, Speciality
from .onboarding import onboarding_status
from .serializers import validate_photo

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_OTHER_DOCUMENTS = 5
AVAILABILITY_STEP_MINUTES = 15
DOCUMENT_SIGNATURES = {
    '.pdf': [b'%PDF-'], '.png': [b'\x89PNG\r\n\x1a\n'], '.jpg': [b'\xff\xd8\xff'], '.jpeg': [b'\xff\xd8\xff'],
}
LOCKED_WHEN_VERIFIED = ('registration_number', 'qualification', 'speciality_id')
QUALIFICATIONS = [
    'MBBS', 'BDS', 'BAMS', 'BHMS', 'BUMS', 'BSMS', 'BNYS', 'MD', 'MS', 'DNB', 'DM', 'MCh', 'MDS',
    'MD (Ayurveda)', 'MS (Ayurveda)', 'MD (Homoeopathy)', 'MD (Unani)', 'Diploma', 'Fellowship', 'PhD',
]


def time_display(value):
    return value.strftime('%I:%M %p')


class SpecialityRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speciality
        fields = ['id', 'name']
        read_only_fields = fields


class DoctorDocumentSerializer(serializers.ModelSerializer):
    document_type_label = serializers.CharField(source='get_document_type_display', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DoctorDocument
        fields = ['id', 'document_type', 'document_type_label', 'original_name', 'uploaded_at', 'download_url']
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        path = f'/api/v1/doctors/me/documents/{obj.pk}/download/'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path


class OnboardingSerializer(serializers.Serializer):
    profile_completed = serializers.BooleanField(help_text='Name, age, gender, registration number and qualification are filled')
    registration_certificate_uploaded = serializers.BooleanField()
    availability_set = serializers.BooleanField()
    is_complete = serializers.BooleanField()
    next_step = serializers.ChoiceField(
        choices=['profile', 'availability', 'done'],
        help_text='Screen to open after sign-in: profile = Step 2 Professional Details, availability = Step 3, done = Home',
    )


class DoctorMeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user_id', read_only=True, help_text='Doctor user id (used by staff to assign appointments)')
    profile_id = serializers.IntegerField(source='pk', read_only=True)
    full_name = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    photo_url = serializers.SerializerMethodField()
    gender = serializers.ChoiceField(choices=DoctorProfile.Gender.choices, allow_blank=True, read_only=True)
    registration_number = serializers.CharField(read_only=True, allow_null=True)
    speciality = SpecialityRefSerializer(read_only=True, allow_null=True, help_text='null = General Physician')
    verification_status_label = serializers.CharField(source='get_verification_status_display', read_only=True)
    is_verified = serializers.BooleanField(read_only=True, help_text='Only verified doctors receive appointments')
    documents = DoctorDocumentSerializer(many=True, read_only=True)
    onboarding = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'profile_id', 'full_name', 'first_name', 'last_name', 'phone_number', 'email', 'photo_url',
            'age', 'gender', 'registration_number', 'qualification', 'speciality', 'specialization',
            'experience_years', 'city', 'verification_status', 'verification_status_label', 'is_verified',
            'documents', 'onboarding',
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    def get_photo_url(self, obj) -> str | None:
        if not obj.profile_photo:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.profile_photo.url) if request else obj.profile_photo.url

    @extend_schema_field(OnboardingSerializer)
    def get_onboarding(self, obj):
        return onboarding_status(obj)


class DoctorMeUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False, help_text='"Dr." is added by the app; send the name only')
    age = serializers.IntegerField(min_value=18, max_value=100, required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=DoctorProfile.Gender.choices, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text='Medical Council Registration Number')
    qualification = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text='e.g. MBBS, MD. Suggestions: GET /api/v1/doctors/qualifications/')
    speciality_id = serializers.IntegerField(
        required=False, allow_null=True, help_text='id from GET /api/v1/doctors/specialities/; null = General Physician',
    )
    experience_years = serializers.IntegerField(min_value=0, max_value=70, required=False)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate(self, attrs):
        unsupported = set(self.initial_data) - set(self.fields)
        if unsupported:
            raise serializers.ValidationError({field: 'This field cannot be updated here.' for field in sorted(unsupported)})
        profile = self.instance
        if profile.verification_status == DoctorProfile.VerificationStatus.VERIFIED:
            current = {
                'registration_number': profile.registration_number or '', 'qualification': profile.qualification,
                'speciality_id': profile.speciality_id,
            }
            locked = {
                field: 'Verified details cannot be changed in the app. Contact support to update them.'
                for field in LOCKED_WHEN_VERIFIED if field in attrs and attrs[field] != current[field]
            }
            if locked:
                raise serializers.ValidationError(locked)
        return attrs

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter your full name.')
        return value

    def validate_registration_number(self, value):
        value = value.strip()
        if value and DoctorProfile.objects.filter(registration_number__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('This registration number is already registered with another doctor.')
        return value

    def validate_speciality_id(self, value):
        if value is not None and not Speciality.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('Choose a speciality from the list.')
        return value

    def update(self, profile, validated_data):
        from .onboarding import GENERAL_PHYSICIAN, split_name

        user = profile.user
        if 'full_name' in validated_data:
            user.first_name, user.last_name = split_name(validated_data.pop('full_name'))
        if 'city' in validated_data:
            user.city = validated_data['city']
        user.save(update_fields=['first_name', 'last_name', 'city'])
        if 'registration_number' in validated_data:
            validated_data['registration_number'] = validated_data['registration_number'] or None
        if 'speciality_id' in validated_data:
            speciality_id = validated_data['speciality_id']
            profile.specialization = (
                Speciality.objects.get(pk=speciality_id).name if speciality_id else GENERAL_PHYSICIAN
            )
        for field, value in validated_data.items():
            setattr(profile, field, value)
        profile.save()
        return profile


class DoctorPhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(help_text='JPG, PNG or WEBP, up to 5 MB')

    def validate_photo(self, value):
        return validate_photo(value)


class DoctorDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=DoctorDocument.DocumentType.choices)
    file = serializers.FileField(help_text='PDF, JPG or PNG, up to 10 MB')

    def validate_file(self, value):
        if value.size > MAX_DOCUMENT_BYTES:
            raise serializers.ValidationError('Maximum file size is 10 MB.')
        extension = Path(value.name).suffix.lower()
        header = value.read(8)
        value.seek(0)
        if extension not in DOCUMENT_SIGNATURES or not any(header.startswith(sig) for sig in DOCUMENT_SIGNATURES[extension]):
            raise serializers.ValidationError('Upload a valid PDF, PNG or JPG file.')
        return value


class AvailabilityWindowSerializer(serializers.Serializer):
    start_time = serializers.TimeField(format='%H:%M', help_text='24-hour HH:MM on a 15-minute boundary, e.g. 07:00')
    end_time = serializers.TimeField(format='%H:%M', help_text='Later than start_time, e.g. 10:00')
    display = serializers.SerializerMethodField()

    def get_display(self, obj) -> str:
        return f'{time_display(obj["start_time"])} - {time_display(obj["end_time"])}'

    def validate(self, attrs):
        for field in ('start_time', 'end_time'):
            value = attrs[field]
            if value.second or value.microsecond or value.minute % AVAILABILITY_STEP_MINUTES:
                raise serializers.ValidationError({field: 'Use a 15-minute time, e.g. 07:00 or 07:15.'})
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return attrs


class AvailabilityDaySerializer(serializers.Serializer):
    weekday = serializers.ChoiceField(choices=DoctorAvailability.Weekday.choices, help_text='0 = Monday ... 6 = Sunday')
    label = serializers.CharField(read_only=True)
    is_open = serializers.BooleanField()
    windows = AvailabilityWindowSerializer(many=True, required=False, default=list)
    total_hours = serializers.FloatField(read_only=True)


def window_minutes(window):
    start, end = (datetime.combine(datetime.min, window[key]) for key in ('start_time', 'end_time'))
    return int((end - start).total_seconds() // 60)


class AvailabilityWeekSerializer(serializers.Serializer):
    days = AvailabilityDaySerializer(many=True, help_text='Send all 7 days, or only open days (missing days are closed)')
    min_daily_hours = serializers.IntegerField(read_only=True)
    max_windows_per_day = serializers.IntegerField(read_only=True)
    timezone = serializers.CharField(read_only=True)

    def validate_days(self, days):
        seen = set()
        errors = {}
        max_windows = settings.DOCTOR_AVAILABILITY_MAX_WINDOWS
        min_minutes = settings.DOCTOR_MIN_DAILY_AVAILABILITY_HOURS * 60
        for day in days:
            weekday = day['weekday']
            label = DoctorAvailability.Weekday(weekday).label
            if weekday in seen:
                errors[label] = 'This day is sent more than once.'
                continue
            seen.add(weekday)
            if not day['is_open']:
                continue
            windows = sorted(day['windows'], key=lambda window: window['start_time'])
            if not windows:
                errors[label] = 'Add at least one time window or turn this day off.'
            elif len(windows) > max_windows:
                errors[label] = f'Add at most {max_windows} time windows per day.'
            elif any(later['start_time'] < earlier['end_time'] for earlier, later in zip(windows, windows[1:])):
                errors[label] = 'Time windows overlap.'
            elif sum(window_minutes(window) for window in windows) < min_minutes:
                errors[label] = f'Open days require at least {settings.DOCTOR_MIN_DAILY_AVAILABILITY_HOURS} hours.'
            day['windows'] = windows
        if errors:
            raise serializers.ValidationError(errors)
        if not any(day['is_open'] for day in days):
            raise serializers.ValidationError('Open at least one day.')
        return days


def availability_payload(profile):
    windows = {}
    for window in profile.availability_windows.all():
        windows.setdefault(window.weekday, []).append({'start_time': window.start_time, 'end_time': window.end_time})
    days = []
    for weekday, label in DoctorAvailability.Weekday.choices:
        day_windows = windows.get(weekday, [])
        days.append({
            'weekday': weekday, 'label': label, 'is_open': bool(day_windows), 'windows': day_windows,
            'total_hours': round(sum(window_minutes(window) for window in day_windows) / 60, 2),
        })
    return AvailabilityWeekSerializer({
        'days': days, 'min_daily_hours': settings.DOCTOR_MIN_DAILY_AVAILABILITY_HOURS,
        'max_windows_per_day': settings.DOCTOR_AVAILABILITY_MAX_WINDOWS, 'timezone': settings.TIME_ZONE,
    }).data


class QualificationSerializer(serializers.Serializer):
    name = serializers.CharField()
