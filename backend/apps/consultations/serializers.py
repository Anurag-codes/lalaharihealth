from pathlib import Path

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.doctors.models import Speciality
from apps.patients.models import FamilyMember
from .models import Consultation, ConsultationDocument, PrescriptionItem


def self_booking_defaults(user):
    """Patient details for "Myself", from the account profile and the latest own booking."""
    from apps.patients.models import years_since

    profile = getattr(user, 'patient_profile', None)
    last = (
        Consultation.objects.filter(patient=user, patient_relation='self').exclude(patient_name='')
        .order_by('-created_at').first()
    )
    age = years_since(profile.date_of_birth) if profile and profile.date_of_birth else None
    if age is None and last and last.patient_age is not None:
        age = last.patient_age
    return {
        'patient_name': user.get_full_name() or (last.patient_name if last else ''),
        'patient_age': age,
        'patient_gender': (profile.gender if profile and profile.gender else '') or (last.patient_gender if last else ''),
        'patient_phone': user.phone_number or (last.patient_phone if last else ''),
    }


def remember_self_details(user, consultation):
    """Fill blank account name/gender from the first "Myself" booking so later bookings can skip the form."""
    from apps.patients.models import PatientProfile

    if consultation.patient_relation != 'self':
        return
    if not user.first_name and not user.last_name and consultation.patient_name:
        first, _, last = consultation.patient_name.strip().partition(' ')
        user.first_name, user.last_name = first[:150], last.strip()[:150]
        user.save(update_fields=['first_name', 'last_name'])
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    if not profile.gender and consultation.patient_gender in PatientProfile.Gender.values:
        profile.gender = consultation.patient_gender
        profile.save(update_fields=['gender'])


class PatientDetailsSerializer(serializers.ModelSerializer):
    family_member_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, write_only=True,
        help_text=(
            'Select Patient screen. A family member id books for that member; null or omitted books for yourself. '
            'Blank patient fields are filled from the member, or for yourself from your profile and latest booking. '
            'If anything is still unknown the response is 400 listing the missing fields, so show the Patient Details form.'
        ),
    )
    patient_name = serializers.CharField(max_length=150, required=False)
    patient_age = serializers.IntegerField(min_value=0, max_value=120, required=False)
    patient_gender = serializers.ChoiceField(choices=Consultation._meta.get_field('patient_gender').choices, required=False)
    patient_phone = serializers.RegexField(r'^\+?[0-9]{10,15}$', max_length=16, required=False)
    speciality = serializers.PrimaryKeyRelatedField(
        queryset=Speciality.objects.filter(is_active=True), required=False, allow_null=True,
        help_text='Book Specialist: id from GET /api/v1/doctors/specialities/. Omit or null for Book Appointment (general physician).',
    )
    country_code = serializers.RegexField(
        r'^[A-Za-z]{2}$', required=False, allow_blank=True,
        help_text=(
            'country_code from GET /api/v1/pricing/ for the user\'s location. Sets the general physician fee and '
            'currency charged at checkout. Omit for India (INR). Specialist bookings are always INR.'
        ),
    )

    class Meta:
        model = Consultation
        fields = [
            'family_member_id', 'speciality', 'country_code', 'patient_name', 'patient_age', 'patient_gender',
            'patient_phone', 'mode',
        ]

    def validate_country_code(self, value):
        from apps.pricing.service import active_pricing

        value = value.upper()
        if value and active_pricing(value) is None:
            raise serializers.ValidationError('Pricing is not available for this country. Use country_code from GET /api/v1/pricing/.')
        return value

    def validate(self, attrs):
        request = self.context['request']
        if 'family_member_id' in attrs or self.instance is None:
            member_id = attrs.pop('family_member_id', None)
            member = None
            if member_id is not None:
                member = FamilyMember.objects.filter(pk=member_id, owner=request.user).first()
                if member is None:
                    raise serializers.ValidationError({'family_member_id': 'Select one of your family members.'})
                defaults = {
                    'patient_name': member.full_name, 'patient_age': member.age, 'patient_gender': member.gender,
                    'patient_phone': member.phone_number or request.user.phone_number,
                }
            else:
                defaults = self_booking_defaults(request.user)
            for field, value in defaults.items():
                if attrs.get(field) in (None, '') and value not in (None, ''):
                    attrs[field] = value
            attrs['family_member'] = member
            attrs['patient_relation'] = member.relation if member else 'self'
        if self.instance is None:
            missing = [
                field for field in ['patient_name', 'patient_age', 'patient_gender', 'patient_phone']
                if attrs.get(field) in (None, '')
            ]
            if missing:
                raise serializers.ValidationError({field: 'This field is required.' for field in missing})
        return attrs


