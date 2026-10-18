import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone as datetime_timezone
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, Throttled, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.patients.models import PatientProfile
from .firebase import AuthServiceUnavailable
from .models import AuthRateLimit, EmailOtpChallenge, UsedFirebaseToken, User, VerifiedIdentity

logger = logging.getLogger(__name__)


def require_patient(user):
    if not user.is_active or user.role != User.Role.PATIENT or user.is_staff or user.is_superuser:
        raise PermissionDenied('An active patient account is required.')


def rate_limit(scope, identifier, limit, window_seconds=3600, cooldown_seconds=0):
    key = salted_hmac('patient-auth-rate', f'{scope}:{identifier}', algorithm='sha256').hexdigest()
    now = timezone.now()
    with transaction.atomic():
        AuthRateLimit.objects.get_or_create(key=key, defaults={'window_start': now})
        bucket = AuthRateLimit.objects.select_for_update().get(pk=key)
        if bucket.next_allowed_at and bucket.next_allowed_at > now:
            raise Throttled(wait=max(1, int((bucket.next_allowed_at - now).total_seconds())))
        if now >= bucket.window_start + timedelta(seconds=window_seconds):
            bucket.window_start = now
            bucket.count = 0
        if bucket.count >= limit:
            raise Throttled(wait=max(1, int((bucket.window_start + timedelta(seconds=window_seconds) - now).total_seconds())))
        bucket.count += 1
        bucket.next_allowed_at = now + timedelta(seconds=cooldown_seconds) if cooldown_seconds else None
        bucket.save()


def otp_digest(challenge_id, code):
    return salted_hmac('patient-email-otp', f'{challenge_id}:{code}', algorithm='sha256').hexdigest()


def request_email_otp(email, ip, link_user=None):
    if link_user:
        require_patient(link_user)
    if (
        settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend'
        or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
        or not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL
        or settings.EMAIL_USE_TLS == settings.EMAIL_USE_SSL
    ):
        raise AuthServiceUnavailable('Email sign-in is not configured. Please contact support.')
    rate_limit('email-send-ip', ip, settings.EMAIL_OTP_IP_HOURLY_LIMIT)
    rate_limit('email-send-address', email, settings.EMAIL_OTP_ADDRESS_HOURLY_LIMIT, cooldown_seconds=settings.EMAIL_OTP_RESEND_SECONDS)
    now = timezone.now()
    code = f'{secrets.randbelow(1_000_000):06d}'
    with transaction.atomic():
        EmailOtpChallenge.objects.filter(email=email, consumed_at__isnull=True).update(consumed_at=now)
        challenge = EmailOtpChallenge(
            email=email, link_user=link_user,
            expires_at=now + timedelta(seconds=settings.EMAIL_OTP_EXPIRY_SECONDS),
        )
        challenge.code_digest = otp_digest(challenge.id, code)
        challenge.save()
    try:
        sent = send_mail(
            'Your LalahariHealth verification code',
            f'Your LalahariHealth verification code is {code}.\n\n'
            f'It expires in {settings.EMAIL_OTP_EXPIRY_SECONDS // 60} minutes. '
            'Do not share this code. If you did not request it, ignore this email.\n'
            'This code verifies your email for patient sign-in or account linking.',
            settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,
        )
    except (SMTPException, OSError):
        EmailOtpChallenge.objects.filter(pk=challenge.pk).update(consumed_at=timezone.now())
        logger.error('Patient email OTP delivery failed.')
        raise AuthServiceUnavailable('The verification email could not be sent. Please try again later.') from None
    if sent != 1:
        EmailOtpChallenge.objects.filter(pk=challenge.pk).update(consumed_at=timezone.now())
        logger.error('SMTP did not confirm patient OTP delivery.')
        raise AuthServiceUnavailable('The verification email could not be sent. Please try again later.')
    challenge.delivered_at = timezone.now()
    challenge.save(update_fields=['delivered_at'])
    return challenge


