from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .serializers import ContactMessageSerializer


class ContactMessageCreateView(APIView):
    """Public, unauthenticated endpoint for callback requests from the homepage."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Public enquiries'],
        summary='Submit a callback request',
        request=ContactMessageSerializer,
        responses={201: ContactMessageSerializer},
    )
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
