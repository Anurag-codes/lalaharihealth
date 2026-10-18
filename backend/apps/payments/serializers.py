from rest_framework import serializers

from .models import Payment


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