# API endpoints for doctor onboarding, verification and public doctor listing/search.
from django.urls import path

from .views import DoctorApplicationCreateView

app_name = 'doctors'

urlpatterns = [
    path('applications/', DoctorApplicationCreateView.as_view(), name='doctor-application-create'),
]
