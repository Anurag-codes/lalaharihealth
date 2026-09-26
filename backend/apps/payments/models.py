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
    amount = models.PositiveIntegerField(help_text='Amount in INR')
    method = models.CharField(max_length=15, choices=Method.choices, default=Method.UPI)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.pk} - INR {self.amount}'
