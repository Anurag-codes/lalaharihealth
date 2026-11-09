"""Doctor mobile app: my profile, photo, verification documents, weekly availability and qualification suggestions."""
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from apps.accounts.services import require_doctor
from apps.accounts.views import NoStoreResponseMixin
from .app_serializers import (
    MAX_OTHER_DOCUMENTS, QUALIFICATIONS, AvailabilityWeekSerializer, DoctorDocumentSerializer,
    DoctorDocumentUploadSerializer, DoctorMeSerializer, DoctorMeUpdateSerializer, DoctorPhotoSerializer,
    QualificationSerializer, availability_payload,
)
from .models import DoctorAvailability, DoctorDocument, DoctorProfile
from .onboarding import ensure_doctor_profile

TAG = 'Doctor app: profile'
AUTH = ' Doctor access token from POST /api/v1/auth/doctor/phone/firebase/.'

DOCUMENT_EXAMPLE = {
    'id': 31, 'document_type': 'medical_registration', 'document_type_label': 'Medical Council Registration',
    'original_name': 'registration.pdf', 'uploaded_at': '2026-10-18T10:15:00+05:30',
    'download_url': 'https://api.lalaharihealth.com/api/v1/doctors/me/documents/31/download/',
}
DOCTOR_ME_EXAMPLE = {
    'id': 57, 'profile_id': 12, 'full_name': 'Ananya Sharma', 'first_name': 'Ananya', 'last_name': 'Sharma',
    'phone_number': '+919876543210', 'email': '', 'photo_url': 'https://api.lalaharihealth.com/media/doctors/photos/3f2a9c1e5b7d4e8f.jpg',
    'age': 34, 'gender': 'female', 'registration_number': 'DMC/R/12345', 'qualification': 'MBBS, MD',
    'speciality': None, 'specialization': 'General Physician', 'experience_years': 8, 'city': 'Delhi',
    'verification_status': 'pending', 'verification_status_label': 'Pending Review', 'is_verified': False,
    'documents': [DOCUMENT_EXAMPLE],
    'onboarding': {
        'profile_completed': True, 'registration_certificate_uploaded': True, 'availability_set': False,
        'is_complete': False, 'next_step': 'availability',
    },
}
WINDOW = lambda start, end, display: {'start_time': start, 'end_time': end, 'display': display}  # noqa: E731
AVAILABILITY_EXAMPLE = {
    'days': [
        {'weekday': 0, 'label': 'Mon', 'is_open': True, 'total_hours': 7.0, 'windows': [
            WINDOW('07:00', '10:00', '07:00 AM - 10:00 AM'), WINDOW('15:00', '17:00', '03:00 PM - 05:00 PM'),
            WINDOW('21:00', '23:00', '09:00 PM - 11:00 PM'),
        ]},
        {'weekday': 1, 'label': 'Tue', 'is_open': True, 'total_hours': 6.0, 'windows': [WINDOW('09:00', '15:00', '09:00 AM - 03:00 PM')]},
        {'weekday': 2, 'label': 'Wed', 'is_open': False, 'total_hours': 0.0, 'windows': []},
        {'weekday': 3, 'label': 'Thu', 'is_open': False, 'total_hours': 0.0, 'windows': []},
        {'weekday': 4, 'label': 'Fri', 'is_open': False, 'total_hours': 0.0, 'windows': []},
        {'weekday': 5, 'label': 'Sat', 'is_open': False, 'total_hours': 0.0, 'windows': []},
        {'weekday': 6, 'label': 'Sun', 'is_open': False, 'total_hours': 0.0, 'windows': []},
    ],
    'min_daily_hours': 6, 'max_windows_per_day': 3, 'timezone': 'Asia/Kolkata',
}


