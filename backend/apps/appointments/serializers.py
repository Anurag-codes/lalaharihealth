from rest_framework import serializers

from .models import Appointment, AppointmentSlot


class SlotQuerySerializer(serializers.Serializer):
    date = serializers.DateField(help_text='Local India date, YYYY-MM-DD')


class AppointmentSlotSerializer(serializers.ModelSerializer):
    remaining_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = AppointmentSlot
        fields = ['id', 'starts_at', 'remaining_capacity']


class AppointmentRequestSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField(min_value=1)
    slot_id = serializers.IntegerField(min_value=1)


class DoctorAssignmentSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(min_value=1)


class AppointmentSerializer(serializers.ModelSerializer):
    appointment_number = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='consultation.fee_charged', read_only=True)
    currency = serializers.CharField(default='INR', read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ['id', 'appointment_number', 'consultation', 'slot', 'slot_time', 'status', 'doctor', 'amount', 'currency', 'payment_status', 'created_at']
        read_only_fields = fields

    def get_appointment_number(self, obj) -> str:
        return f'APT-{obj.pk:05d}'

    def get_payment_status(self, obj) -> str:
        payment = getattr(obj.consultation, 'payment', None)
        return payment.status if payment else 'not_started'