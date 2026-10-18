from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, extend_schema

from .models import DoctorApplication, DoctorApplicationDocument, Speciality
from .serializers import (
    DoctorApplicationSerializer,
    DoctorApplicationSubmissionSerializer,
    FeaturedDoctorSerializer,
    SpecialitySerializer,
)

MAX_APPLICATION_DOCUMENTS = 5
MAX_FEATURED_DOCTORS = 8


class DoctorApplicationCreateView(APIView):
    """Public, unauthenticated endpoint for the pre-launch doctor onboarding interest form."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['Doctors'],
        summary='Submit a doctor application',
        description=(
            'Submit multipart form data with up to five optional supporting documents and an optional `photo` '
            '(JPG, PNG or WEBP, up to 5 MB) that is shown on the website once staff approve the application. The fee is checked against the '
            'pricing of country_code (GET /api/v1/pricing/; default India): general doctors use the country general fee, '
            'specialists a fee within the country range and step. The response includes the currency.'
        ),
        request=DoctorApplicationSubmissionSerializer,
        responses={201: DoctorApplicationSerializer},
    )
    def post(self, request):
        serializer = DoctorApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()

        uploaded_files = request.FILES.getlist('documents')[:MAX_APPLICATION_DOCUMENTS]
        for uploaded_file in uploaded_files:
            DoctorApplicationDocument.objects.create(application=application, file=uploaded_file)

        response_data = DoctorApplicationSerializer(application, context={'request': request}).data
        return Response(response_data, status=status.HTTP_201_CREATED)


FEATURED_DOCTOR_EXAMPLE = {
    'id': 12, 'name': 'Dr. Ananya Sharma', 'qualification': 'MBBS, MD', 'specialization': 'General Physician',
    'experience_years': 12, 'consultation_category': 'general', 'treatment_systems': ['allopathy', 'home_remedy'],
    'consultation_fee': 200, 'currency': 'INR', 'fee_display': '\u20b9200',
    'photo_url': 'https://api.lalaharihealth.com/media/doctor_applications/photos/3f2a9c1e5b7d4e8f9a0b1c2d3e4f5a6b.jpg',
}


@extend_schema(
    tags=['Doctors'],
    summary='Doctors shown on the website and app',
    description=(
        'Public. Doctors who registered through the For Doctors form and were marked Approved by staff in admin, '
        f'newest first, at most {MAX_FEATURED_DOCTORS}. Not paginated. `photo_url` is null when no photo was uploaded: '
        'show a default image. General doctors (`consultation_category` general) charge the country general fee '
        '(GET /api/v1/pricing/); specialists show `fee_display`. Contact details are never returned.'
    ),
    examples=[OpenApiExample('Approved doctors', response_only=True, value=[
        FEATURED_DOCTOR_EXAMPLE,
        {**FEATURED_DOCTOR_EXAMPLE, 'id': 9, 'name': 'Dr. Rohan Mehta', 'specialization': 'Dermatologist',
         'experience_years': 9, 'consultation_category': 'specialist', 'treatment_systems': ['allopathy'],
         'consultation_fee': 500, 'fee_display': '\u20b9500', 'photo_url': None},
    ])],
)
class FeaturedDoctorListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = FeaturedDoctorSerializer
    pagination_class = None

    def get_queryset(self):
        approved = DoctorApplication.objects.filter(status=DoctorApplication.Status.APPROVED)
        return approved.order_by('-created_at', '-id')[:MAX_FEATURED_DOCTORS]


@extend_schema(
    tags=['Appointment booking'],
    summary='Specialities for Book Specialist',
    description=(
        'Active specialities with their per-consultation fee, for the "Expert Care" card. Send the chosen `id` as '
        '`speciality` in step 1 (`POST /api/v1/consultations/`) and as `speciality_id` when listing slots. '
        'Public, not paginated. Specialist fees are in INR for every country.'
    ),
    examples=[OpenApiExample('Specialities', response_only=True, value=[
        {'id': 1, 'name': 'Cardiology', 'slug': 'cardiology', 'short_name': 'Cardio', 'title': 'Cardiology Consultation',
         'description': 'Heart and blood pressure', 'fee': 500, 'currency': 'INR', 'fee_display': '\u20b9500'},
        {'id': 2, 'name': 'Dermatology', 'slug': 'dermatology', 'short_name': 'Derma', 'title': 'Skin Consultation',
         'description': 'Skin, hair and nails', 'fee': 400, 'currency': 'INR', 'fee_display': '\u20b9400'},
    ])],
)
class SpecialityListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = SpecialitySerializer
    pagination_class = None
    queryset = Speciality.objects.filter(is_active=True).order_by('display_order', 'name')
