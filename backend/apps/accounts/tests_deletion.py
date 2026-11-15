import time
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.appointments.models import Appointment, AppointmentCall, AppointmentSlot
from apps.consultations.models import Consultation
from apps.doctors.models import DoctorApplication, DoctorProfile
from apps.notifications.models import DeviceToken
from apps.payments.gateway import record_capture
from apps.payments.models import Payment
from .models import EmailOtpChallenge, User, VerifiedIdentity
from .services import doctor_tokens, otp_digest, patient_tokens


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AccountDeletionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = self.user('patient')
        self.doctor = self.user('doctor')
        self.profile = DoctorProfile.objects.create(
            user=self.doctor, verification_status='verified', registration_number='REG-DELETE',
            qualification='MBBS',
        )
        self.consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.doctor, status='requested', history_completed=True,
            patient_name='Historical Patient', patient_phone=self.patient.phone_number, fee_charged=200,
        )
        self.appointment = Appointment.objects.create(
            consultation=self.consultation, patient=self.patient, doctor=self.doctor,
            status='confirmed', slot_time=timezone.now() + timedelta(days=1),
        )
        self.payment = Payment.objects.create(
            user=self.patient, consultation=self.consultation, amount=200, status='success',
            gateway_order_id='order_retained', transaction_id='pay_retained',
        )

    def user(self, role):
        user = User.objects.create_user(
            username=role, password='test-password', role=role, phone_number='+919000000001',
            first_name=f'Historical {role}', is_phone_verified=True,
        )
        VerifiedIdentity.objects.create(
            user=user, role=role, kind='phone', value=user.phone_number, firebase_uid=f'firebase-{role}',
        )
        return user

    def tokens(self, user):
        return doctor_tokens(user) if user.role == 'doctor' else patient_tokens(user)

    def authenticate(self, user):
        tokens = self.tokens(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        return tokens

    def delete(self, role, data=None):
        return self.client.delete(f'/api/v1/auth/{role}/account/', {'confirm': True} if data is None else data, format='json')

    def phone(self, role, token, authenticated_at):
        claims = {
            'uid': f'firebase-{role}', 'phone_number': '+919000000001',
            'auth_time': authenticated_at, 'exp': int(time.time()) + 3600,
        }
        module = 'doctor_views' if role == 'doctor' else 'views'
        with patch(f'apps.accounts.{module}.verify_phone_token', return_value=claims):
            return self.client.post(f'/api/v1/auth/{role}/phone/firebase/', {'id_token': token}, format='json')

    def test_patient_closure_preserves_records_revokes_all_tokens_and_flags_staff(self):
        first = self.authenticate(self.patient)
        self.tokens(self.patient)
        DeviceToken.objects.create(user=self.patient, token='old-device', platform='android')
        call = AppointmentCall.objects.create(appointment=self.appointment, status='completed', duration_seconds=45)
        payment_snapshot = Payment.objects.values().get(pk=self.payment.pk)
        consultation_snapshot = Consultation.objects.values().get(pk=self.consultation.pk)
        appointment_snapshot = Appointment.objects.values().get(pk=self.appointment.pk)
        response = self.delete('patient')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertTrue(response.data['records_retained'])
        self.assertEqual(response.data['unfinished_appointments'], 1)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_active)
        self.assertFalse(self.patient.has_usable_password())
        self.assertIsNotNone(self.patient.deleted_at)
        self.assertFalse(self.patient.is_phone_verified)
        self.assertTrue(VerifiedIdentity.objects.get(user=self.patient).retired_at)
        self.assertEqual(Payment.objects.values().get(pk=self.payment.pk), payment_snapshot)
        self.assertEqual(Consultation.objects.values().get(pk=self.consultation.pk), consultation_snapshot)
        self.assertEqual(Appointment.objects.values().get(pk=self.appointment.pk), appointment_snapshot)
        self.assertTrue(AppointmentCall.objects.filter(pk=call.pk).exists())
        self.assertFalse(DeviceToken.objects.filter(user=self.patient).exists())
        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.patient).count(),
            OutstandingToken.objects.filter(user=self.patient).count(),
        )
        self.assertEqual(self.client.get('/api/v1/auth/patient/me/').status_code, 401)
        self.assertEqual(self.delete('patient').status_code, 401)
        self.client.credentials()
        for endpoint in ('patient/token/refresh/', 'token/refresh/'):
            response = self.client.post(f'/api/v1/auth/{endpoint}', {'refresh': first['refresh']}, format='json')
            self.assertEqual(response.status_code, 401, response.data)
        self.assertEqual(self.client.post('/api/v1/auth/token/', {'username': 'patient', 'password': 'test-password'}, format='json').status_code, 401)
        staff = User.objects.create_user(username='staff', is_staff=True)
        self.client.force_authenticate(staff)
        detail = self.client.get(f'/api/v1/staff/appointments/{self.appointment.pk}/')
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertTrue(detail.data['booker_account_deleted'])
        self.assertFalse(detail.data['can_assign'])
        assigned = self.client.post(f'/api/v1/appointments/{self.appointment.pk}/assign-doctor/', {'doctor_id': self.doctor.pk}, format='json')
        self.assertEqual(assigned.status_code, 400)

    def test_fresh_phone_registration_is_separate_and_old_session_cannot_reregister(self):
        before = int(time.time())
        self.authenticate(self.patient)
        self.assertEqual(self.delete('patient').status_code, 200)
        self.patient.refresh_from_db()
        self.client.credentials()
        old = self.phone('patient', 'different-refreshed-token-from-old-session', before)
        self.assertEqual(old.status_code, 401, old.data)
        new = self.phone('patient', 'fresh-post-deletion-token', int(self.patient.deleted_at.timestamp()) + 1)
        self.assertEqual(new.status_code, 200, new.data)
        self.assertTrue(new.data['is_new_user'])
        self.assertNotEqual(new.data['user']['id'], self.patient.pk)
        self.assertEqual(new.data['user']['first_name'], '')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new.data["access"]}')
        self.assertEqual(self.client.get('/api/v1/appointments/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/v1/consultations/{self.consultation.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/payments/{self.payment.pk}/').status_code, 404)
        self.doctor.refresh_from_db()
        self.assertTrue(self.doctor.is_active)
        self.assertIsNone(VerifiedIdentity.objects.get(user=self.doctor).retired_at)

    def challenge(self, email, *, link_user=None):
        challenge = EmailOtpChallenge.objects.create(
            email=email, link_user=link_user, expires_at=timezone.now() + timedelta(minutes=5),
            delivered_at=timezone.now(),
        )
        challenge.code_digest = otp_digest(challenge.pk, '123456')
        challenge.save(update_fields=['code_digest'])
        return challenge

    def test_email_requires_new_challenge_after_closure_and_links_are_invalidated(self):
        self.patient.email = 'patient@example.com'
        self.patient.is_email_verified = True
        self.patient.save()
        VerifiedIdentity.objects.create(user=self.patient, role='patient', kind='email', value=self.patient.email)
        old = self.challenge(self.patient.email)
        linked = self.challenge('other@example.com', link_user=self.patient)
        self.authenticate(self.patient)
        self.assertEqual(self.delete('patient').status_code, 200)
        self.client.credentials()
        for challenge in (old, linked):
            challenge.refresh_from_db()
            self.assertIsNotNone(challenge.consumed_at)
        verify = lambda item: self.client.post('/api/v1/auth/patient/email/verify-otp/', {
            'request_id': str(item.pk), 'otp': '123456',
        }, format='json')
        self.assertEqual(verify(old).status_code, 400)
        with patch('apps.accounts.views.consume_email_otp', return_value=(self.patient.email, old.created_at)):
            self.assertEqual(verify(old).status_code, 401)
        fresh = self.challenge(self.patient.email)
        new = verify(fresh)
        self.assertEqual(new.status_code, 200, new.data)
        self.assertTrue(new.data['is_new_user'])
        self.assertNotEqual(new.data['user']['id'], self.patient.pk)

    def test_doctor_closure_preserves_attribution_and_requires_new_onboarding(self):
        application = DoctorApplication.objects.create(
            full_name='Historical doctor', phone_number=self.doctor.phone_number, qualification='MBBS', status='approved',
        )
        self.profile.application = application
        self.profile.save(update_fields=['application'])
        slot = AppointmentSlot.objects.create(doctor=self.doctor, starts_at=self.appointment.slot_time)
        tokens = self.authenticate(self.doctor)
        response = self.delete('doctor')
        self.assertEqual(response.status_code, 200, response.data)
        self.profile.refresh_from_db()
        slot.refresh_from_db()
        self.assertFalse(self.profile.is_active)
        self.assertIsNotNone(self.profile.account_deleted_at)
        self.assertFalse(slot.is_active)
        self.assertEqual(self.profile.registration_number, 'REG-DELETE')
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.doctor_id, self.appointment.status), (self.doctor.pk, 'confirmed'))
        self.assertEqual(self.client.get('/api/v1/doctors/me/').status_code, 401)
        self.client.credentials()
        featured = self.client.get('/api/v1/doctors/featured/')
        self.assertEqual(featured.status_code, 200, featured.data)
        self.assertNotIn(application.pk, [item['id'] for item in featured.data])
        self.assertEqual(self.client.post('/api/v1/auth/doctor/token/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)
        self.doctor.refresh_from_db()
        new = self.phone('doctor', 'fresh-doctor-token', int(self.doctor.deleted_at.timestamp()) + 1)
        self.assertEqual(new.status_code, 200, new.data)
        self.assertTrue(new.data['is_new_user'])
        self.assertFalse(new.data['doctor']['is_verified'])
        self.assertEqual(new.data['doctor']['onboarding']['next_step'], 'profile')
        new_profile = DoctorProfile.objects.get(user_id=new.data['doctor']['id'])
        self.assertIsNone(new_profile.application_id)
        self.assertIsNone(new_profile.registration_number)
        self.assertFalse(new_profile.documents.exists())
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new.data["access"]}')
        update = self.client.patch('/api/v1/doctors/me/', {'registration_number': 'REG-DELETE'}, format='json')
        self.assertEqual(update.status_code, 200, update.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.registration_number, 'REG-DELETE')
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_active)

    def test_requires_authentication_correct_role_confirmation_and_no_target_user_id(self):
        self.assertEqual(self.delete('patient').status_code, 401)
        self.authenticate(self.patient)
        self.assertEqual(self.delete('doctor').status_code, 403)
        for payload in ({}, {'confirm': False}, {'confirm': True, 'user_id': self.doctor.pk}):
            response = self.delete('patient', payload)
            self.assertEqual(response.status_code, 400, response.data)
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_active)
        staff = User.objects.create_user(username='staff', role='patient', is_staff=True)
        self.client.force_authenticate(staff)
        self.assertEqual(self.delete('patient').status_code, 403)

    def test_late_payment_capture_still_records_money_after_account_closure(self):
        self.payment.status = 'pending'
        self.payment.transaction_id = None
        self.payment.save()
        self.appointment.status = 'awaiting_payment'
        self.appointment.save()
        self.authenticate(self.patient)
        self.assertEqual(self.delete('patient').status_code, 200)
        payment = record_capture(self.payment.pk, {
            'id': 'pay_late_capture', 'order_id': self.payment.gateway_order_id,
            'amount': 20000, 'currency': 'INR', 'status': 'captured', 'method': 'upi',
        })
        self.assertEqual(payment.status, 'success')
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'finding_doctor')
        self.assertEqual(self.appointment.patient_id, self.patient.pk)

    def test_ordinary_admin_deactivation_does_not_release_identity(self):
        self.patient.is_active = False
        self.patient.save(update_fields=['is_active'])
        response = self.phone('patient', 'token-for-admin-disabled-account', int(time.time()))
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIsNone(VerifiedIdentity.objects.get(user=self.patient).retired_at)
