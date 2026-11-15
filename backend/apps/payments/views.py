import json

import razorpay
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.views import IsPatient
from apps.appointments.models import Appointment
from apps.pricing.service import pricing_for, to_minor_units
from .gateway import GatewayUnavailable, gateway_client, record_capture, record_subscription_capture
from .models import Payment, Subscription
from .serializers import (
	CheckoutOrderSerializer, PaymentOrderRequestSerializer, PaymentSerializer,
	PaymentVerificationSerializer, SubscriptionCheckoutOrderSerializer, SubscriptionCountrySerializer,
	SubscriptionOrderRequestSerializer, SubscriptionPlanSerializer, SubscriptionSerializer,
	SubscriptionVerificationSerializer,
)
from .subscriptions import plan_payload, purchase_block_reason

GATEWAY_ERRORS = (razorpay.errors.BadRequestError, razorpay.errors.GatewayError, razorpay.errors.ServerError, requests.RequestException)


class PaymentOrderView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PaymentOrderRequestSerializer

	@extend_schema(tags=['Mobile payments'], summary='Step 5: create/reuse Razorpay checkout order', description='Send only appointment_id and card/upi. Server controls amount and currency. Use the returned key_id, gateway_order_id, amount (smallest unit: paise for INR, cents for USD) and currency with the official Razorpay mobile SDK. The currency follows the booking country (international payments must be enabled in Razorpay). Never send PAN, CVV, card details or UPI credentials to this API. Returns 503 when gateway keys are not configured.', responses={200: CheckoutOrderSerializer})
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		with transaction.atomic():
			appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=data['appointment_id'], patient=request.user)
			if appointment.is_free_consultation:
				raise serializers.ValidationError('Payment is not required for this free consultation.')
			if appointment.status != Appointment.Status.AWAITING_PAYMENT:
				raise serializers.ValidationError('This appointment is not awaiting payment.')
			client = gateway_client()
			payment, _ = Payment.objects.get_or_create(
				consultation=appointment.consultation,
				defaults={
					'user': request.user, 'amount': appointment.consultation.fee_charged,
					'currency': appointment.consultation.currency, 'method': data['method'],
				},
			)
			if payment.status != Payment.Status.PENDING:
				raise serializers.ValidationError('Payment is not pending.')
			if not payment.gateway_order_id:
				try:
					order = client.order.create({
						'amount': to_minor_units(payment.amount, payment.currency), 'currency': payment.currency,
						'receipt': f'payment_{payment.pk}',
					}, timeout=15)
				except GATEWAY_ERRORS as error:
					raise GatewayUnavailable() from error
				payment.gateway_order_id = order['id']
			payment.method = data['method']
			payment.save(update_fields=['gateway_order_id', 'method'])
		return Response({
			'payment_id': payment.pk, 'gateway_order_id': payment.gateway_order_id,
			'key_id': settings.RAZORPAY_KEY_ID, 'amount': to_minor_units(payment.amount, payment.currency),
			'currency': payment.currency, 'status': payment.status,
		})


class PaymentVerifyView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PaymentVerificationSerializer

	@extend_schema(tags=['Mobile payments'], summary='Verify signed checkout result and captured status', description='Call after Razorpay SDK success. Backend verifies the signature using its stored order id, then fetches the payment from Razorpay. An authorized but not captured payment is not considered paid. After success, poll appointment detail: finding_doctor changes to confirmed after staff assign a doctor.', responses=PaymentSerializer)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		payment = get_object_or_404(Payment, pk=data['payment_id'], user=request.user)
		if not payment.gateway_order_id:
			raise serializers.ValidationError('Create a gateway order first.')
		client = gateway_client()
		try:
			client.utility.verify_payment_signature({
				'razorpay_order_id': payment.gateway_order_id,
				'razorpay_payment_id': data['razorpay_payment_id'],
				'razorpay_signature': data['razorpay_signature'],
			})
		except razorpay.errors.SignatureVerificationError as error:
			raise serializers.ValidationError('Invalid payment signature.') from error
		try:
			entity = client.payment.fetch(data['razorpay_payment_id'], timeout=15)
		except GATEWAY_ERRORS as error:
			raise GatewayUnavailable() from error
		payment = record_capture(payment.pk, entity)
		return Response(PaymentSerializer(payment).data)


class PaymentDetailView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PaymentSerializer

	@extend_schema(tags=['Mobile payments'], summary='Read your payment status')
	def get(self, request, payment_id):
		payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
		return Response(self.get_serializer(payment).data)


class RazorpayWebhookView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	@extend_schema(tags=['Gateway webhooks'], summary='Razorpay only: signed payment.captured webhook', request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, parameters=[OpenApiParameter('X-Razorpay-Signature', OpenApiTypes.STR, location=OpenApiParameter.HEADER, required=True)], description='Configure this HTTPS URL in Razorpay, subscribe to payment.captured and use the separate webhook secret. This is not an app callback.')
	def post(self, request):
		if not settings.RAZORPAY_WEBHOOK_SECRET:
			raise GatewayUnavailable('Payment webhook is not configured.')
		signature = request.headers.get('X-Razorpay-Signature', '')
		try:
			body = request.body.decode('utf-8')
			gateway_client().utility.verify_webhook_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
			event = json.loads(body)
		except (razorpay.errors.SignatureVerificationError, ValueError, UnicodeDecodeError) as error:
			raise serializers.ValidationError('Invalid webhook payload or signature.') from error
		if not isinstance(event, dict):
			raise serializers.ValidationError('Invalid webhook event.')
		if event.get('event') == 'payment.captured':
			try:
				entity = event['payload']['payment']['entity']
				order_id = entity['order_id']
			except (KeyError, TypeError):
				return Response({'received': True, 'processed': False})
			if not isinstance(order_id, str) or not order_id:
				return Response({'received': True, 'processed': False})
			payment = Payment.objects.filter(gateway_order_id=order_id).first()
			if payment is not None:
				record_capture(payment.pk, entity)
			else:
				subscription = Subscription.objects.filter(gateway_order_id=order_id).first()
				if subscription is None:
					return Response({'received': True, 'processed': False})
				record_subscription_capture(subscription.pk, entity)
		return Response({'received': True})


