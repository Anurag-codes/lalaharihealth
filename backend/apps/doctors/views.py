from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, extend_schema

from .models import DoctorApplication, DoctorApplicationDocument, Speciality
from .serializers import DoctorApplicationSerializer, DoctorApplicationSubmissionSerializer, SpecialitySerializer

MAX_APPLICATION_DOCUMENTS = 5


class DoctorApplicationCreateView(APIView):
    """Public, unauthenticated endpoint for the pre-launch doctor onboarding interest form."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['Doctors'],
        summary='Submit a doctor application',
        description=(
            'Submit multipart form data with up to five optional supporting documents. The fee is checked against the '
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

        response_data = DoctorApplicationSerializer(application).data
        return Response(response_data, status=status.HTTP_201_CREATED)


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
