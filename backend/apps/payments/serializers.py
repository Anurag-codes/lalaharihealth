from rest_framework import serializers

from .models import Payment, Subscription


class PaymentOrderRequestSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=[('card', 'Card'), ('upi', 'UPI')])


class CheckoutOrderSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    gateway_order_id = serializers.CharField()
    key_id = serializers.CharField()
    amount = serializers.IntegerField(
        help_text='Smallest currency unit for Razorpay: 20000 = INR 200 (paise), 1000 = USD 10 (cents)',
    )
    currency = serializers.CharField()
    status = serializers.CharField()


class PaymentVerificationSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField(min_value=1, help_text='Local payment id from the order API')
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.RegexField(r'^[a-fA-F0-9]{64}$')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'consultation', 'amount', 'currency', 'method', 'status', 'gateway_order_id', 'transaction_id', 'created_at']
        read_only_fields = fields


class SubscriptionCountrySerializer(serializers.Serializer):
    country_code = serializers.RegexField(
        r'^[A-Za-z]{2}$', required=False,
        help_text='ISO country code from pricing (step 1). Missing or not configured = default country (India).',
    )


class SubscriptionPlanSerializer(serializers.Serializer):
    available = serializers.BooleanField(help_text='False when staff have not set a subscription fee: hide the plan.')
    country_code = serializers.CharField()
    amount = serializers.IntegerField(allow_null=True, help_text='Whole units, e.g. 999 = INR 999')
    currency = serializers.CharField(allow_null=True)
    amount_display = serializers.CharField(allow_null=True)
    valid_days = serializers.IntegerField()
    is_active = serializers.BooleanField(help_text='Covered right now')
    active_until = serializers.DateTimeField(allow_null=True, help_text='End of paid cover, including a bought renewal')
    can_purchase = serializers.BooleanField(help_text='Show Buy/Renew. Renewal opens in the last 30 days of cover.')


class SubscriptionOrderRequestSerializer(SubscriptionCountrySerializer):
    method = serializers.ChoiceField(choices=[('card', 'Card'), ('upi', 'UPI')])


class SubscriptionCheckoutOrderSerializer(serializers.Serializer):
    subscription_id = serializers.IntegerField()
    gateway_order_id = serializers.CharField()
    key_id = serializers.CharField()
    amount = serializers.IntegerField(help_text='Smallest currency unit for Razorpay: 99900 = INR 999 (paise)')
    currency = serializers.CharField()
    status = serializers.CharField()


class SubscriptionVerificationSerializer(serializers.Serializer):
    subscription_id = serializers.IntegerField(min_value=1, help_text='Local subscription id from the order API')
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.RegexField(r'^[a-fA-F0-9]{64}$')


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'id', 'country_code', 'amount', 'currency', 'method', 'status', 'starts_at', 'ends_at', 'paid_at',
            'gateway_order_id', 'transaction_id', 'created_at',
        ]
        read_only_fields = fields