class HistorySerializer(serializers.ModelSerializer):
    duration_value = serializers.IntegerField(min_value=1, max_value=10000, required=True)
    duration_unit = serializers.ChoiceField(choices=Consultation._meta.get_field('duration_unit').choices)
    ongoing_medication = serializers.BooleanField(required=True)
    treatment_details = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    symptoms = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    condition_details = serializers.CharField(
        max_length=10000, required=False, allow_blank=True, help_text='"Specific Medical Condition Details" text box',
    )

    class Meta:
        model = Consultation
        fields = [
            'condition', 'condition_type', 'condition_variant', 'condition_details', 'symptoms',
            'duration_value', 'duration_unit', 'ongoing_medication', 'treatment_details',
        ]
        extra_kwargs = {
            'condition_type': {'help_text': 'Required when the selected disease has types.'},
            'condition_variant': {'help_text': 'Required when the selected type has variants.'},
        }

    def validate(self, attrs):
        condition = attrs.get('condition')
        condition_type = attrs.get('condition_type')
        variant = attrs.get('condition_variant')
        errors = {}
        if condition and not condition.is_active:
            errors['condition'] = 'Select an active condition.'
        if condition_type and (not condition_type.is_active or condition_type.condition_id != getattr(condition, 'pk', None)):
            errors['condition_type'] = 'Select a type of the selected disease.'
        if variant and (not variant.is_active or variant.condition_type_id != getattr(condition_type, 'pk', None)):
            errors['condition_variant'] = 'Select a variant of the selected type.'
        if not errors and condition and not condition_type and condition.types.filter(is_active=True).exists():
            errors['condition_type'] = 'Select the specific type.'
        if not errors and condition_type and not variant and condition_type.variants.filter(is_active=True).exists():
            errors['condition_variant'] = 'Select the sub-condition / variant.'
        if errors:
            raise serializers.ValidationError(errors)
        attrs.setdefault('condition_type', None)
        attrs.setdefault('condition_variant', None)
        attrs['chief_complaint'] = ' - '.join(item.name for item in [condition, condition_type, variant] if item)
        return attrs


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
    consultation_title = serializers.CharField(source='title', read_only=True)
    fee = serializers.IntegerField(source='expected_fee', read_only=True, help_text='Amount payable for this booking, whole currency units')
    fee_currency = serializers.CharField(source='expected_currency', read_only=True, help_text='Currency of fee, e.g. INR or USD')
    # Drafts return '' until filled in; declare blank so the schema allows it.
    patient_gender = serializers.ChoiceField(choices=Consultation._meta.get_field('patient_gender').choices, allow_blank=True, read_only=True)
    duration_unit = serializers.ChoiceField(choices=Consultation._meta.get_field('duration_unit').choices, allow_blank=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'speciality', 'country_code', 'consultation_title', 'fee', 'fee_currency', 'family_member', 'patient_relation', 'patient_name', 'patient_age', 'patient_gender', 'patient_phone', 'mode',
            'condition', 'condition_type', 'condition_variant', 'chief_complaint', 'condition_details',
            'symptoms', 'duration_value', 'duration_unit', 'ongoing_medication',
            'treatment_details', 'history_completed', 'status', 'fee_charged', 'currency', 'scheduled_at',
            'information_confirmed_at', 'documents', 'created_at',
        ]
        read_only_fields = fields


ONLINE_MODES = {Consultation.Mode.CHAT, Consultation.Mode.AUDIO, Consultation.Mode.VIDEO}


def record_status(consultation) -> str:
    appointment = getattr(consultation, 'appointment', None)
    appointment_status = appointment.status if appointment else None
    if consultation.status == Consultation.Status.CANCELLED or appointment_status == 'cancelled':
        return 'cancelled'
    if consultation.status == Consultation.Status.COMPLETED or appointment_status == 'completed':
        return 'completed'
    return 'upcoming'


