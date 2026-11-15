from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.appointments.models import Appointment, AppointmentSlot
from apps.doctors.models import DoctorProfile
from apps.notifications.models import DeviceToken
from .models import EmailOtpChallenge, User, VerifiedIdentity
from .services import lock_contact, require_role
from .views import NoStoreResponseMixin


def delete_account(user_id, role):
    with transaction.atomic():
        snapshot = User.objects.get(pk=user_id)
        contacts = set(VerifiedIdentity.objects.filter(user_id=user_id, retired_at__isnull=True).values_list('kind', 'value'))
        if snapshot.email:
            contacts.add((VerifiedIdentity.Kind.EMAIL, snapshot.email.lower()))
        if snapshot.phone_number:
            contacts.add((VerifiedIdentity.Kind.PHONE, snapshot.phone_number))
        for kind, value in sorted(contacts):
            lock_contact(role, kind, value)
        user = User.objects.select_for_update().get(pk=user_id)
        if user.deleted_at is not None:
            return user.deleted_at, unfinished_appointments(user)
        require_role(user, role)
        now = timezone.now()
        user.is_active = False
        user.deleted_at = now
        user.is_phone_verified = False
        user.is_email_verified = False
        user.set_unusable_password()
        user.save(update_fields=['is_active', 'deleted_at', 'is_phone_verified', 'is_email_verified', 'password'])
        identities = VerifiedIdentity.objects.filter(user=user, retired_at__isnull=True)
        emails = set(identities.filter(kind=VerifiedIdentity.Kind.EMAIL).values_list('value', flat=True))
        if user.email:
            emails.add(user.email.lower())
        identities.update(retired_at=now)
        challenges = Q(link_user=user)
        if role == User.Role.PATIENT:
            challenges |= Q(email__in=emails, created_at__lte=now)
        EmailOtpChallenge.objects.filter(challenges, consumed_at__isnull=True).update(consumed_at=now)
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        DeviceToken.objects.filter(user=user).delete()
        if role == User.Role.DOCTOR:
            DoctorProfile.objects.filter(user=user).update(is_active=False, account_deleted_at=now)
            AppointmentSlot.objects.filter(doctor=user, is_active=True).update(is_active=False)
        return now, unfinished_appointments(user)


def unfinished_appointments(user):
    owner = Q(patient=user) if user.role == User.Role.PATIENT else Q(doctor=user) | Q(free_consultation_doctor=user)
    return Appointment.objects.filter(owner).exclude(status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]).count()


class AccountDeletionRequestSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(help_text='Explicit user confirmation. Must be true.')

    def validate(self, attrs):
        unsupported = set(self.initial_data) - {'confirm'}
        if unsupported:
            raise serializers.ValidationError({key: 'Only your authenticated account can be deleted; send confirm only.' for key in sorted(unsupported)})
        if attrs['confirm'] is not True:
            raise serializers.ValidationError({'confirm': 'Confirm account deletion to continue.'})
        return attrs


class AccountDeletionResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    status = serializers.CharField(help_text='account_closed; retained-data review is still required, not a claim of complete data erasure.')
    deleted_at = serializers.DateTimeField()
    records_retained = serializers.BooleanField()
    unfinished_appointments = serializers.IntegerField()


DELETE_DESCRIPTION = (
    'Authenticated, explicit account closure. Send {"confirm": true}. Disables only your own account, revokes all '
    'backend refresh tokens, blocks old access JWTs and removes push-device registrations. Clinical, appointment, '
    'payment, invoice/settlement and attribution records remain under the old account for restricted retention/review; '
    'this is not full data erasure. Unfinished appointments stay unchanged for staff resolution; no automatic cancellation '
    'or refund. The same contact can register a separate account only after a fresh OTP authenticated after closure. '
    'Old account records/verification are not transferred. Patient and doctor accounts on the same phone are separate. '
    'After success clear local data/tokens and sign out of Firebase. Repeating with an old JWT returns 401 because access '
    'was revoked; do not automatically sign in or create a new account to retry deletion.'
)
DELETE_EXAMPLE = {
    'detail': 'Account access closed. Your data-deletion request is recorded; retained data and unfinished appointments require staff review.',
    'status': 'account_closed',
    'deleted_at': '2026-11-15T06:45:00+05:30', 'records_retained': True, 'unfinished_appointments': 1,
}


class AccountDeletionView(NoStoreResponseMixin, APIView):
    permission_classes = [IsAuthenticated]
    role = User.Role.PATIENT

    def perform_delete(self, request):
        require_role(request.user, self.role)
        serializer = AccountDeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deleted_at, unfinished = delete_account(request.user.pk, self.role)
        return Response({**DELETE_EXAMPLE, 'deleted_at': deleted_at, 'unfinished_appointments': unfinished})


class PatientAccountDeletionView(AccountDeletionView):
    @extend_schema(
        tags=['Patient authentication'], summary='Delete the signed-in patient account (retain clinical/financial records)',
        description=DELETE_DESCRIPTION, request=AccountDeletionRequestSerializer, responses=AccountDeletionResponseSerializer,
        examples=[OpenApiExample('Confirm deletion', request_only=True, value={'confirm': True}),
                  OpenApiExample('Account closed', response_only=True, value=DELETE_EXAMPLE)],
    )
    def delete(self, request):
        return self.perform_delete(request)


class DoctorAccountDeletionView(AccountDeletionView):
    role = User.Role.DOCTOR

    @extend_schema(
        tags=['Doctor app: authentication'], summary='Delete the signed-in doctor account (retain clinical/financial records)',
        description=DELETE_DESCRIPTION + ' Disables doctor availability. New signup requires onboarding and fresh staff verification.',
        request=AccountDeletionRequestSerializer, responses=AccountDeletionResponseSerializer,
        examples=[OpenApiExample('Confirm deletion', request_only=True, value={'confirm': True}),
                  OpenApiExample('Account closed', response_only=True, value=DELETE_EXAMPLE)],
    )
    def delete(self, request):
        return self.perform_delete(request)
