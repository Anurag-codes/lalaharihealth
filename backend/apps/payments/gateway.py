import razorpay
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.appointments.models import Appointment
from .models import Payment


class GatewayUnavailable(APIException):
    status_code = 503
    default_detail = 'Payment gateway is unavailable. Please retry later.'
    default_code = 'gateway_unavailable'


def gateway_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise GatewayUnavailable('Razorpay is not configured on the server.')
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def record_capture(payment_id, entity):
    consultation_id = Payment.objects.values_list('consultation_id', flat=True).get(pk=payment_id)
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(consultation_id=consultation_id)
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if (
            entity.get('order_id') != payment.gateway_order_id
            or entity.get('amount') != payment.amount * 100
            or entity.get('currency') != payment.currency
            or entity.get('status') != 'captured'
            or not entity.get('id')
        ):
            raise ValidationError('Gateway payment is not a captured payment for this order and amount.')
        if payment.status == Payment.Status.SUCCESS:
            if payment.transaction_id != entity['id']:
                raise ValidationError('This order already has a different successful payment.')
            return payment
        if payment.status != Payment.Status.PENDING:
            raise ValidationError('Payment cannot transition to success from its current state.')
        if appointment.status != Appointment.Status.AWAITING_PAYMENT:
            raise ValidationError('Appointment is not awaiting payment. Contact support.')
        payment.status = Payment.Status.SUCCESS
        payment.transaction_id = entity['id']
        if entity.get('method') in Payment.Method.values:
            payment.method = entity['method']
        payment.save(update_fields=['status', 'transaction_id', 'method'])
        appointment.status = Appointment.Status.FINDING_DOCTOR
        appointment.save(update_fields=['status'])
        return payment