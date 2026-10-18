from django.urls import path

from . import cases, views

app_name = 'patients'

urlpatterns = [
    path('home/', cases.PatientHomeView.as_view(), name='home'),
    path('cases/', cases.CaseListView.as_view(), name='case-list'),
    path('cases/<int:consultation_id>/', cases.CaseDetailView.as_view(), name='case-detail'),
    path('profile/', views.PatientProfileView.as_view(), name='profile'),
    path('profile/photo/', views.PatientProfilePhotoView.as_view(), name='profile-photo'),
    path('booking-patients/', views.BookingPatientListView.as_view(), name='booking-patient-list'),
    path('family-members/', views.FamilyMemberListCreateView.as_view(), name='family-member-list'),
    path('family-members/<int:member_id>/', views.FamilyMemberDetailView.as_view(), name='family-member-detail'),
    path('medical-records/', views.MedicalRecordListView.as_view(), name='medical-record-list'),
    path('medical-records/<int:consultation_id>/', views.MedicalRecordDetailView.as_view(), name='medical-record-detail'),
]
