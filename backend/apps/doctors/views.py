from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DoctorApplication, DoctorApplicationDocument
from .serializers import DoctorApplicationSerializer

MAX_APPLICATION_DOCUMENTS = 5


class DoctorApplicationCreateView(APIView):
    """Public, unauthenticated endpoint for the pre-launch doctor onboarding interest form."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DoctorApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()

        uploaded_files = request.FILES.getlist('documents')[:MAX_APPLICATION_DOCUMENTS]
        for uploaded_file in uploaded_files:
            DoctorApplicationDocument.objects.create(application=application, file=uploaded_file)

        response_data = DoctorApplicationSerializer(application).data
        return Response(response_data, status=status.HTTP_201_CREATED)
