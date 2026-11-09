"""Doctor app sign-in with Firebase phone OTP. Doctor accounts are separate from patient accounts on the same number."""
import re

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from apps.doctors.app_serializers import DoctorMeSerializer
from apps.doctors.app_views import DOCTOR_ME_EXAMPLE, IsDoctor, my_profile
from .firebase import verify_phone_token
from .models import User
from .serializers import DoctorRefreshSerializer, FirebasePhoneSerializer, PatientLogoutSerializer
from .services import doctor_tokens, phone_identity, rate_limit
from .views import NoStoreResponseMixin, PatientLogoutView, PublicAuthView, request_ip

TAG = 'Doctor app: authentication'
TOKENS_EXAMPLE = {'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access', 'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh'}


class DoctorAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    is_new_user = serializers.BooleanField(help_text='true when this sign-in created the doctor account')
    doctor = DoctorMeSerializer()


class DoctorFirebasePhoneView(PublicAuthView):
    @extend_schema(
        tags=[TAG], summary='Doctor sign up / sign in: exchange a Firebase phone ID token for doctor JWTs',
        description=(
            'The doctor app sends and verifies the SMS OTP with Firebase Phone Auth (Sign Up and Verify Your Number screens), '
            'then sends the fresh Firebase ID token here. A new number creates a doctor account (`is_new_user: true`), '
            'separate from any patient account on the same number. If the number was used in the website For Doctors form, '
            'its name, qualification, speciality, experience, city, photo and documents are copied into the profile. '
            'Every new doctor is Pending Review until staff verify them. Open the screen in `doctor.onboarding.next_step`. '
            'Store `access` (60 minutes) and `refresh` (7 days) securely. 401 = invalid, expired or reused token; '
            '403 = the number belongs to a staff or deactivated account; 503 = Firebase is not configured on the server.'
        ),
        request=FirebasePhoneSerializer, responses=DoctorAuthResponseSerializer,
        examples=[
            OpenApiExample('Firebase ID token', request_only=True, value={'id_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...firebase-id-token'}),
            OpenApiExample('Signed in', response_only=True, value={**TOKENS_EXAMPLE, 'is_new_user': True, 'doctor': DOCTOR_ME_EXAMPLE}),
        ],
    )
    def post(self, request):
        rate_limit('doctor-firebase-exchange-ip', request_ip(request), settings.PATIENT_AUTH_VERIFY_HOURLY_LIMIT)
        serializer = FirebasePhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data['id_token']
        claims = verify_phone_token(id_token)
        if not isinstance(claims.get('phone_number'), str) or not re.fullmatch(r'\+[1-9][0-9]{6,14}', claims['phone_number']):
            raise AuthenticationFailed('Firebase token must contain a verified E.164 phone number.')
        user, created = phone_identity(id_token, claims, role=User.Role.DOCTOR)
        request.user = user
        doctor = DoctorMeSerializer(my_profile(request), context={'request': request}).data
        return Response({**doctor_tokens(user), 'is_new_user': created, 'doctor': doctor})


class DoctorRefreshView(NoStoreResponseMixin, TokenRefreshView):
    serializer_class = DoctorRefreshSerializer

    @extend_schema(
        tags=[TAG], summary='Refresh doctor JWTs (rotates and revokes the used refresh token)',
        description='Send the doctor refresh token; returns a new access and refresh token. 401 if it is expired, revoked or not a doctor token.',
        examples=[
            OpenApiExample('Refresh', request_only=True, value={'refresh': TOKENS_EXAMPLE['refresh']}),
            OpenApiExample('New tokens', response_only=True, value=TOKENS_EXAMPLE),
        ],
    )
    def post(self, request, *args, **kwargs):
        rate_limit('doctor-refresh-ip', request_ip(request), settings.PATIENT_AUTH_VERIFY_HOURLY_LIMIT)
        return super().post(request, *args, **kwargs)


class DoctorLogoutView(PatientLogoutView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @extend_schema(
        tags=[TAG], summary='Log out: revoke this doctor refresh token',
        description=(
            'Call POST /api/v1/notifications/devices/remove/ first, then send the current refresh token here and delete '
            'the stored tokens. Returns 204.'
        ),
        examples=[OpenApiExample('Logout', request_only=True, value={'refresh': TOKENS_EXAMPLE['refresh']})],
        request=PatientLogoutSerializer, responses={204: None},
    )
    def post(self, request):
        return super().post(request)
