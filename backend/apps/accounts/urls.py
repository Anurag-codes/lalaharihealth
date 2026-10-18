from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    EmailOtpRequestView, EmailOtpVerifyView, FirebasePhoneView,
    LinkEmailRequestView, LinkEmailVerifyView, LinkPhoneView,
    PatientLogoutView, PatientMeView, PatientRefreshView,
)

app_name = 'accounts'

urlpatterns = [
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
]