def consume_email_otp(challenge_id, code, link_user=None):
    now = timezone.now()
    valid = False
    email = None
    with transaction.atomic():
        challenge = EmailOtpChallenge.objects.select_for_update().filter(pk=challenge_id).first()
        if (
            challenge and challenge.link_user_id == (link_user.pk if link_user else None)
            and challenge.delivered_at and not challenge.consumed_at and challenge.expires_at > now
            and challenge.attempts < settings.EMAIL_OTP_MAX_ATTEMPTS
        ):
            challenge.attempts += 1
            valid = constant_time_compare(challenge.code_digest, otp_digest(challenge.id, code))
            if valid or challenge.attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
                challenge.consumed_at = now
            challenge.save(update_fields=['attempts', 'consumed_at'])
            email = challenge.email
    if not valid:
        raise ValidationError({'otp': 'Invalid or expired code. Request a new code if needed.'})
    return email


def resolve_identity(kind, value, link_user=None, firebase_uid=None):
    """Call inside an atomic block; database uniqueness arbitrates concurrent sign-ins."""
    if link_user:
        user = User.objects.select_for_update().get(pk=link_user.pk)
        require_patient(user)
    else:
        user = None
    identity = VerifiedIdentity.objects.select_for_update().filter(kind=kind, value=value).first()
    if firebase_uid:
        uid_identity = VerifiedIdentity.objects.filter(firebase_uid=firebase_uid).first()
        if uid_identity and (identity is None or uid_identity.pk != identity.pk):
            raise ValidationError('This Firebase account is already associated with another phone number. Contact support.')
    created = False
    if identity:
        if user and identity.user_id != user.pk:
            raise ValidationError('This contact is already linked to another account. Accounts cannot be merged automatically.')
        user = User.objects.select_for_update().get(pk=identity.user_id)
        require_patient(user)
        if firebase_uid and identity.firebase_uid != firebase_uid:
            raise ValidationError('This phone number has a different Firebase identity. Contact support to recover the account.')
    else:
        if user and VerifiedIdentity.objects.filter(user=user, kind=kind).exists():
            raise ValidationError('This account already has a verified contact of this type. Contact support to change it.')
        # Existing profile fields are not proof of ownership. Require explicit migration or linking.
        legacy = User.objects.filter(email__iexact=value) if kind == 'email' else User.objects.filter(phone_number=value)
        if legacy.exclude(pk=user.pk if user else None).exists():
            raise ValidationError('This contact is present on an existing account. Sign in to that account to link it, or contact support.')
        if user is None:
            user = User.objects.create_user(username=f'patient_{secrets.token_hex(16)}', password=None, role=User.Role.PATIENT)
            created = True
        identity = VerifiedIdentity.objects.create(user=user, kind=kind, value=value, firebase_uid=firebase_uid)
    if kind == VerifiedIdentity.Kind.EMAIL:
        user.email = value
        user.is_email_verified = True
        user.save(update_fields=['email', 'is_email_verified'])
    else:
        user.phone_number = value
        user.is_phone_verified = True
        user.save(update_fields=['phone_number', 'is_phone_verified'])
    PatientProfile.objects.get_or_create(user=user)
    return user, created


def email_identity(email, link_user=None):
    try:
        with transaction.atomic():
            return resolve_identity(VerifiedIdentity.Kind.EMAIL, email, link_user=link_user)
    except IntegrityError:
        raise ValidationError('A simultaneous account update occurred. Please sign in again or contact support.') from None


def phone_identity(id_token, claims, link_user=None):
    digest = hashlib.sha256(id_token.encode()).hexdigest()
    try:
        with transaction.atomic():
            if UsedFirebaseToken.objects.filter(pk=digest).exists():
                raise AuthenticationFailed('This Firebase token has already been exchanged. Verify your phone again.')
            UsedFirebaseToken.objects.create(
                digest=digest,
                expires_at=datetime.fromtimestamp(claims['exp'], tz=datetime_timezone.utc),
            )
            return resolve_identity(
                VerifiedIdentity.Kind.PHONE, claims['phone_number'],
                link_user=link_user, firebase_uid=claims['uid'],
            )
    except IntegrityError:
        raise ValidationError('This token or contact was already used in another request. Please sign in again.') from None


def patient_tokens(user):
    require_patient(user)
    refresh = RefreshToken.for_user(user)
    refresh['auth_scope'] = 'patient'
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}
