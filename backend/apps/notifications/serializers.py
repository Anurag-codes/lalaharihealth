from rest_framework import serializers

from .models import DeviceToken, Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    appointment_id = serializers.IntegerField(read_only=True, allow_null=True, help_text='Open the appointment when set')
    consultation_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'kind_label', 'title', 'body', 'appointment_id', 'consultation_id', 'is_read', 'read_at', 'created_at']
        read_only_fields = fields

    def get_is_read(self, obj) -> bool:
        return obj.read_at is not None


class NotificationQuerySerializer(serializers.Serializer):
    unread = serializers.BooleanField(required=False, help_text='true = only unread notifications')


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkAllReadResultSerializer(serializers.Serializer):
    marked_read = serializers.IntegerField()


class DeviceTokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=512, help_text='Firebase Cloud Messaging registration token')

    class Meta:
        model = DeviceToken
        fields = ['token', 'platform']


class DeviceTokenRemoveSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
