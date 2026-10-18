import hashlib
import hmac
import json
import tempfile
from datetime import timedelta
from unittest.mock import patch

import razorpay
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment, AppointmentSlot
from apps.doctors.models import DoctorProfile
from apps.payments.models import Payment
from .models import Consultation, ConsultationDocument


@override_settings(
	RAZORPAY_KEY_ID='test_key', RAZORPAY_KEY_SECRET='test_secret', RAZORPAY_WEBHOOK_SECRET='webhook_secret',
	PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class MobileConsultationFlowTests(APITestCase):
	def setUp(self):
		self.owner = get_user_model().objects.create_user(username='patient', password='test-password')
		self.other = get_user_model().objects.create_user(username='other', password='test-password')
		self.client.force_authenticate(self.owner)
		self.patient_details = {
			'patient_name': 'Family Member', 'patient_age': 55,
			'patient_gender': 'female', 'patient_phone': '9876543210', 'mode': 'audio',
		}
		self.history = {'duration_value': 5, 'duration_unit': 'days', 'ongoing_medication': False}
		starts_at = (timezone.localtime() + timedelta(days=2)).replace(hour=13, minute=0, second=0, microsecond=0)
		self.slot = AppointmentSlot.objects.create(starts_at=starts_at)
		self.storage_directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.storage_directory.cleanup)
		storage_patch = patch.object(
			ConsultationDocument._meta.get_field('file'), 'storage',
			FileSystemStorage(location=self.storage_directory.name),
		)
		storage_patch.start()
		self.addCleanup(storage_patch.stop)
		self.gateway = razorpay.Client(auth=('test_key', 'test_secret'))
		gateway_patch = patch('apps.payments.views.gateway_client', return_value=self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)

	def create_draft(self):
		response = self.client.post('/api/v1/consultations/', self.patient_details)
		self.assertEqual(response.status_code, 201, response.data)
		consultation_id = response.data['id']
		response = self.client.put(f'/api/v1/consultations/{consultation_id}/history/', self.history, format='json')
		self.assertEqual(response.status_code, 200, response.data)
		return consultation_id

	def book(self):
		consultation_id = self.create_draft()
		response = self.client.post('/api/v1/appointments/', {'consultation_id': consultation_id, 'slot_id': self.slot.pk, 'information_confirmed': True}, format='json')
		self.assertEqual(response.status_code, 201, response.data)
		return response.data

	def order(self):
		appointment = self.book()
		with patch.object(self.gateway.order, 'create', return_value={'id': 'order_test'}) as create:
			response = self.client.post('/api/v1/payments/orders/', {'appointment_id': appointment['id'], 'method': 'upi', 'amount': 1}, format='json')
			self.assertEqual(response.status_code, 200, response.data)
			self.assertEqual(create.call_args.args[0]['amount'], 20000)
		return appointment, response.data

	def captured_entity(self):
		return {'id': 'pay_test', 'order_id': 'order_test', 'amount': 20000, 'currency': 'INR', 'status': 'captured', 'method': 'upi'}

	def test_authenticated_patient_details_are_required(self):
		self.client.force_authenticate(None)
		response = self.client.post('/api/v1/consultations/', self.patient_details)
		self.assertEqual(response.status_code, 401)

	def test_patient_validation(self):
		invalid = {**self.patient_details, 'patient_age': -1, 'patient_phone': 'invalid'}
		self.assertEqual(self.client.post('/api/v1/consultations/', invalid).status_code, 400)

	def test_history_validation(self):
		consultation_id = self.create_draft()
		response = self.client.put(f'/api/v1/consultations/{consultation_id}/history/', {**self.history, 'duration_unit': 'centuries'}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_booking_without_documents_and_duplicate_booking(self):
		appointment = self.book()
		self.assertEqual(appointment['amount'], 200)
		self.assertEqual(appointment['currency'], 'INR')
		self.assertEqual(appointment['status'], 'awaiting_payment')
		self.assertIsNone(appointment['doctor'])
		repeated = self.client.post('/api/v1/appointments/', {'consultation_id': appointment['consultation'], 'slot_id': self.slot.pk, 'information_confirmed': True}, format='json')
		self.assertEqual(repeated.status_code, 200)
		self.assertEqual(repeated.data['id'], appointment['id'])
		self.assertEqual(Appointment.objects.count(), 1)

	def test_draft_requires_history_before_booking(self):
		draft = self.client.post('/api/v1/consultations/', self.patient_details).data
		response = self.client.post('/api/v1/appointments/', {'consultation_id': draft['id'], 'slot_id': self.slot.pk, 'information_confirmed': True}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_full_slot_is_hidden_and_rejected(self):
		self.book()
		response = self.client.get('/api/v1/appointments/slots/', {'date': timezone.localdate(self.slot.starts_at).isoformat()})
		self.assertEqual(response.data, [])
		self.client.force_authenticate(self.other)
		consultation_id = self.create_draft()
		response = self.client.post('/api/v1/appointments/', {'consultation_id': consultation_id, 'slot_id': self.slot.pk, 'information_confirmed': True}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_past_slot_rejected(self):
		self.slot.starts_at = timezone.now() - timedelta(hours=1)
		self.slot.save()
		consultation_id = self.create_draft()
		response = self.client.post('/api/v1/appointments/', {'consultation_id': consultation_id, 'slot_id': self.slot.pk, 'information_confirmed': True}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_cross_account_access_is_hidden(self):
		appointment = self.book()
		self.client.force_authenticate(self.other)
		self.assertEqual(self.client.get(f'/api/v1/consultations/{appointment["consultation"]}/').status_code, 404)
		self.assertEqual(self.client.get(f'/api/v1/appointments/{appointment["id"]}/').status_code, 404)

	def test_booked_intake_is_read_only(self):
		appointment = self.book()
		response = self.client.patch(f'/api/v1/consultations/{appointment["consultation"]}/', {'patient_name': 'Changed'}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_upload_download_delete_are_private(self):
		consultation_id = self.create_draft()
		pdf = SimpleUploadedFile('report.pdf', b'%PDF-1.4\nexample', content_type='application/pdf')
		response = self.client.post(f'/api/v1/consultations/{consultation_id}/documents/', {'file': pdf}, format='multipart')
		self.assertEqual(response.status_code, 201, response.data)
		document_id = response.data['id']
		self.assertNotIn('file', response.data)
		url = f'/api/v1/consultations/{consultation_id}/documents/{document_id}/download/'
		self.client.force_authenticate(self.other)
		self.assertEqual(self.client.get(url).status_code, 404)
		self.client.force_authenticate(self.owner)
		download = self.client.get(url)
		self.assertEqual(download.status_code, 200)
		download.close()
		self.assertEqual(self.client.delete(f'/api/v1/consultations/{consultation_id}/documents/{document_id}/').status_code, 204)

	def test_invalid_file_type_and_oversize_are_rejected(self):
		consultation_id = self.create_draft()
		for file in [
			SimpleUploadedFile('fake.pdf', b'<script>not a PDF</script>'),
			SimpleUploadedFile('big.pdf', b'%PDF-' + b'0' * (10 * 1024 * 1024)),
		]:
			response = self.client.post(f'/api/v1/consultations/{consultation_id}/documents/', {'file': file}, format='multipart')
			self.assertEqual(response.status_code, 400)
		self.assertEqual(ConsultationDocument.objects.count(), 0)

	def test_checkout_order_uses_server_amount_and_is_reused(self):
		appointment, order = self.order()
		self.assertEqual(order['amount'], 20000)
		with patch.object(self.gateway.order, 'create') as create:
			response = self.client.post('/api/v1/payments/orders/', {'appointment_id': appointment['id'], 'method': 'card'}, format='json')
			self.assertEqual(response.data['gateway_order_id'], 'order_test')
			create.assert_not_called()

	def test_capture_verification_and_replay(self):
		appointment, order = self.order()
		signature = hmac.new(b'test_secret', b'order_test|pay_test', hashlib.sha256).hexdigest()
		payload = {'payment_id': order['payment_id'], 'razorpay_payment_id': 'pay_test', 'razorpay_signature': signature}
		with patch.object(self.gateway.payment, 'fetch', return_value=self.captured_entity()):
			for attempt in range(2):
				response = self.client.post('/api/v1/payments/verify/', payload, format='json')
				self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(Payment.objects.get(pk=order['payment_id']).status, 'success')
		self.assertEqual(Appointment.objects.get(pk=appointment['id']).status, 'finding_doctor')

	def test_invalid_signature_is_rejected_before_gateway_fetch(self):
		_, order = self.order()
		with patch.object(self.gateway.payment, 'fetch') as fetch:
			response = self.client.post('/api/v1/payments/verify/', {'payment_id': order['payment_id'], 'razorpay_payment_id': 'pay_test', 'razorpay_signature': '0' * 64}, format='json')
			self.assertEqual(response.status_code, 400)
			fetch.assert_not_called()

	def test_authorized_or_wrong_amount_is_not_paid(self):
		_, order = self.order()
		signature = hmac.new(b'test_secret', b'order_test|pay_test', hashlib.sha256).hexdigest()
		for entity in [{**self.captured_entity(), 'status': 'authorized'}, {**self.captured_entity(), 'amount': 1}]:
			with patch.object(self.gateway.payment, 'fetch', return_value=entity):
				response = self.client.post('/api/v1/payments/verify/', {'payment_id': order['payment_id'], 'razorpay_payment_id': 'pay_test', 'razorpay_signature': signature}, format='json')
				self.assertEqual(response.status_code, 400)
		self.assertEqual(Payment.objects.get(pk=order['payment_id']).status, 'pending')

	def test_signed_webhook_is_idempotent(self):
		appointment, order = self.order()
		body = json.dumps({'event': 'payment.captured', 'payload': {'payment': {'entity': self.captured_entity()}}})
		signature = hmac.new(b'webhook_secret', body.encode(), hashlib.sha256).hexdigest()
		self.client.force_authenticate(None)
		for attempt in range(2):
			response = self.client.post('/api/v1/payments/webhooks/razorpay/', body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=signature)
			self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(Appointment.objects.get(pk=appointment['id']).status, 'finding_doctor')

	def test_unsigned_webhook_is_rejected(self):
		response = self.client.post('/api/v1/payments/webhooks/razorpay/', '{}', content_type='application/json')
		self.assertEqual(response.status_code, 400)

	def test_unconfigured_gateway_does_not_fake_payment(self):
		appointment = self.book()
		with patch('apps.payments.views.gateway_client') as client:
			from apps.payments.gateway import GatewayUnavailable
			client.side_effect = GatewayUnavailable('Not configured')
			response = self.client.post('/api/v1/payments/orders/', {'appointment_id': appointment['id'], 'method': 'upi'}, format='json')
		self.assertEqual(response.status_code, 503)
		self.assertFalse(Payment.objects.filter(status='success').exists())

	def test_staff_assign_verified_doctor_after_payment(self):
		appointment, _ = self.order()
		from apps.payments.gateway import record_capture
		record_capture(Payment.objects.get(consultation_id=appointment['consultation']).pk, self.captured_entity())
		doctor = get_user_model().objects.create_user(username='doctor', role='doctor')
		DoctorProfile.objects.create(user=doctor, specialization='General', systems_practiced='allopathy', qualification='MBBS', registration_number='TEST-123', consultation_fee=200, verification_status='verified')
		staff = get_user_model().objects.create_user(username='staff', is_staff=True)
		url = f'/api/v1/appointments/{appointment["id"]}/assign-doctor/'
		self.assertEqual(self.client.post(url, {'doctor_id': doctor.pk}).status_code, 403)
		self.client.force_authenticate(staff)
		response = self.client.post(url, {'doctor_id': doctor.pk}, format='json')
		self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(response.data['status'], 'confirmed')

	def test_jwt_login_and_swagger(self):
		self.client.force_authenticate(None)
		token = self.client.post('/api/v1/auth/token/', {'username': 'patient', 'password': 'test-password'})
		self.assertEqual(token.status_code, 200)
		self.assertIn('access', token.data)
		self.assertEqual(self.client.get('/api/v1/docs/').status_code, 200)
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.data["access"]}')
		self.assertEqual(self.client.post('/api/v1/consultations/', self.patient_details).status_code, 201)

	def test_schema_contains_mobile_screen_contracts(self):
		response = self.client.get('/api/v1/schema/?format=json')
		self.assertEqual(response.status_code, 200)
		for path in [
			'/api/v1/consultations/', '/api/v1/consultations/{consultation_id}/history/',
			'/api/v1/consultations/{consultation_id}/documents/', '/api/v1/appointments/slots/',
			'/api/v1/appointments/', '/api/v1/payments/orders/', '/api/v1/payments/verify/',
		]:
			self.assertIn(path, response.data['paths'])
