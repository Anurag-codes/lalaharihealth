from datetime import timedelta

import razorpay
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.appointments.models import Appointment
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment
from apps.pricing.service import to_minor_units
from .models import Payment, Subscription


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
            or entity.get('amount') != to_minor_units(payment.amount, payment.currency)
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
        appointment.save(update_fields=appointment.set_status(Appointment.Status.FINDING_DOCTOR))
        notify_appointment(appointment, Notification.Kind.PAYMENT_SUCCESS)
        return payment


def record_subscription_capture(subscription_id, entity):
    """Activate a paid yearly plan. A renewal starts when the current plan ends."""
    user_id = Subscription.objects.values_list('user_id', flat=True).get(pk=subscription_id)
    with transaction.atomic():
        # Serialises activations per user so stacked plans never overlap.
        get_user_model().objects.select_for_update().get(pk=user_id)
        subscription = Subscription.objects.select_for_update().get(pk=subscription_id)
        if (
            entity.get('order_id') != subscription.gateway_order_id
            or entity.get('amount') != to_minor_units(subscription.amount, subscription.currency)
            or entity.get('currency') != subscription.currency
            or entity.get('status') != 'captured'
            or not entity.get('id')
        ):
            raise ValidationError('Gateway payment is not a captured payment for this order and amount.')
        if subscription.status == Subscription.Status.ACTIVE:
            if subscription.transaction_id != entity['id']:
                raise ValidationError('This order already has a different successful payment.')
            return subscription
        if subscription.status != Subscription.Status.PENDING:
            raise ValidationError('Subscription cannot be activated from its current state.')
        now = timezone.now()
        current_end = Subscription.objects.filter(
            user_id=user_id, status=Subscription.Status.ACTIVE, ends_at__gt=now,
        ).aggregate(end=Max('ends_at'))['end']
        subscription.status = Subscription.Status.ACTIVE
        subscription.transaction_id = entity['id']
        if entity.get('method') in Payment.Method.values:
            subscription.method = entity['method']
        subscription.paid_at = now
        subscription.starts_at = max(now, current_end) if current_end else now
        subscription.ends_at = subscription.starts_at + timedelta(days=Subscription.VALID_DAYS)
        subscription.save(update_fields=['status', 'transaction_id', 'method', 'paid_at', 'starts_at', 'ends_at'])
        return subscription