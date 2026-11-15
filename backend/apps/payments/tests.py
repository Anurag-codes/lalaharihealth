import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

import razorpay
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.doctors.models import Speciality
from apps.pricing.models import CountryPricing
from .models import Payment, Subscription


@override_settings(
	RAZORPAY_KEY_ID='test_key', RAZORPAY_KEY_SECRET='test_secret', RAZORPAY_WEBHOOK_SECRET='webhook_secret',
	PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class SubscriptionTests(APITestCase):
	def setUp(self):
		CountryPricing.objects.filter(country_code='IN').update(subscription_fee=999)
		self.patient = get_user_model().objects.create_user(username='subscriber', password='test-password')
		self.client.force_authenticate(self.patient)
		self.gateway = razorpay.Client(auth=('test_key', 'test_secret'))
		gateway_patch = patch('apps.payments.views.gateway_client', return_value=self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)
		self.starts_at = (timezone.localtime() + timedelta(days=2)).replace(hour=13, minute=0, second=0, microsecond=0)

	def entity(self, order_id='order_sub', payment_id='pay_sub'):
		return {'id': payment_id, 'order_id': order_id, 'amount': 99900, 'currency': 'INR', 'status': 'captured', 'method': 'upi'}

	def order(self, order_id='order_sub'):
		with patch.object(self.gateway.order, 'create', return_value={'id': order_id}) as create:
			response = self.client.post('/api/v1/payments/subscription/orders/', {'method': 'upi'}, format='json')
		self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(create.call_args.args[0]['amount'], 99900)
		return response.data

	def buy(self, order_id='order_sub', payment_id='pay_sub'):
		order = self.order(order_id)
		signature = hmac.new(b'test_secret', f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
		payload = {'subscription_id': order['subscription_id'], 'razorpay_payment_id': payment_id, 'razorpay_signature': signature}
		with patch.object(self.gateway.payment, 'fetch', return_value=self.entity(order_id, payment_id)):
			response = self.client.post('/api/v1/payments/subscription/verify/', payload, format='json')
		self.assertEqual(response.status_code, 200, response.data)
		return response.data

	def draft(self, **changes):
		response = self.client.post('/api/v1/consultations/', {
			'patient_name': 'Rahul', 'patient_age': 30, 'patient_gender': 'male', 'patient_phone': '9876543210', 'mode': 'video',
		})
		self.assertEqual(response.status_code, 201, response.data)
		consultation_id = response.data['id']
		response = self.client.put(f'/api/v1/consultations/{consultation_id}/history/', {
			'duration_value': 2, 'duration_unit': 'days', 'ongoing_medication': False,
		}, format='json')
		self.assertEqual(response.status_code, 200, response.data)
		if changes:
			Consultation.objects.filter(pk=consultation_id).update(**changes)
		return consultation_id

	def book(self, consultation_id):
		response = self.client.post('/api/v1/appointments/', {
			'consultation_id': consultation_id, 'starts_at': self.starts_at.isoformat(), 'information_confirmed': True,
		}, format='json')
		self.assertEqual(response.status_code, 201, response.data)
		return response.data

	def test_plan_hidden_and_not_sold_without_fee(self):
		CountryPricing.objects.filter(country_code='IN').update(subscription_fee=None)
		plan = self.client.get('/api/v1/payments/subscription/').data
		self.assertEqual((plan['available'], plan['amount'], plan['can_purchase']), (False, None, False))
		response = self.client.post('/api/v1/payments/subscription/orders/', {'method': 'upi'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertFalse(Subscription.objects.exists())

	def test_verified_payment_activates_for_a_year_and_blocks_early_rebuy(self):
		subscription = self.buy()
		self.assertEqual(subscription['status'], 'active')
		row = Subscription.objects.get(pk=subscription['id'])
		self.assertEqual(row.ends_at - row.starts_at, timedelta(days=365))
		plan = self.client.get('/api/v1/payments/subscription/').data
		self.assertEqual((plan['is_active'], plan['can_purchase'], plan['amount']), (True, False, 999))
		response = self.client.post('/api/v1/payments/subscription/orders/', {'method': 'upi'}, format='json')
		self.assertEqual(response.status_code, 400)

	def test_renewal_in_last_month_starts_when_current_plan_ends(self):
		first = Subscription.objects.get(pk=self.buy()['id'])
		Subscription.objects.filter(pk=first.pk).update(ends_at=timezone.now() + timedelta(days=10))
		first.refresh_from_db()
		renewal = Subscription.objects.get(pk=self.buy('order_renew', 'pay_renew')['id'])
		self.assertEqual(renewal.starts_at, first.ends_at)
		self.assertEqual(renewal.ends_at, first.ends_at + timedelta(days=365))

	def test_wrong_amount_or_signature_does_not_activate(self):
		order = self.order()
		signature = hmac.new(b'test_secret', b'order_sub|pay_sub', hashlib.sha256).hexdigest()
		with patch.object(self.gateway.payment, 'fetch', return_value={**self.entity(), 'amount': 100}):
			response = self.client.post('/api/v1/payments/subscription/verify/', {
				'subscription_id': order['subscription_id'], 'razorpay_payment_id': 'pay_sub', 'razorpay_signature': signature,
			}, format='json')
		self.assertEqual(response.status_code, 400)
		with patch.object(self.gateway.payment, 'fetch') as fetch:
			response = self.client.post('/api/v1/payments/subscription/verify/', {
				'subscription_id': order['subscription_id'], 'razorpay_payment_id': 'pay_sub', 'razorpay_signature': '0' * 64,
			}, format='json')
			fetch.assert_not_called()
		self.assertEqual(response.status_code, 400)
		self.assertEqual(Subscription.objects.get().status, 'pending')

	def test_signed_webhook_activates_subscription(self):
		order = self.order()
		body = json.dumps({'event': 'payment.captured', 'payload': {'payment': {'entity': self.entity()}}})
		signature = hmac.new(b'webhook_secret', body.encode(), hashlib.sha256).hexdigest()
		self.client.force_authenticate(None)
		for attempt in range(2):
			response = self.client.post(
				'/api/v1/payments/webhooks/razorpay/', body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=signature,
			)
			self.assertEqual(response.data, {'received': True})
		self.assertEqual(Subscription.objects.get(pk=order['subscription_id']).status, 'active')

	def test_subscriber_books_own_general_consultation_free(self):
		self.buy()
		consultation_id = self.draft()
		preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'starts_at': self.starts_at.isoformat()})
		self.assertEqual(preview.data['fee'], 0)
		appointment = self.book(consultation_id)
		self.assertEqual(
			(appointment['amount'], appointment['status'], appointment['payment_required'], appointment['payment_status']),
			(0, 'finding_doctor', False, 'not_required'),
		)
		response = self.client.post('/api/v1/payments/orders/', {'appointment_id': appointment['id'], 'method': 'upi'}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertFalse(Payment.objects.exists())

	def test_family_specialist_and_unsubscribed_bookings_are_paid(self):
		unsubscribed = self.book(self.draft())
		self.assertEqual((unsubscribed['amount'], unsubscribed['status']), (200, 'awaiting_payment'))
		self.buy()
		speciality = Speciality.objects.create(name='Plan test speciality', slug='plan-test', fee=500)
		for changes in [{'patient_relation': 'mother'}, {'speciality': speciality}]:
			appointment = self.book(self.draft(**changes))
			self.assertEqual(appointment['status'], 'awaiting_payment')
			self.assertTrue(appointment['payment_required'])
			self.assertGreater(appointment['amount'], 0)

	def test_doctor_cannot_buy_plan(self):
		self.patient.role = 'doctor'
		self.patient.save(update_fields=['role'])
		self.assertEqual(self.client.get('/api/v1/payments/subscription/').status_code, 403)
