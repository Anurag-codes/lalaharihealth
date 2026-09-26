from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .views import ContactMessageCreateView

app_name = 'core'


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'service': 'LalahariHealth API'})


urlpatterns = [
    path('contact-messages/', ContactMessageCreateView.as_view(), name='contact-message-create'),
]

