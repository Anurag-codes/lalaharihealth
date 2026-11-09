# API endpoints for doctor onboarding, verification and public doctor listing/search.
from django.urls import path

from apps.appointments.doctor_app import (
    DoctorAppointmentCallDetailView, DoctorAppointmentCallListView, DoctorAppointmentDetailView,
    DoctorEarningsView, DoctorScheduleView,
)
from apps.appointments.doctor_views import DoctorSlotDetailView, DoctorSlotListCreateView
from apps.consultations.doctor_views import DoctorConsultationListView, DoctorConsultationRecordView
from .app_views import (
    DoctorAvailabilityView, DoctorDocumentDetailView, DoctorDocumentDownloadView, DoctorDocumentListView,
    DoctorMeView, DoctorPhotoView, QualificationListView,
)
from .views import DoctorApplicationCreateView, FeaturedDoctorListView, SpecialityListView

app_name = 'doctors'

urlpatterns = [
    path('specialities/', SpecialityListView.as_view(), name='speciality-list'),
    path('qualifications/', QualificationListView.as_view(), name='qualification-list'),
    path('featured/', FeaturedDoctorListView.as_view(), name='featured-doctor-list'),
    path('applications/', DoctorApplicationCreateView.as_view(), name='doctor-application-create'),
    path('me/', DoctorMeView.as_view(), name='doctor-me'),
    path('me/photo/', DoctorPhotoView.as_view(), name='doctor-photo'),
    path('me/documents/', DoctorDocumentListView.as_view(), name='doctor-document-list'),
    path('me/documents/<int:document_id>/', DoctorDocumentDetailView.as_view(), name='doctor-document-detail'),
    path('me/documents/<int:document_id>/download/', DoctorDocumentDownloadView.as_view(), name='doctor-document-download'),
    path('me/availability/', DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('me/schedule/', DoctorScheduleView.as_view(), name='doctor-schedule'),
    path('me/appointments/<int:appointment_id>/', DoctorAppointmentDetailView.as_view(), name='doctor-appointment-detail'),
    path('me/appointments/<int:appointment_id>/calls/', DoctorAppointmentCallListView.as_view(), name='doctor-appointment-calls'),
    path(
        'me/appointments/<int:appointment_id>/calls/<int:call_id>/', DoctorAppointmentCallDetailView.as_view(),
        name='doctor-appointment-call-detail',
    ),
    path('me/earnings/', DoctorEarningsView.as_view(), name='doctor-earnings'),
    path('me/slots/', DoctorSlotListCreateView.as_view(), name='doctor-slot-list'),
    path('me/slots/<int:slot_id>/', DoctorSlotDetailView.as_view(), name='doctor-slot-detail'),
    path('me/consultations/', DoctorConsultationListView.as_view(), name='doctor-consultation-list'),
    path(
        'me/consultations/<int:consultation_id>/record/', DoctorConsultationRecordView.as_view(),
        name='doctor-consultation-record',
    ),
]
