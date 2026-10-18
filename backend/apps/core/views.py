from django.conf import settings
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, extend_schema

from .serializers import ContactMessageSerializer


class SupportContactsSerializer(serializers.Serializer):
    phone = serializers.CharField()
    phone_display = serializers.CharField()
    phone_link = serializers.CharField(help_text='tel: link to open the dialer')
    email = serializers.EmailField()
    email_link = serializers.CharField(help_text='mailto: link to open the mail app')


class SupportContactsView(APIView):
    """Contact Us screen: helpline numbers and email support."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Patient profile'], summary='Contact Us: helpline number and support email',
        responses={200: SupportContactsSerializer},
        examples=[OpenApiExample('Support contacts', response_only=True, value={
            'phone': '+919818677599', 'phone_display': '98186 77599', 'phone_link': 'tel:+919818677599',
            'email': 'care@lalaharihealth.com', 'email_link': 'mailto:care@lalaharihealth.com',
        })],
    )
    def get(self, request):
        digits = settings.SUPPORT_PHONE_NUMBER[-10:]
        return Response({
            'phone': settings.SUPPORT_PHONE_NUMBER,
            'phone_display': f'{digits[:5]} {digits[5:]}',
            'phone_link': f'tel:{settings.SUPPORT_PHONE_NUMBER}',
            'email': settings.SUPPORT_EMAIL,
            'email_link': f'mailto:{settings.SUPPORT_EMAIL}',
        })


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