SUBSCRIPTION_COVER = (
	'The yearly plan covers unlimited general physician consultations for the buyer themself only '
	'(patient_relation self, no family_member). Specialist and family bookings are still paid.'
)


class SubscriptionPlanView(generics.GenericAPIView):
	permission_classes = [IsPatient]
	serializer_class = SubscriptionPlanSerializer

	@extend_schema(
		tags=['Mobile subscription'], summary='Yearly plan: price and my status', parameters=[SubscriptionCountrySerializer],
		description=(
			'Price is the staff-set subscription fee for the country (same as `subscription_fee` in `GET /api/v1/pricing/`). '
			'available=false: hide the plan. Show Buy/Renew only when can_purchase=true. ' + SUBSCRIPTION_COVER
		),
	)
	def get(self, request):
		query = SubscriptionCountrySerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		pricing = pricing_for(query.validated_data.get('country_code'))
		return Response(self.get_serializer(plan_payload(request.user, pricing)).data)


class SubscriptionOrderView(generics.GenericAPIView):
	permission_classes = [IsPatient]
	serializer_class = SubscriptionOrderRequestSerializer

	@extend_schema(
		tags=['Mobile subscription'], summary='Buy yearly plan: create/reuse Razorpay order',
		description=(
			'Send country_code (optional) and card/upi. The server sets the amount from the subscription fee. Open the Razorpay '
			'SDK with key_id, gateway_order_id, amount (paise) and currency, then call subscription/verify/. 400 when the plan '
			'is not offered or the current plan has more than 30 days left. 503 when Razorpay is not configured.'
		),
		responses={200: SubscriptionCheckoutOrderSerializer},
	)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		pricing = pricing_for(data.get('country_code'))
		with transaction.atomic():
			get_user_model().objects.select_for_update().get(pk=request.user.pk)
			reason = purchase_block_reason(request.user, pricing)
			if reason:
				raise serializers.ValidationError(reason)
			client = gateway_client()
			subscription = Subscription.objects.filter(
				user=request.user, status=Subscription.Status.PENDING, country_code=pricing.country_code,
				amount=pricing.subscription_fee, currency=pricing.currency,
			).order_by('-created_at').first()
			if subscription is None:
				subscription = Subscription.objects.create(
					user=request.user, country_code=pricing.country_code, amount=pricing.subscription_fee,
					currency=pricing.currency, method=data['method'],
				)
			if not subscription.gateway_order_id:
				try:
					order = client.order.create({
						'amount': to_minor_units(subscription.amount, subscription.currency),
						'currency': subscription.currency, 'receipt': f'subscription_{subscription.pk}',
					}, timeout=15)
				except GATEWAY_ERRORS as error:
					raise GatewayUnavailable() from error
				subscription.gateway_order_id = order['id']
			subscription.method = data['method']
			subscription.save(update_fields=['gateway_order_id', 'method'])
		return Response({
			'subscription_id': subscription.pk, 'gateway_order_id': subscription.gateway_order_id,
			'key_id': settings.RAZORPAY_KEY_ID, 'amount': to_minor_units(subscription.amount, subscription.currency),
			'currency': subscription.currency, 'status': subscription.status,
		})


class SubscriptionVerifyView(generics.GenericAPIView):
	permission_classes = [IsPatient]
	serializer_class = SubscriptionVerificationSerializer

	@extend_schema(
		tags=['Mobile subscription'], summary='Buy yearly plan: verify Razorpay result and activate',
		description=(
			'Call after Razorpay SDK success. The server checks the signature and that Razorpay captured the exact amount, '
			'then activates the plan for 365 days (a renewal starts when the current plan ends). Safe to repeat.'
		),
		responses=SubscriptionSerializer,
	)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		subscription = get_object_or_404(Subscription, pk=data['subscription_id'], user=request.user)
		if not subscription.gateway_order_id:
			raise serializers.ValidationError('Create a gateway order first.')
		client = gateway_client()
		try:
			client.utility.verify_payment_signature({
				'razorpay_order_id': subscription.gateway_order_id,
				'razorpay_payment_id': data['razorpay_payment_id'],
				'razorpay_signature': data['razorpay_signature'],
			})
		except razorpay.errors.SignatureVerificationError as error:
			raise serializers.ValidationError('Invalid payment signature.') from error
		try:
			entity = client.payment.fetch(data['razorpay_payment_id'], timeout=15)
		except GATEWAY_ERRORS as error:
			raise GatewayUnavailable() from error
		subscription = record_subscription_capture(subscription.pk, entity)
		return Response(SubscriptionSerializer(subscription).data)
