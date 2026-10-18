import time
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from firebase_admin import auth
from firebase_admin.exceptions import UnavailableError
from rest_framework.test import APIClient
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.patients.models import PatientProfile
from .firebase import verify_phone_token
from .models import AuthRateLimit, EmailOtpChallenge, UsedFirebaseToken, User, VerifiedIdentity
from .services import patient_tokens


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    EMAIL_HOST_USER='sender@example.com', EMAIL_HOST_PASSWORD='test-only-password',
    DEFAULT_FROM_EMAIL='sender@example.com', FIREBASE_PROJECT_ID='test-project',
)
class PatientAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mail = patch('apps.accounts.services.send_mail', return_value=1).start()
        self.random_code = patch('apps.accounts.services.secrets.randbelow', return_value=123456).start()
        self.addCleanup(patch.stopall)

    def endpoint(self, name):
        return reverse(f'accounts:patient-{name}')

    def request_code(self, email='patient@example.com', link=False):
        return self.client.post(self.endpoint('link-email-request' if link else 'email-request'), {'email': email}, format='json')

    def verify_code(self, request_id, otp='123456', link=False):
        return self.client.post(
            self.endpoint('link-email-verify' if link else 'email-verify'),
            {'request_id': str(request_id), 'otp': otp}, format='json',
        )

    def email_login(self, email='patient@example.com'):
        request = self.request_code(email)
        self.assertEqual(request.status_code, 202, request.data)
        response = self.verify_code(request.data['request_id'])
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def authenticate(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {patient_tokens(user)["access"]}')

    def phone_claims(self, **overrides):
        return {
            'uid': 'firebase-patient-1', 'phone_number': '+919812345678',
            'auth_time': int(time.time()), 'exp': int(time.time()) + 3600,
            'firebase': {'sign_in_provider': 'phone'}, **overrides,
        }

    def phone(self, token='phone-token', claims=None, link=False):
        with patch('apps.accounts.views.verify_phone_token', return_value=claims or self.phone_claims()):
            return self.client.post(
                self.endpoint('link-phone' if link else 'phone'),
                {'id_token': token}, format='json',
            )

    def test_email_request_normalizes_and_never_returns_or_stores_plaintext_code(self):
        response = self.request_code(' Patient@Example.COM ')
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response['Cache-Control'], 'no-store')
        challenge = EmailOtpChallenge.objects.get(pk=response.data['request_id'])
        self.assertEqual(challenge.email, 'patient@example.com')
        self.assertNotEqual(challenge.code_digest, '123456')
        self.assertNotIn('123456', str(response.data))
        self.assertEqual(response.data['expires_in'], 300)
        self.assertIn('123456', self.mail.call_args.args[1])
        self.assertFalse(User.objects.exists())

    def test_email_signup_existing_login_and_patient_profile(self):
        response = self.email_login()
        self.assertTrue(response.data['is_new_user'])
        user = User.objects.get(pk=response.data['user']['id'])
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.role, 'patient')
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_email_verified)
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())
        self.assertEqual(user.verified_identities.get().value, 'patient@example.com')
        AuthRateLimit.objects.all().delete()
        response = self.email_login('PATIENT@example.com')
        self.assertFalse(response.data['is_new_user'])
        self.assertEqual(response.data['user']['id'], user.pk)
        self.assertEqual(User.objects.count(), 1)

    def test_correct_code_is_one_time_only(self):
        request = self.request_code()
        self.assertEqual(self.verify_code(request.data['request_id']).status_code, 200)
        self.assertEqual(self.verify_code(request.data['request_id']).status_code, 400)

    def test_expired_and_undelivered_codes_are_rejected(self):
        response = self.request_code()
        challenge = EmailOtpChallenge.objects.get(pk=response.data['request_id'])
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save()
        self.assertEqual(self.verify_code(challenge.pk).status_code, 400)
        challenge.expires_at = timezone.now() + timedelta(minutes=5)
        challenge.delivered_at = None
        challenge.save()
        self.assertEqual(self.verify_code(challenge.pk).status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_five_wrong_attempts_disable_even_the_correct_code(self):
        request = self.request_code()
        for _ in range(5):
            self.assertEqual(self.verify_code(request.data['request_id'], '000000').status_code, 400)
        challenge = EmailOtpChallenge.objects.get(pk=request.data['request_id'])
        self.assertEqual(challenge.attempts, 5)
        self.assertIsNotNone(challenge.consumed_at)
        self.assertEqual(self.verify_code(challenge.pk).status_code, 400)

    def test_resend_cooldown_and_invalidation(self):
        old = self.request_code()
        blocked = self.request_code()
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)
        AuthRateLimit.objects.all().update(next_allowed_at=timezone.now() - timedelta(seconds=1))
        new = self.request_code()
        self.assertEqual(new.status_code, 202)
        self.assertEqual(self.verify_code(old.data['request_id']).status_code, 400)
        self.assertEqual(self.verify_code(new.data['request_id']).status_code, 200)

    @override_settings(EMAIL_OTP_ADDRESS_HOURLY_LIMIT=1)
    def test_address_hourly_limit(self):
        self.assertEqual(self.request_code().status_code, 202)
        AuthRateLimit.objects.all().update(next_allowed_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.request_code().status_code, 429)

    @override_settings(EMAIL_OTP_IP_HOURLY_LIMIT=1)
    def test_ip_hourly_limit(self):
        self.assertEqual(self.request_code().status_code, 202)
        self.assertEqual(self.request_code('another@example.com').status_code, 429)

    @override_settings(PATIENT_AUTH_VERIFY_HOURLY_LIMIT=1)
    def test_verification_ip_limit(self):
        request = self.request_code()
        self.assertEqual(self.verify_code(request.data['request_id'], '000000').status_code, 400)
        self.assertEqual(self.verify_code(request.data['request_id']).status_code, 429)

    def test_email_delivery_failure_is_explicit_and_code_unusable(self):
        self.mail.side_effect = SMTPException('Delivery failed')
        response = self.request_code()
        self.assertEqual(response.status_code, 503)
        challenge = EmailOtpChallenge.objects.get()
        self.assertIsNotNone(challenge.consumed_at)
        self.assertIsNone(challenge.delivered_at)
        self.assertEqual(self.verify_code(challenge.pk).status_code, 400)

    @override_settings(EMAIL_HOST_PASSWORD='')
    def test_missing_smtp_credentials_do_not_claim_success(self):
        self.assertEqual(self.request_code().status_code, 503)
        self.mail.assert_not_called()
        self.assertFalse(EmailOtpChallenge.objects.exists())

    def test_unconfirmed_smtp_delivery_does_not_claim_success(self):
        self.mail.return_value = 0
        self.assertEqual(self.request_code().status_code, 503)

    def test_invalid_inputs_and_unverified_flags_cannot_sign_in(self):
        for data in [{'email': 'bad'}, {}]:
            self.assertEqual(self.client.post(self.endpoint('email-request'), data).status_code, 400)
        self.assertEqual(self.client.post(self.endpoint('phone'), {'phone_number': '+919812345678', 'verified': True}).status_code, 400)
        self.assertEqual(self.client.post(self.endpoint('email-verify'), {'email': 'patient@example.com', 'verified': True}).status_code, 400)

    def test_phone_registers_and_signs_in_same_patient(self):
        response = self.phone()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['is_new_user'])
        self.assertEqual(response.data['user']['phone_number'], '+919812345678')
        self.assertTrue(response.data['user']['is_phone_verified'])
        again = self.phone(token='another-fresh-token')
        self.assertEqual(again.status_code, 200)
        self.assertFalse(again.data['is_new_user'])
        self.assertEqual(again.data['user']['id'], response.data['user']['id'])

    def test_same_firebase_token_is_not_exchanged_twice(self):
        self.assertEqual(self.phone().status_code, 200)
        self.assertEqual(self.phone().status_code, 401)
        self.assertEqual(UsedFirebaseToken.objects.count(), 1)

    def test_invalid_firebase_e164_number_is_rejected(self):
        response = self.phone(claims=self.phone_claims(phone_number='9812345678'))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(User.objects.exists())

    def test_phone_number_or_firebase_uid_change_needs_recovery(self):
        self.assertEqual(self.phone().status_code, 200)
        changed_uid = self.phone('second', self.phone_claims(uid='different-user'))
        self.assertEqual(changed_uid.status_code, 400)
        changed_phone = self.phone('third', self.phone_claims(phone_number='+919812345679'))
        self.assertEqual(changed_phone.status_code, 400)
        self.assertEqual(VerifiedIdentity.objects.count(), 1)

    def test_phone_verifier_uses_sdk_revocation_check_and_rejects_bad_claims(self):
        with patch('apps.accounts.firebase.firebase_app', return_value='firebase-app'):
            with patch('apps.accounts.firebase.auth.verify_id_token', return_value=self.phone_claims()) as verify:
                self.assertEqual(verify_phone_token('jwt')['uid'], 'firebase-patient-1')
                verify.assert_called_once_with('jwt', app='firebase-app', check_revoked=True)
            for claims in [
                self.phone_claims(firebase={'sign_in_provider': 'password'}),
                self.phone_claims(firebase={'sign_in_provider': 'phone', 'tenant': 'other'}),
                self.phone_claims(auth_time=int(time.time()) - 301),
                self.phone_claims(auth_time=int(time.time()) + 100),
                self.phone_claims(auth_time='not-a-date'),
                self.phone_claims(exp=0),
                self.phone_claims(uid=''),
            ]:
                with self.subTest(claims=claims), patch('apps.accounts.firebase.auth.verify_id_token', return_value=claims):
                    with self.assertRaises(AuthenticationFailed) as context:
                        verify_phone_token('jwt')
                    self.assertEqual(context.exception.status_code, 401)

    def test_invalid_or_revoked_firebase_token_is_rejected(self):
        with patch('apps.accounts.firebase.firebase_app', return_value='app'):
            for error in [auth.InvalidIdTokenError('bad'), auth.RevokedIdTokenError('revoked'), auth.UserDisabledError('disabled')]:
                with self.subTest(error=error), patch('apps.accounts.firebase.auth.verify_id_token', side_effect=error):
                    response = self.client.post(self.endpoint('phone'), {'id_token': 'bad'})
                    self.assertEqual(response.status_code, 401)
                    self.assertFalse(User.objects.exists())

    def test_firebase_outage_returns_explicit_unavailable_response(self):
        with patch('apps.accounts.firebase.firebase_app', return_value='app'):
            with patch('apps.accounts.firebase.auth.verify_id_token', side_effect=UnavailableError('Unavailable')):
                response = self.client.post(self.endpoint('phone'), {'id_token': 'token'})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.exists())

    @override_settings(FIREBASE_PROJECT_ID='')
    def test_missing_firebase_configuration_is_explicit(self):
        self.assertEqual(self.client.post(self.endpoint('phone'), {'id_token': 'token'}).status_code, 503)

    def test_link_phone_to_email_patient_and_login_with_either(self):
        signed_in = self.email_login()
        user = User.objects.get(pk=signed_in.data['user']['id'])
        self.authenticate(user)
        linked = self.phone(link=True)
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertFalse(linked.data['is_new_user'])
        self.assertEqual(linked.data['user']['id'], user.pk)
        self.assertEqual(user.verified_identities.count(), 2)
        self.client.credentials()
        logged_in = self.phone('new-phone-token')
        self.assertEqual(logged_in.data['user']['id'], user.pk)

    def test_link_email_to_phone_patient_requires_same_signed_in_owner(self):
        response = self.phone()
        user = User.objects.get(pk=response.data['user']['id'])
        self.authenticate(user)
        requested = self.request_code(link=True)
        request_id = requested.data['request_id']
        self.client.credentials()
        self.assertEqual(self.verify_code(request_id).status_code, 400)
        self.assertEqual(self.verify_code(request_id, link=True).status_code, 401)
        other = User.objects.create_user('other-patient')
        self.authenticate(other)
        self.assertEqual(self.verify_code(request_id, link=True).status_code, 400)
        self.authenticate(user)
        linked = self.verify_code(request_id, link=True)
        self.assertEqual(linked.status_code, 200)
        self.assertEqual(linked.data['user']['id'], user.pk)

    def test_link_endpoints_require_authentication(self):
        self.assertEqual(self.request_code(link=True).status_code, 401)
        self.assertEqual(self.phone(link=True).status_code, 401)

    def test_cannot_merge_two_existing_accounts_or_replace_verified_contact(self):
        email = self.email_login()
        phone = self.phone()
        user = User.objects.get(pk=email.data['user']['id'])
        self.authenticate(user)
        self.assertEqual(self.phone('link-conflict', link=True).status_code, 400)
        self.assertNotEqual(email.data['user']['id'], phone.data['user']['id'])
        AuthRateLimit.objects.all().delete()
        requested = self.request_code('second@example.com', link=True)
        self.assertEqual(self.verify_code(requested.data['request_id'], link=True).status_code, 400)
        self.assertEqual(user.verified_identities.count(), 1)

    def test_unverified_legacy_contact_does_not_auto_merge_or_duplicate(self):
        legacy = User.objects.create_user('legacy', email='patient@example.com')
        requested = self.request_code()
        self.assertEqual(self.verify_code(requested.data['request_id']).status_code, 400)
        self.assertEqual(User.objects.count(), 1)
        AuthRateLimit.objects.all().delete()
        self.authenticate(legacy)
        requested = self.request_code(link=True)
        self.assertEqual(self.verify_code(requested.data['request_id'], link=True).status_code, 200)

    def test_staff_doctor_and_inactive_accounts_cannot_use_patient_login(self):
        for flags in [{'is_staff': True}, {'role': 'doctor'}, {'is_active': False}]:
            with self.subTest(flags=flags):
                User.objects.all().delete()
                AuthRateLimit.objects.all().delete()
                user = User.objects.create_user('restricted', **flags)
                VerifiedIdentity.objects.create(user=user, kind='email', value='patient@example.com')
                requested = self.request_code()
                self.assertEqual(self.verify_code(requested.data['request_id']).status_code, 403)

    def test_profile_only_edits_safe_fields(self):
        signed_in = self.email_login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {signed_in.data["access"]}')
        response = self.client.patch(self.endpoint('me'), {
            'first_name': 'Test', 'city': 'Delhi', 'role': 'admin',
            'email': 'unverified@example.com', 'is_phone_verified': True,
        })
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(self.endpoint('me'), {'first_name': 'Test', 'city': 'Delhi'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['role'], 'patient')
        self.assertEqual(response.data['email'], 'patient@example.com')
        self.assertFalse(response.data['is_phone_verified'])
        self.assertEqual(self.client.get(self.endpoint('me'))['Cache-Control'], 'no-store')

    def test_refresh_rotation_logout_and_cross_account_protection(self):
        signed_in = self.email_login()
        refreshed = self.client.post(self.endpoint('refresh'), {'refresh': signed_in.data['refresh']})
        self.assertEqual(refreshed.status_code, 200, refreshed.data)
        self.assertEqual(self.client.post(self.endpoint('refresh'), {'refresh': signed_in.data['refresh']}).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refreshed.data["access"]}')
        other = User.objects.create_user('other')
        other_refresh = patient_tokens(other)['refresh']
        self.assertEqual(self.client.post(self.endpoint('logout'), {'refresh': other_refresh}).status_code, 401)
        self.assertEqual(self.client.post(self.endpoint('logout'), {'refresh': refreshed.data['refresh']}).status_code, 204)
        self.assertEqual(self.client.post(self.endpoint('refresh'), {'refresh': refreshed.data['refresh']}).status_code, 401)

    def test_patient_refresh_rejects_deleted_or_non_patient_account_and_legacy_token(self):
        user = User.objects.create_user('patient')
        legacy = str(RefreshToken.for_user(user))
        self.assertEqual(self.client.post(self.endpoint('refresh'), {'refresh': legacy}).status_code, 401)
        token = patient_tokens(user)['refresh']
        user.role = 'doctor'
        user.save()
        self.assertEqual(self.client.post(self.endpoint('refresh'), {'refresh': token}).status_code, 403)
        user.delete()
        self.assertEqual(self.client.post(self.endpoint('refresh'), {'refresh': token}).status_code, 401)

    def test_existing_username_password_endpoint_still_works(self):
        User.objects.create_user('legacy-patient', password='test-password')
        response = self.client.post(reverse('accounts:token-obtain'), {'username': 'legacy-patient', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    @override_settings(EMAIL_OTP_IP_HOURLY_LIMIT=1, PATIENT_AUTH_TRUST_PROXY_HEADERS=False)
    def test_untrusted_forwarded_addresses_cannot_bypass_limits(self):
        self.assertEqual(self.request_code().status_code, 202)
        response = self.client.post(self.endpoint('email-request'), {'email': 'another@example.com'}, HTTP_X_REAL_IP='192.0.2.4')
        self.assertEqual(response.status_code, 429)

    @override_settings(EMAIL_OTP_IP_HOURLY_LIMIT=1, PATIENT_AUTH_TRUST_PROXY_HEADERS=True)
    def test_explicitly_trusted_proxy_addresses_separate_clients(self):
        first = self.client.post(self.endpoint('email-request'), {'email': 'one@example.com'}, HTTP_X_REAL_IP='192.0.2.4')
        second = self.client.post(self.endpoint('email-request'), {'email': 'two@example.com'}, HTTP_X_REAL_IP='192.0.2.5')
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)

    def test_link_conflict_rolls_back_firebase_token_and_account_changes(self):
        first = self.email_login()
        self.phone()
        self.authenticate(User.objects.get(pk=first.data['user']['id']))
        before = UsedFirebaseToken.objects.count()
        self.assertEqual(self.phone('conflict-proof', link=True).status_code, 400)
        self.assertEqual(UsedFirebaseToken.objects.count(), before)
        self.assertEqual(User.objects.count(), 2)

    def test_cleanup_removes_only_expired_authentication_records(self):
        from io import StringIO
        now = timezone.now()
        old = EmailOtpChallenge.objects.create(
            email='old@example.com', code_digest='digest', expires_at=now - timedelta(days=2),
        )
        active = EmailOtpChallenge.objects.create(
            email='active@example.com', code_digest='digest', expires_at=now + timedelta(minutes=5),
        )
        UsedFirebaseToken.objects.create(digest='expired', expires_at=now - timedelta(seconds=1))
        UsedFirebaseToken.objects.create(digest='active', expires_at=now + timedelta(hours=1))
        call_command('cleanup_patient_auth', stdout=StringIO())
        self.assertFalse(EmailOtpChallenge.objects.filter(pk=old.pk).exists())
        self.assertTrue(EmailOtpChallenge.objects.filter(pk=active.pk).exists())
        self.assertFalse(UsedFirebaseToken.objects.filter(pk='expired').exists())
        self.assertTrue(UsedFirebaseToken.objects.filter(pk='active').exists())
