from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HospitalApplication, HospitalApplicationDocument
from .serializers import HospitalApplicationSerializer

MAX_APPLICATION_DOCUMENTS = 5


class HospitalApplicationCreateView(APIView):
    """Public, unauthenticated endpoint for the pre-launch hospital/clinic interest form."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = HospitalApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()

        uploaded_files = request.FILES.getlist('documents')[:MAX_APPLICATION_DOCUMENTS]
        for uploaded_file in uploaded_files:
            HospitalApplicationDocument.objects.create(application=application, file=uploaded_file)

        response_data = HospitalApplicationSerializer(application).data
        return Response(response_data, status=status.HTTP_201_CREATED)
