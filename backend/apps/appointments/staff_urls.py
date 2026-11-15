from django.urls import path

from apps.accounts.staff_views import StaffMeView
from . import staff_views

app_name = 'staff'

urlpatterns = [
    path('me/', StaffMeView.as_view(), name='me'),
    path('summary/', staff_views.StaffSummaryView.as_view(), name='summary'),
    path('appointments/', staff_views.StaffAppointmentListView.as_view(), name='appointment-list'),
    path('appointments/<int:appointment_id>/', staff_views.StaffAppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/<int:appointment_id>/patient/', staff_views.StaffPatientUpdateView.as_view(), name='appointment-patient'),
    path('appointments/<int:appointment_id>/doctors/', staff_views.StaffDoctorChoicesView.as_view(), name='appointment-doctors'),
    path(
        'appointments/<int:appointment_id>/documents/<int:document_id>/download/',
        staff_views.StaffDocumentDownloadView.as_view(), name='appointment-document-download',
    ),
    path('doctors/', staff_views.StaffDoctorListView.as_view(), name='doctor-list'),
    path('doctors/<int:doctor_id>/schedule/', staff_views.StaffDoctorScheduleView.as_view(), name='doctor-schedule'),
]