def relation_label(relation: str) -> str:
    if relation == 'self':
        return 'You'
    return FamilyMember.Relation(relation).label if relation in FamilyMember.Relation.values else relation.title()


class RecordDoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(help_text='Display name, for example "Dr. Ananya Sharma"')
    specialization = serializers.CharField(allow_blank=True)


class RecordPatientSerializer(serializers.Serializer):
    name = serializers.CharField()
    age = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField(allow_blank=True)
    relation = serializers.CharField(help_text='"self" or a family relation such as spouse, son')
    relation_label = serializers.CharField(help_text='"You", "Spouse", "Son" ...')
    is_self = serializers.BooleanField()
    family_member_id = serializers.IntegerField(allow_null=True)


class MedicalRecordListSerializer(serializers.ModelSerializer):
    appointment_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField(help_text='upcoming, completed or cancelled')
    appointment_status = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    mode_label = serializers.SerializerMethodField(help_text='"Online" for chat, audio and video consultations')
    mode_display = serializers.CharField(source='get_mode_display')
    has_clinical_record = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            'id', 'appointment_id', 'scheduled_at', 'status', 'appointment_status', 'doctor', 'patient',
            'mode', 'mode_display', 'mode_label', 'has_clinical_record',
        ]
        read_only_fields = fields

    def get_appointment_id(self, obj) -> int | None:
        appointment = getattr(obj, 'appointment', None)
        return appointment.pk if appointment else None

    def get_status(self, obj) -> str:
        return record_status(obj)

    def get_appointment_status(self, obj) -> str | None:
        appointment = getattr(obj, 'appointment', None)
        return appointment.status if appointment else None

    @extend_schema_field(RecordDoctorSerializer(allow_null=True))
    def get_doctor(self, obj):
        if not obj.doctor:
            return None
        profile = getattr(obj.doctor, 'doctor_profile', None)
        name = obj.doctor.get_full_name() or obj.doctor.username
        return {'id': obj.doctor.pk, 'name': f'Dr. {name}', 'specialization': profile.specialization if profile else ''}

    @extend_schema_field(RecordPatientSerializer)
    def get_patient(self, obj):
        return {
            'name': obj.patient_name, 'age': obj.patient_age, 'gender': obj.patient_gender,
            'relation': obj.patient_relation, 'relation_label': relation_label(obj.patient_relation),
            'is_self': obj.patient_relation == 'self', 'family_member_id': obj.family_member_id,
        }

    def get_mode_label(self, obj) -> str:
        return 'Online' if obj.mode in ONLINE_MODES else obj.get_mode_display()

    def get_has_clinical_record(self, obj) -> bool:
        return obj.status == Consultation.Status.COMPLETED and obj.record_updated_at is not None


class PrescriptionItemSerializer(serializers.ModelSerializer):
    timings = serializers.ListField(
        child=serializers.ChoiceField(choices=PrescriptionItem.Timing.choices), min_length=1, max_length=4,
    )
    duration_days = serializers.IntegerField(min_value=1, max_value=365)
    timing_labels = serializers.SerializerMethodField()
    food_relation_label = serializers.CharField(source='get_food_relation_display', read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'medicine_name', 'dosage', 'timings', 'timing_labels', 'food_relation',
            'food_relation_label', 'duration_days', 'instructions',
        ]
        read_only_fields = ['id', 'timing_labels', 'food_relation_label']

    def validate_timings(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Each timing can be listed only once.')
        order = list(PrescriptionItem.Timing.values)
        return sorted(value, key=order.index)

    def get_timing_labels(self, obj) -> list[str]:
        return [PrescriptionItem.Timing(value).label for value in obj.timings]


class FollowUpSerializer(serializers.Serializer):
    date = serializers.DateField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)