class IsDoctor(BasePermission):
    """Any active doctor account, including doctors still awaiting verification."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        require_doctor(request.user)
        return True


def my_profile(request, lock=False):
    profile = ensure_doctor_profile(request.user)
    queryset = DoctorProfile.objects.select_related('user', 'speciality').prefetch_related('documents')
    if lock:
        queryset = queryset.select_for_update(of=('self',))
    return queryset.get(pk=profile.pk)


def me_response(request):
    return Response(DoctorMeSerializer(my_profile(request), context={'request': request}).data)


class DoctorMeView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorMeSerializer

    @extend_schema(
        tags=[TAG], summary='My doctor profile and onboarding progress',
        description=(
            'Profile, verification status, documents and `onboarding`. After sign-in open the screen given by '
            '`onboarding.next_step`: profile (Step 2 Professional Details), availability (Step 3) or done (Home). '
            'New doctors are Pending Review until staff verify them; only verified doctors receive appointments.' + AUTH
        ),
        examples=[OpenApiExample('Profile', value=DOCTOR_ME_EXAMPLE, response_only=True)],
    )
    def get(self, request):
        return me_response(request)

    @extend_schema(
        tags=[TAG], summary='Save Professional Details (Step 2) or edit my profile',
        description=(
            'Send only changed fields. `speciality_id` is an id from GET /api/v1/doctors/specialities/ or null for General Physician. '
            'Registration number, qualification and speciality are locked once you are verified (400).' + AUTH
        ),
        request=DoctorMeUpdateSerializer, responses=DoctorMeSerializer,
        examples=[
            OpenApiExample('Professional details', request_only=True, value={
                'full_name': 'Ananya Sharma', 'age': 34, 'gender': 'female', 'registration_number': 'DMC/R/12345',
                'qualification': 'MBBS, MD', 'speciality_id': None,
            }),
            OpenApiExample('Profile', value=DOCTOR_ME_EXAMPLE, response_only=True),
        ],
    )
    def patch(self, request):
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            serializer = DoctorMeUpdateSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return me_response(request)


class DoctorPhotoView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=[TAG], summary='Upload or replace my profile photo',
        description='multipart/form-data with field `photo` (JPG, PNG or WEBP, up to 5 MB).' + AUTH,
        request={'multipart/form-data': DoctorPhotoSerializer}, responses=DoctorMeSerializer,
        examples=[
            OpenApiExample('Photo', value={'photo': '<file: dr-anjali.jpg>'}, request_only=True, media_type='multipart/form-data'),
            OpenApiExample('Profile', value=DOCTOR_ME_EXAMPLE, response_only=True),
        ],
    )
    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            old = profile.profile_photo.name if profile.profile_photo else None
            profile.profile_photo = serializer.validated_data['photo']
            profile.save(update_fields=['profile_photo'])
            if old:
                storage = profile.profile_photo.storage
                transaction.on_commit(lambda: storage.delete(old))
        return me_response(request)

    @extend_schema(tags=[TAG], summary='Remove my profile photo', description='Returns 204.' + AUTH, responses={204: None})
    def delete(self, request):
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            if profile.profile_photo:
                old, storage = profile.profile_photo.name, profile.profile_photo.storage
                profile.profile_photo = None
                profile.save(update_fields=['profile_photo'])
                transaction.on_commit(lambda: storage.delete(old))
        return Response(status=204)


class DoctorDocumentListView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorDocumentUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = None

    @extend_schema(
        tags=[TAG], summary='My verification documents',
        description='Open a file with `download_url` and the auth header. Files are private.' + AUTH,
        responses=DoctorDocumentSerializer(many=True),
        examples=[OpenApiExample('Documents', response_only=True, value=[
            DOCUMENT_EXAMPLE,
            {**DOCUMENT_EXAMPLE, 'id': 32, 'document_type': 'degree_certificate', 'document_type_label': 'Degree Certificate',
             'original_name': 'mbbs-degree.jpg', 'download_url': 'https://api.lalaharihealth.com/api/v1/doctors/me/documents/32/download/'},
        ])],
    )
    def get(self, request):
        documents = my_profile(request).documents.all()
        return Response(DoctorDocumentSerializer(documents, many=True, context={'request': request}).data)

    @extend_schema(
        tags=[TAG], summary='Upload a verification document',
        description=(
            'multipart/form-data with `document_type` and `file` (PDF, PNG or JPG, up to 10 MB). '
            '`medical_registration` = Medical Council Registration Certificate (required in Step 2), '
            '`degree_certificate` = Qualification Degree, `government_id` = Government ID Proof. Uploading one of these '
            f'replaces the previous file of that type. `other` keeps up to {MAX_OTHER_DOCUMENTS} files.' + AUTH
        ),
        request={'multipart/form-data': DoctorDocumentUploadSerializer}, responses={201: DoctorDocumentSerializer},
        examples=[
            OpenApiExample(
                'Registration certificate', request_only=True, media_type='multipart/form-data',
                value={'document_type': 'medical_registration', 'file': '<file: mci-registration.pdf>'},
            ),
            OpenApiExample('Uploaded', value=DOCUMENT_EXAMPLE, response_only=True, status_codes=['201']),
        ],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_type = serializer.validated_data['document_type']
        upload = serializer.validated_data['file']
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            existing = profile.documents.filter(document_type=document_type)
            if document_type == DoctorDocument.DocumentType.OTHER:
                if existing.count() >= MAX_OTHER_DOCUMENTS:
                    raise serializers.ValidationError({'file': f'You can upload at most {MAX_OTHER_DOCUMENTS} other documents.'})
                replaced = []
            else:
                replaced = list(existing)
            document = DoctorDocument.objects.create(
                doctor=profile, document_type=document_type, file=upload, original_name=upload.name[:255],
            )
            for old in replaced:
                name, storage = old.file.name, old.file.storage
                old.delete()
                transaction.on_commit(lambda name=name, storage=storage: storage.delete(name))
        return Response(DoctorDocumentSerializer(document, context={'request': request}).data, status=201)


class DoctorDocumentDetailView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorDocumentSerializer

    @extend_schema(
        tags=[TAG], summary='Delete one of my documents',
        description='Returns 204. Verified doctors cannot delete the Medical Council Registration Certificate (400).' + AUTH,
        responses={204: None},
    )
    def delete(self, request, document_id):
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            document = get_object_or_404(profile.documents.all(), pk=document_id)
            if profile.is_verified and document.document_type == DoctorDocument.DocumentType.MEDICAL_REGISTRATION:
                raise serializers.ValidationError('Your verified registration certificate cannot be deleted. Upload a new one to replace it.')
            name, storage = document.file.name, document.file.storage
            document.delete()
            transaction.on_commit(lambda: storage.delete(name))
        return Response(status=204)


class DoctorDocumentDownloadView(generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorDocumentSerializer

    @extend_schema(
        tags=[TAG], summary='Download one of my documents',
        description='Streams the private file (PDF or image bytes).' + AUTH,
        responses={(200, 'application/octet-stream'): bytes},
    )
    def get(self, request, document_id):
        document = get_object_or_404(DoctorDocument.objects.filter(doctor__user=request.user), pk=document_id)
        try:
            handle = document.file.open('rb')
        except FileNotFoundError:
            raise serializers.ValidationError('This file is no longer available. Upload it again.') from None
        response = FileResponse(handle, as_attachment=True, filename=document.original_name or None)
        response['Cache-Control'] = 'private, no-store'
        return response


class DoctorAvailabilityView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsDoctor]
    serializer_class = AvailabilityWeekSerializer

    @extend_schema(
        tags=[TAG], summary='My weekly availability (Step 3)',
        description=(
            'Weekly hours (India time) when our care team may contact you and assign consultations. '
            'Patients never see or choose these.' + AUTH
        ),
        examples=[OpenApiExample('Week', value=AVAILABILITY_EXAMPLE, response_only=True)],
    )
    def get(self, request):
        return Response(availability_payload(my_profile(request)))

    @extend_schema(
        tags=[TAG], summary='Save my weekly availability ("Start Consulting")',
        description=(
            'Replaces the whole week. Each open day has 1 to 3 time windows (24-hour HH:MM, 15-minute steps, '
            'no overlaps), e.g. 07:00-10:00, 15:00-17:00 and 21:00-23:00, totalling at least 6 hours. '
            'Windows of closed days are ignored; missing days are closed. At least one day must be open.' + AUTH
        ),
        examples=[
            OpenApiExample('Monday three windows, Tuesday one', request_only=True, value={'days': [
                {'weekday': 0, 'is_open': True, 'windows': [
                    {'start_time': '07:00', 'end_time': '10:00'}, {'start_time': '15:00', 'end_time': '17:00'},
                    {'start_time': '21:00', 'end_time': '23:00'},
                ]},
                {'weekday': 1, 'is_open': True, 'windows': [{'start_time': '09:00', 'end_time': '15:00'}]},
                {'weekday': 2, 'is_open': False, 'windows': []},
            ]}),
            OpenApiExample('Week', value=AVAILABILITY_EXAMPLE, response_only=True),
        ],
    )
    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = my_profile(request, lock=True)
            profile.availability_windows.all().delete()
            DoctorAvailability.objects.bulk_create([
                DoctorAvailability(doctor=profile, weekday=day['weekday'], **window)
                for day in serializer.validated_data['days'] if day['is_open']
                for window in day['windows']
            ])
        return Response(availability_payload(profile))


@extend_schema(
    tags=[TAG], summary='Qualification suggestions',
    description='Public. Suggestions for the "Search or enter" qualification field; the doctor may also type any other value.',
    parameters=[OpenApiParameter('search', str, required=False, description='Case-insensitive part of the name, e.g. "md"')],
    examples=[OpenApiExample('Qualifications', response_only=True, value=[{'name': 'MD'}, {'name': 'MD (Ayurveda)'}])],
)
class QualificationListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = QualificationSerializer
    pagination_class = None

    def get_queryset(self):
        search = self.request.query_params.get('search', '').strip().lower()
        return [{'name': name} for name in QUALIFICATIONS if search in name.lower()]
