from django.conf import settings
from django.db import models

from apps.consultations.models import Consultation


class Payment(models.Model):
    """Payment record for a consultation's fee."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    class Method(models.TextChoices):
        UPI = 'upi', 'UPI'
        CARD = 'card', 'Card'
        NETBANKING = 'netbanking', 'Netbanking'
        WALLET = 'wallet', 'Wallet'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='payments', on_delete=models.CASCADE)
    consultation = models.OneToOneField(
        Consultation, related_name='payment', on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.PositiveIntegerField(help_text='Amount in whole units of currency')
    method = models.CharField(max_length=15, choices=Method.choices, default=Method.UPI)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    gateway_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.pk} - {self.currency} {self.amount}'


class Subscription(models.Model):
    """Yearly plan: unlimited general physician consultations for the buyer themself (not family members)."""

    VALID_DAYS = 365

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending payment'
        ACTIVE = 'active', 'Paid'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='subscriptions', on_delete=models.PROTECT)
    country_code = models.CharField(max_length=2)
    amount = models.PositiveIntegerField(help_text='Price paid, whole units of currency (staff-set subscription fee)')
    currency = models.CharField(max_length=3)
    method = models.CharField(max_length=15, choices=Payment.Method.choices, default=Payment.Method.UPI)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    gateway_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True, help_text='Set on payment; a renewal starts when the current plan ends')
    ends_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Subscription #{self.pk} - {self.user} ({self.get_status_display()})'
