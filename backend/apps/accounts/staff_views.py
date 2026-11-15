"""Username/password sign-in for the staff web console (Django users with is_staff)."""
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .services import rate_limit
from .views import NoStoreResponseMixin, request_ip

INVALID_LOGIN = 'Invalid username or password.'


class IsStaffUser(BasePermission):
    message = 'A staff account is required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class StaffUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    email = serializers.CharField(allow_blank=True)
    is_superuser = serializers.BooleanField()

    def get_full_name(self, user) -> str:
        return user.get_full_name()


class StaffLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True, style={'input_type': 'password'})


class StaffLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text='Access JWT (60 minutes). Keep it server-side, e.g. in an httpOnly cookie.')
    refresh = serializers.CharField(help_text='Refresh JWT (7 days, rotated by POST /api/v1/auth/token/refresh/).')
    user = StaffUserSerializer()


class StaffLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


STAFF_USER_EXAMPLE = {'id': 3, 'username': 'ops.priya', 'full_name': 'Priya Verma', 'email': 'ops@example.com', 'is_superuser': False}


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class StaffLoginView(NoStoreResponseMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        return 'Bearer'

    @extend_schema(
        tags=['Staff console'], summary='Staff console: sign in with username and password',
        description=(
            'Only active staff accounts (Django admin users with "Staff status") receive tokens; every other account gets '
            'the same 401 as a wrong password. Attempts are rate limited per username and per client IP (429). '
            'The web console keeps these tokens server-side in httpOnly cookies; never store them in browser JavaScript.'
        ),
        request=StaffLoginSerializer, responses={200: StaffLoginResponseSerializer},
        examples=[
            OpenApiExample('Sign in', request_only=True, value={'username': 'ops.priya', 'password': '<password>'}),
            OpenApiExample('Signed in', response_only=True, value={
                'access': '<access-jwt>', 'refresh': '<refresh-jwt>', 'user': STAFF_USER_EXAMPLE,
            }),
        ],
    )
    def post(self, request):
        rate_limit('staff-login-ip', request_ip(request), settings.STAFF_LOGIN_IP_HOURLY_LIMIT)
        serializer = StaffLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username'].strip()
        rate_limit('staff-login-user', username.lower(), settings.STAFF_LOGIN_USER_HOURLY_LIMIT)
        user = authenticate(request._request, username=username, password=serializer.validated_data['password'])
        if user is None or not user.is_active or not user.is_staff:
            raise AuthenticationFailed(INVALID_LOGIN)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token), 'refresh': str(refresh), 'user': StaffUserSerializer(user).data,
        })


@method_decorator(sensitive_post_parameters('refresh'), name='dispatch')
class StaffLogoutView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffLogoutSerializer

    @extend_schema(
        tags=['Staff console'], summary='Staff console: revoke the refresh token',
        description='Blacklists the given refresh token of the signed-in staff member. Returns 204.',
        responses={204: None},
        examples=[OpenApiExample('Sign out', request_only=True, value={'refresh': '<refresh-jwt>'})],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            if str(token.get(api_settings.USER_ID_CLAIM)) != str(request.user.pk):
                raise InvalidToken('The refresh token does not belong to this account.')
            token.blacklist()
        except TokenError:
            raise InvalidToken('Invalid or already revoked refresh token.') from None
        return Response(status=204)


class StaffMeView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = StaffUserSerializer

    @extend_schema(
        tags=['Staff console'], summary='Staff console: the signed-in staff member',
        description='403 when the account is not active staff.',
        examples=[OpenApiExample('Staff member', response_only=True, value=STAFF_USER_EXAMPLE)],
    )
    def get(self, request):
        return Response(self.get_serializer(request.user).data)
