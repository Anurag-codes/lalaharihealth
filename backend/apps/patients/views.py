from django.db import transaction
from django.http import FileResponse, Http404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.views import IsPatient, NoStoreResponseMixin
from apps.consultations.models import Consultation
from apps.consultations.serializers import MedicalRecordDetailSerializer, MedicalRecordListSerializer
from .models import FamilyMember, PatientProfile
from .serializers import BookingPatientSerializer, FamilyMemberSerializer, PatientProfileSerializer, ProfilePhotoUploadSerializer

PROFILE_EXAMPLE = {
    'id': 12, 'first_name': 'Rahul', 'last_name': 'Sharma', 'full_name': 'Rahul Sharma',
    'email': 'rahul@example.com', 'phone_number': '+919876543210', 'is_email_verified': True,
    'is_phone_verified': True, 'city': 'Delhi', 'gender': 'male', 'date_of_birth': '1990-05-14', 'age': 35,
    'preferred_language': 'en', 'preferred_language_label': 'English',
    'available_languages': [{'code': 'en', 'label': 'English'}, {'code': 'hi', 'label': 'हिन्दी'}],
    'photo_url': 'https://api.lalaharihealth.com/api/v1/patients/profile/photo/',
    'membership_label': 'LalaHari Health Beneficiary', 'family_member_count': 2, 'medical_record_count': 3,
}
FAMILY_EXAMPLE = {
    'id': 4, 'full_name': 'Priya Sharma', 'relation': 'spouse', 'relation_label': 'Spouse',
    'date_of_birth': '1992-08-21', 'age': 33, 'gender': 'female', 'gender_label': 'Female',
    'phone_number': '+919876543211', 'created_at': '2026-01-10T09:30:00Z', 'updated_at': '2026-01-10T09:30:00Z',
}
FAMILY_REQUEST_EXAMPLE = {
    'full_name': 'Priya Sharma', 'relation': 'spouse', 'date_of_birth': '1992-08-21',
    'gender': 'female', 'phone_number': '+919876543211',
}
RECORD_LIST_EXAMPLE = {
    'id': 41, 'appointment_id': 18, 'scheduled_at': '2026-02-12T10:30:00+05:30', 'status': 'completed',
    'appointment_status': 'completed',
    'doctor': {'id': 7, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician'},
    'patient': {
        'name': 'Rahul Sharma', 'age': 35, 'gender': 'male', 'relation': 'self', 'relation_label': 'You',
        'is_self': True, 'family_member_id': None,
    },
    'mode': 'video', 'mode_display': 'Video', 'mode_label': 'Online', 'has_clinical_record': True,
}
PRESCRIPTION_EXAMPLE = [
    {
        'id': 1, 'medicine_name': 'Azithromycin 500mg', 'dosage': '1 tablet', 'timings': ['morning'],
        'timing_labels': ['Morning'], 'food_relation': 'after_food', 'food_relation_label': 'After food',
        'duration_days': 5, 'instructions': '',
    },
    {
        'id': 2, 'medicine_name': 'Cough syrup', 'dosage': '10 ml', 'timings': ['morning', 'night'],
        'timing_labels': ['Morning', 'Night'], 'food_relation': 'after_food', 'food_relation_label': 'After food',
        'duration_days': 7, 'instructions': 'Shake well before use',
    },
]
RECORD_DETAIL_EXAMPLE = {
    **RECORD_LIST_EXAMPLE,
    'chief_complaint': 'Throat infection',
    'condition_details': 'Fever and sore throat for 3 days',
    'symptoms': 'Fever and sore throat for 3 days',
    'diagnosis': 'Acute pharyngitis',
    'prescriptions': PRESCRIPTION_EXAMPLE,
    'doctor_notes': 'Drink warm fluids and take rest.',
    'follow_up': {'date': '2026-02-19', 'notes': 'Follow up after 1 week if symptoms persist.'},
    'record_updated_at': '2026-02-12T11:05:00+05:30',
    'documents': [],
}


def patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile


class PatientProfileView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = PatientProfileSerializer

    @extend_schema(
        tags=['Patient profile'], summary='Get the profile screen data',
        examples=[OpenApiExample('Profile', value=PROFILE_EXAMPLE, response_only=True)],
    )
    def get(self, request):
        return Response(self.get_serializer(patient_profile(request.user)).data)

    @extend_schema(
        tags=['Patient profile'], summary='Update name, city, gender, date of birth or app language',
        description='Send only the fields to change. Email and phone are changed through the verified link endpoints in Patient auth.',
        examples=[
            OpenApiExample('Update details', value={
                'first_name': 'Rahul', 'last_name': 'Sharma', 'city': 'Delhi', 'gender': 'male', 'date_of_birth': '1990-05-14',
            }, request_only=True),
            OpenApiExample('Change app language to Hindi', value={'preferred_language': 'hi'}, request_only=True),
            OpenApiExample(
                'Updated profile', response_only=True,
                value={**PROFILE_EXAMPLE, 'preferred_language': 'hi', 'preferred_language_label': 'हिन्दी'},
            ),
        ],
    )
    def patch(self, request):
        serializer = self.get_serializer(patient_profile(request.user), data=request.data, partial=True)
        writable = {name for name, field in serializer.fields.items() if not field.read_only}
        rejected = sorted(set(request.data) - writable) if hasattr(request.data, 'keys') else []
        if rejected:
            return Response({field: ['This field cannot be updated here.'] for field in rejected}, status=400)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PatientProfilePhotoView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = ProfilePhotoUploadSerializer
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=['Patient profile'], summary='Download your profile photo',
        description='Photos are private. Load this URL with your access token in the Authorization header (Bearer scheme).',
        responses={(200, 'image/*'): OpenApiTypes.BINARY, 404: OpenApiResponse(description='No photo uploaded.')},
    )
    def get(self, request):
        profile = patient_profile(request.user)
        if not profile.profile_photo:
            raise Http404
        return FileResponse(profile.profile_photo.open('rb'))

    @extend_schema(
        tags=['Patient profile'], summary='Upload or replace your profile photo (camera icon)',
        description='Send multipart/form-data with a `photo` field: PNG or JPG, up to 5 MB.',
        request={'multipart/form-data': ProfilePhotoUploadSerializer},
        responses={200: PatientProfileSerializer},
        examples=[OpenApiExample('Profile with photo', value=PROFILE_EXAMPLE, response_only=True)],
    )
    @transaction.atomic
    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = PatientProfile.objects.select_for_update().get(pk=patient_profile(request.user).pk)
        old_photo = profile.profile_photo.name if profile.profile_photo else ''
        profile.profile_photo = serializer.validated_data['photo']
        profile.save(update_fields=['profile_photo'])
        if old_photo:
            storage = profile.profile_photo.storage
            transaction.on_commit(lambda: storage.delete(old_photo))
        return Response(PatientProfileSerializer(profile, context={'request': request}).data)

    @extend_schema(tags=['Patient profile'], summary='Remove your profile photo', request=None, responses={204: None})
    @transaction.atomic
    def delete(self, request):
        profile = PatientProfile.objects.select_for_update().get(pk=patient_profile(request.user).pk)
        if profile.profile_photo:
            old_photo, storage = profile.profile_photo.name, profile.profile_photo.storage
            profile.profile_photo = ''
            profile.save(update_fields=['profile_photo'])
            transaction.on_commit(lambda: storage.delete(old_photo))
        return Response(status=status.HTTP_204_NO_CONTENT)