class MedicalRecordDetailSerializer(MedicalRecordListSerializer):
    diagnosis = serializers.SerializerMethodField()
    prescriptions = serializers.SerializerMethodField()
    doctor_notes = serializers.SerializerMethodField()
    follow_up = serializers.SerializerMethodField()
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta(MedicalRecordListSerializer.Meta):
        fields = MedicalRecordListSerializer.Meta.fields + [
            'chief_complaint', 'condition_details', 'symptoms', 'diagnosis', 'prescriptions', 'doctor_notes', 'follow_up', 'record_updated_at', 'documents',
        ]
        read_only_fields = fields

    def _published(self, obj):
        return self.get_has_clinical_record(obj)

    def get_diagnosis(self, obj) -> str:
        return obj.diagnosis if self._published(obj) else ''

    @extend_schema_field(PrescriptionItemSerializer(many=True))
    def get_prescriptions(self, obj):
        if not self._published(obj):
            return []
        return PrescriptionItemSerializer(obj.prescription_items.all(), many=True).data

    def get_doctor_notes(self, obj) -> str:
        return obj.doctor_notes if self._published(obj) else ''

    @extend_schema_field(FollowUpSerializer(allow_null=True))
    def get_follow_up(self, obj):
        if not self._published(obj) or (not obj.follow_up_date and not obj.follow_up_notes):
            return None
        return FollowUpSerializer({'date': obj.follow_up_date, 'notes': obj.follow_up_notes}).data


class DoctorConsultationSerializer(MedicalRecordListSerializer):
    condition_name = serializers.CharField(source='condition.name', default='', read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    prescriptions = PrescriptionItemSerializer(source='prescription_items', many=True, read_only=True)

    class Meta(MedicalRecordListSerializer.Meta):
        fields = MedicalRecordListSerializer.Meta.fields + [
            'condition_name', 'chief_complaint', 'condition_details', 'symptoms', 'duration_value', 'duration_unit', 'ongoing_medication',
            'treatment_details', 'diagnosis', 'prescriptions', 'doctor_notes', 'follow_up_date',
            'follow_up_notes', 'record_updated_at', 'documents',
        ]
        read_only_fields = fields


class ConsultationRecordWriteSerializer(serializers.Serializer):
    diagnosis = serializers.CharField(max_length=5000)
    prescriptions = PrescriptionItemSerializer(many=True, required=False, default=list)
    doctor_notes = serializers.CharField(max_length=10000, required=False, allow_blank=True, default='')
    follow_up_date = serializers.DateField(required=False, allow_null=True, default=None)
    follow_up_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')
    mark_completed = serializers.BooleanField(
        default=False,
        help_text='Set true to complete the consultation and publish this record to the patient.',
    )

    def validate_prescriptions(self, value):
        if len(value) > 30:
            raise serializers.ValidationError('A record can contain at most 30 prescription items.')
        return value


class CasePreviewPatientSerializer(serializers.Serializer):
    name = serializers.CharField()
    age = serializers.IntegerField(allow_null=True)
    gender = serializers.CharField()
    gender_label = serializers.CharField()
    phone = serializers.CharField()
    relation = serializers.CharField()
    relation_label = serializers.CharField()


class CasePreviewScheduleSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField(allow_null=True)
    starts_at = serializers.DateTimeField(allow_null=True)
    date_display = serializers.CharField(help_text='e.g. 18 Oct 2026')
    time_display = serializers.CharField(help_text='e.g. 07:00 PM')
    is_available = serializers.BooleanField()


class CasePreviewSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField()
    consultation_title = serializers.CharField(help_text='"General Consultation" or e.g. "Skin Consultation"')
    speciality = serializers.CharField(allow_null=True)
    patient = CasePreviewPatientSerializer()
    chief_complaint = serializers.CharField(help_text='The consultation title when no disease was selected')
    condition_details = serializers.CharField(allow_blank=True)
    symptoms = serializers.CharField(allow_blank=True)
    duration_display = serializers.CharField(allow_blank=True, help_text='e.g. 5 Days')
    ongoing_medication = serializers.BooleanField(allow_null=True)
    treatment_details = serializers.CharField(allow_blank=True)
    mode = serializers.CharField()
    schedule = CasePreviewScheduleSerializer(allow_null=True)
    documents = DocumentSerializer(many=True)
    document_count = serializers.IntegerField()
    fee = serializers.IntegerField(help_text='INR rupees')
    currency = serializers.CharField()
    ready_to_submit = serializers.BooleanField()
    missing_steps = serializers.ListField(child=serializers.CharField())
