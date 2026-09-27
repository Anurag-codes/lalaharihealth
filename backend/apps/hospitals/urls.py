# API endpoints for hospital search/recommendation.
from django.urls import path

from .views import HospitalApplicationCreateView

app_name = 'hospitals'

urlpatterns = [
    path('applications/', HospitalApplicationCreateView.as_view(), name='hospital-application-create'),
]
