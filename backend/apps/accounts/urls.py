from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .doctor_views import DoctorFirebasePhoneView, DoctorLogoutView, DoctorRefreshView
from .staff_views import StaffLoginView, StaffLogoutView
from .deletion import DoctorAccountDeletionView, PatientAccountDeletionView
from .views import (
    EmailOtpRequestView, EmailOtpVerifyView, FirebasePhoneView,
    LinkEmailRequestView, LinkEmailVerifyView, LinkPhoneView,
    PatientLogoutView, PatientMeView, PatientRefreshView,
)

app_name = 'accounts'

urlpatterns = [
    path('patient/account/', PatientAccountDeletionView.as_view(), name='patient-delete-account'),
    path('doctor/account/', DoctorAccountDeletionView.as_view(), name='doctor-delete-account'),
    path('token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('patient/email/request-otp/', EmailOtpRequestView.as_view(), name='patient-email-request'),
    path('patient/email/verify-otp/', EmailOtpVerifyView.as_view(), name='patient-email-verify'),
    path('patient/phone/firebase/', FirebasePhoneView.as_view(), name='patient-phone'),
    path('patient/link/email/request-otp/', LinkEmailRequestView.as_view(), name='patient-link-email-request'),
    path('patient/link/email/verify-otp/', LinkEmailVerifyView.as_view(), name='patient-link-email-verify'),
    path('patient/link/phone/', LinkPhoneView.as_view(), name='patient-link-phone'),
    path('patient/me/', PatientMeView.as_view(), name='patient-me'),
    path('patient/token/refresh/', PatientRefreshView.as_view(), name='patient-refresh'),
    path('patient/logout/', PatientLogoutView.as_view(), name='patient-logout'),
    path('doctor/phone/firebase/', DoctorFirebasePhoneView.as_view(), name='doctor-phone'),
    path('doctor/token/refresh/', DoctorRefreshView.as_view(), name='doctor-refresh'),
    path('doctor/logout/', DoctorLogoutView.as_view(), name='doctor-logout'),
    path('staff/login/', StaffLoginView.as_view(), name='staff-login'),
    path('staff/logout/', StaffLogoutView.as_view(), name='staff-logout'),
]
