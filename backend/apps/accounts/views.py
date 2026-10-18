import ipaddress
import re

from django.conf import settings
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings as rest_settings
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .firebase import verify_phone_token
from .serializers import (
    EmailOtpRequestSerializer, EmailOtpResponseSerializer, EmailOtpVerifySerializer,
    FirebasePhoneSerializer, PatientAuthResponseSerializer, PatientLogoutSerializer,
    PatientRefreshSerializer, PatientSerializer, PatientUpdateSerializer,
)
from .services import (
    consume_email_otp, email_identity, patient_tokens, phone_identity, rate_limit,
    request_email_otp, require_patient,
)


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        require_patient(request.user)
        return True


def request_ip(request):
    address = request.META.get('REMOTE_ADDR') or 'unknown'
    if settings.PATIENT_AUTH_TRUST_PROXY_HEADERS:
        forwarded = request.META.get('HTTP_X_REAL_IP', '')
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return address


def auth_response(user, created):
    return Response({**patient_tokens(user), 'is_new_user': created, 'user': PatientSerializer(user).data})


class NoStoreResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response


@method_decorator(sensitive_post_parameters('otp', 'id_token', 'refresh'), name='dispatch')
class PublicAuthView(NoStoreResponseMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        return 'Bearer'


class EmailOtpRequestView(PublicAuthView):
    link = False

    @extend_schema(
        tags=['Patient authentication'], summary='Send a patient sign-in OTP by email',
        request=EmailOtpRequestSerializer, responses={202: EmailOtpResponseSerializer},
    )
    def post(self, request):
        serializer = EmailOtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        challenge = request_email_otp(
            serializer.validated_data['email'], request_ip(request),
            link_user=request.user if self.link else None,
        )
        response = Response({
            'request_id': str(challenge.id), 'expires_in': settings.EMAIL_OTP_EXPIRY_SECONDS,
            'resend_after': settings.EMAIL_OTP_RESEND_SECONDS,
            'detail': 'Verification email sent. Use the code to continue.',
        }, status=202)
        response['Cache-Control'] = 'no-store'
        return response


class EmailOtpVerifyView(PublicAuthView):
    link = False

    @extend_schema(
        tags=['Patient authentication'], summary='Verify email OTP and register or sign in a patient',
        request=EmailOtpVerifySerializer, responses=PatientAuthResponseSerializer,
    )
    def post(self, request):
        rate_limit('email-verify-ip', request_ip(request), settings.PATIENT_AUTH_VERIFY_HOURLY_LIMIT)
        serializer = EmailOtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = consume_email_otp(
            challenge_id=serializer.validated_data['request_id'], code=serializer.validated_data['otp'],
            link_user=request.user if self.link else None,
        )
        user, created = email_identity(email, link_user=request.user if self.link else None)
        return auth_response(user, created)


class FirebasePhoneView(PublicAuthView):
    link = False

    @extend_schema(
        tags=['Patient authentication'],
        summary='Exchange an app-verified Firebase phone ID token for patient JWTs',
        description='The Android/iOS app sends and verifies the SMS OTP with Firebase Phone Auth. Send its fresh ID token here. No phone number or verified flag is accepted as proof.',
        request=FirebasePhoneSerializer, responses=PatientAuthResponseSerializer,
    )
    def post(self, request):
        rate_limit('firebase-exchange-ip', request_ip(request), settings.PATIENT_AUTH_VERIFY_HOURLY_LIMIT)
        serializer = FirebasePhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data['id_token']
        claims = verify_phone_token(id_token)
        if not isinstance(claims.get('phone_number'), str) or not re.fullmatch(r'\+[1-9][0-9]{6,14}', claims['phone_number']):
            raise AuthenticationFailed('Firebase token must contain a verified E.164 phone number.')
        user, created = phone_identity(id_token, claims, link_user=request.user if self.link else None)
        return auth_response(user, created)


class PatientLinkMixin:
    link = True
    permission_classes = [IsAuthenticated, IsPatient]
    # Restore JWT/session authentication, disabled only on anonymous sign-in endpoints.
    authentication_classes = rest_settings.DEFAULT_AUTHENTICATION_CLASSES


@extend_schema_view(post=extend_schema(tags=['Patient authentication'], summary='Send an email OTP to link to the signed-in patient'))
class LinkEmailRequestView(PatientLinkMixin, EmailOtpRequestView):
    pass


@extend_schema_view(post=extend_schema(tags=['Patient authentication'], summary='Verify and link email to the signed-in patient'))
class LinkEmailVerifyView(PatientLinkMixin, EmailOtpVerifyView):
    pass


@extend_schema_view(post=extend_schema(tags=['Patient authentication'], summary='Link an app-verified phone to the signed-in patient'))
class LinkPhoneView(PatientLinkMixin, FirebasePhoneView):
    pass


class PatientMeView(PublicAuthView):
    permission_classes = [IsAuthenticated, IsPatient]
    authentication_classes = rest_settings.DEFAULT_AUTHENTICATION_CLASSES

    @extend_schema(tags=['Patient authentication'], summary='Read the signed-in patient', responses=PatientSerializer)
    def get(self, request):
        return Response(PatientSerializer(request.user).data)

    @extend_schema(tags=['Patient authentication'], summary='Update patient name and city (not verified contacts)', request=PatientUpdateSerializer, responses=PatientSerializer)
    def patch(self, request):
        serializer = PatientUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PatientSerializer(request.user).data)


class PatientRefreshView(NoStoreResponseMixin, TokenRefreshView):
    serializer_class = PatientRefreshSerializer

    @extend_schema(tags=['Patient authentication'], summary='Refresh patient JWTs (rotates and revokes the used refresh token)')
    def post(self, request, *args, **kwargs):
        rate_limit('patient-refresh-ip', request_ip(request), settings.PATIENT_AUTH_VERIFY_HOURLY_LIMIT)
        return super().post(request, *args, **kwargs)


class PatientLogoutView(NoStoreResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(tags=['Patient authentication'], summary='Revoke this patient refresh token', request=PatientLogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = PatientLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            if str(token.get(api_settings.USER_ID_CLAIM)) != str(request.user.pk):
                raise InvalidToken('The refresh token does not belong to this account.')
            token.blacklist()
        except TokenError:
            raise InvalidToken('Invalid or already revoked refresh token.') from None
        return Response(status=204)
