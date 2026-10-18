# API endpoints for doctor onboarding, verification and public doctor listing/search.
from django.urls import path

from apps.appointments.doctor_views import DoctorSlotDetailView, DoctorSlotListCreateView
from apps.consultations.doctor_views import DoctorConsultationListView, DoctorConsultationRecordView
from .views import DoctorApplicationCreateView, SpecialityListView

app_name = 'doctors'

urlpatterns = [
    path('specialities/', SpecialityListView.as_view(), name='speciality-list'),
    path('applications/', DoctorApplicationCreateView.as_view(), name='doctor-application-create'),
    path('me/slots/', DoctorSlotListCreateView.as_view(), name='doctor-slot-list'),
    path('me/slots/<int:slot_id>/', DoctorSlotDetailView.as_view(), name='doctor-slot-detail'),
    path('me/consultations/', DoctorConsultationListView.as_view(), name='doctor-consultation-list'),
    path(
        'me/consultations/<int:consultation_id>/record/', DoctorConsultationRecordView.as_view(),
        name='doctor-consultation-record',
    ),
]
