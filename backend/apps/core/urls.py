from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from .views import ContactMessageCreateView

app_name = 'core'


@extend_schema(
    tags=['System'],
    summary='Check API health',
    responses={200: OpenApiResponse(description='The API is available.')},
)
@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'service': 'LalahariHealth API'})


urlpatterns = [
    path('contact-messages/', ContactMessageCreateView.as_view(), name='contact-message-create'),
]