class FamilyMemberListCreateView(NoStoreResponseMixin, generics.ListCreateAPIView):
    permission_classes = [IsPatient]
    serializer_class = FamilyMemberSerializer
    pagination_class = None

    def get_queryset(self):
        return FamilyMember.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=['Family profiles'], summary='List linked family members',
        examples=[OpenApiExample('Family members', response_only=True, value=[
            FAMILY_EXAMPLE,
            {**FAMILY_EXAMPLE, 'id': 5, 'full_name': 'Aarav Sharma', 'relation': 'son', 'relation_label': 'Son',
             'date_of_birth': '2016-03-02', 'age': 9, 'gender': 'male', 'gender_label': 'Male', 'phone_number': ''},
        ])],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Family profiles'], summary='Add a family member',
        description='Age is calculated from date_of_birth. phone_number is optional.',
        examples=[
            OpenApiExample('Add spouse', value=FAMILY_REQUEST_EXAMPLE, request_only=True),
            OpenApiExample('Add child without phone', request_only=True, value={
                'full_name': 'Aarav Sharma', 'relation': 'son', 'date_of_birth': '2016-03-02', 'gender': 'male',
            }),
            OpenApiExample('Created', value=FAMILY_EXAMPLE, response_only=True, status_codes=['201']),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


def _patient_card(member_id, name, age, gender, gender_label, phone, relation, relation_label):
    parts = [relation_label]
    if age is not None:
        parts.append(f'{age} years')
    if gender_label:
        parts.append(gender_label)
    return {
        'family_member_id': member_id, 'name': name, 'age': age, 'gender': gender, 'gender_label': gender_label,
        'phone': phone, 'relation': relation, 'relation_label': relation_label, 'subtitle': ' \u00b7 '.join(parts),
        'details_complete': all([name, age is not None, gender, phone]),
    }


class BookingPatientListView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = BookingPatientSerializer
    pagination_class = None

    @extend_schema(
        tags=['Mobile intake'], summary='Select Patient: Myself and family members for a booking',
        description=(
            'First item is always Myself (`family_member_id` null), then family members. Send the chosen '
            '`family_member_id` to `POST /api/v1/consultations/`. "+ Add family member" uses `POST /api/v1/patients/family-members/`.'
        ),
        responses=BookingPatientSerializer(many=True),
        examples=[OpenApiExample('Patients', response_only=True, value=[
            {'family_member_id': None, 'name': 'Rahul Sharma', 'age': 25, 'gender': 'male', 'gender_label': 'Male',
             'phone': '+919876543210', 'relation': 'self', 'relation_label': 'Myself',
             'subtitle': 'Myself \u00b7 25 years \u00b7 Male', 'details_complete': True},
            {'family_member_id': 3, 'name': 'Priya Sharma', 'age': 33, 'gender': 'female', 'gender_label': 'Female',
             'phone': '+919812345678', 'relation': 'spouse', 'relation_label': 'Spouse',
             'subtitle': 'Spouse \u00b7 33 years \u00b7 Female', 'details_complete': True},
        ])],
    )
    def get(self, request):
        from apps.consultations.serializers import self_booking_defaults

        me = self_booking_defaults(request.user)
        genders = dict(PatientProfile.Gender.choices)
        cards = [_patient_card(
            None, me['patient_name'], me['patient_age'], me['patient_gender'], genders.get(me['patient_gender'], ''),
            me['patient_phone'], 'self', 'Myself',
        )]
        for member in FamilyMember.objects.filter(owner=request.user):
            cards.append(_patient_card(
                member.pk, member.full_name, member.age, member.gender, member.get_gender_display(),
                member.phone_number or request.user.phone_number or '', member.relation, member.get_relation_display(),
            ))
        return Response(self.get_serializer(cards, many=True).data)


class FamilyMemberDetailView(NoStoreResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsPatient]
    serializer_class = FamilyMemberSerializer
    lookup_url_kwarg = 'member_id'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return FamilyMember.objects.filter(owner=self.request.user)

    @extend_schema(
        tags=['Family profiles'], summary='View a family member',
        examples=[OpenApiExample('Family member', value=FAMILY_EXAMPLE, response_only=True)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Family profiles'], summary='Edit a family member',
        description='Send only the fields to change. Past consultation records keep the name and relation used at booking time.',
        examples=[
            OpenApiExample('Change phone number', value={'phone_number': '+919811112222'}, request_only=True),
            OpenApiExample('Updated', value={**FAMILY_EXAMPLE, 'phone_number': '+919811112222'}, response_only=True),
        ],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Family profiles'], summary='Remove a family member',
        description='Past medical records for this member stay visible in Medical Records.',
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


def medical_records(user):
    return (
        Consultation.objects.filter(patient=user).exclude(status=Consultation.Status.DRAFT)
        .select_related('appointment', 'doctor__doctor_profile')
        .prefetch_related('prescription_items', 'documents')
        .order_by('-scheduled_at', '-created_at')
    )


class MedicalRecordListView(NoStoreResponseMixin, generics.ListAPIView):
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordListSerializer

    def get_queryset(self):
        queryset = medical_records(self.request.user)
        member = self.request.query_params.get('family_member_id', '').strip()
        if member == 'self':
            queryset = queryset.filter(patient_relation='self')
        elif member:
            queryset = queryset.filter(family_member_id=int(member)) if member.isdigit() else queryset.none()
        return queryset

    @extend_schema(
        tags=['Medical records'], summary='Appointment history for you and your family',
        description='Booked consultations, newest first. status is upcoming, completed or cancelled. All modes (chat, audio, video) are online.',
        parameters=[OpenApiParameter(
            'family_member_id', str, required=False,
            description='Optional filter: "self" for your own records, or a family member id.',
        )],
        examples=[OpenApiExample('Medical records page', response_only=True, value={
            'count': 2, 'next': None, 'previous': None,
            'results': [
                {**RECORD_LIST_EXAMPLE, 'id': 42, 'appointment_id': 19, 'status': 'upcoming',
                 'appointment_status': 'confirmed', 'scheduled_at': '2026-02-20T17:00:00+05:30',
                 'has_clinical_record': False, 'mode': 'audio', 'mode_display': 'Audio',
                 'patient': {'name': 'Priya Sharma', 'age': 33, 'gender': 'female', 'relation': 'spouse',
                             'relation_label': 'Spouse', 'is_self': False, 'family_member_id': 4}},
                RECORD_LIST_EXAMPLE,
            ],
        })],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MedicalRecordDetailView(NoStoreResponseMixin, generics.RetrieveAPIView):
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordDetailSerializer
    lookup_url_kwarg = 'consultation_id'

    def get_queryset(self):
        return medical_records(self.request.user)

    @extend_schema(
        tags=['Medical records'], summary='Consultation record',
        description='Diagnosis, prescriptions, doctor notes and follow-up are filled once the doctor completes the consultation; until then they are empty and has_clinical_record is false.',
        examples=[OpenApiExample('Completed consultation record', value=RECORD_DETAIL_EXAMPLE, response_only=True)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
