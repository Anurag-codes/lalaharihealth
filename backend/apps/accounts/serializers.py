from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings

from .models import User, VerifiedIdentity
from .services import require_patient


class EmailOtpRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return value.strip().lower()


class EmailOtpVerifySerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    otp = serializers.RegexField(r'^[0-9]{6}$', max_length=6, min_length=6, write_only=True)


class FirebasePhoneSerializer(serializers.Serializer):
    id_token = serializers.CharField(max_length=8192, trim_whitespace=False, write_only=True)


class EmailOtpResponseSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    expires_in = serializers.IntegerField()
    resend_after = serializers.IntegerField()
    detail = serializers.CharField()


class VerifiedIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifiedIdentity
        fields = ['kind', 'value', 'verified_at']
        read_only_fields = fields


class PatientSerializer(serializers.ModelSerializer):
    identities = VerifiedIdentitySerializer(source='verified_identities', many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'city', 'role', 'email',
            'phone_number', 'is_email_verified', 'is_phone_verified', 'identities',
        ]
        read_only_fields = fields


class PatientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'city']

    def validate(self, attrs):
        unsupported = set(self.initial_data) - set(self.fields)
        if unsupported:
            raise serializers.ValidationError({
                field: 'This field cannot be updated here. Use verified contact linking for email or phone.'
                for field in sorted(unsupported)
            })
        return attrs


class PatientAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    is_new_user = serializers.BooleanField()
    user = PatientSerializer()


class PatientRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])
        if refresh.get('auth_scope') != 'patient':
            raise InvalidToken('Use a patient sign-in token.')
        user = User.objects.filter(pk=refresh.get(api_settings.USER_ID_CLAIM)).first()
        if user is None:
            raise InvalidToken('The patient account no longer exists.')
        require_patient(user)
        return super().validate(attrs)


class PatientLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=8192, write_only=True)
