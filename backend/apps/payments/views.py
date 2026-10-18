import json

import razorpay
import requests
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.pricing.service import to_minor_units
from .gateway import GatewayUnavailable, gateway_client, record_capture
from .models import Payment
from .serializers import (
	CheckoutOrderSerializer, PaymentOrderRequestSerializer, PaymentSerializer,
	PaymentVerificationSerializer,
)

GATEWAY_ERRORS = (razorpay.errors.BadRequestError, razorpay.errors.GatewayError, razorpay.errors.ServerError, requests.RequestException)


class PaymentOrderView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PaymentOrderRequestSerializer

	@extend_schema(tags=['Mobile payments'], summary='Step 5: create/reuse Razorpay checkout order', description='Send only appointment_id and card/upi. Server controls amount and currency. Use the returned key_id, gateway_order_id, amount (smallest unit: paise for INR, cents for USD) and currency with the official Razorpay mobile SDK. The currency follows the booking country (international payments must be enabled in Razorpay). Never send PAN, CVV, card details or UPI credentials to this API. Returns 503 when gateway keys are not configured.', responses={200: CheckoutOrderSerializer})
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		client = gateway_client()
		with transaction.atomic():
			appointment = get_object_or_404(Appointment.objects.select_for_update(), pk=data['appointment_id'], patient=request.user)
			if appointment.status != Appointment.Status.AWAITING_PAYMENT:
				raise serializers.ValidationError('This appointment is not awaiting payment.')
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
				payment = Payment.objects.get(gateway_order_id=entity['order_id'])
			except (KeyError, TypeError, Payment.DoesNotExist):
				return Response({'received': True, 'processed': False})
			record_capture(payment.pk, entity)
		return Response({'received': True})
