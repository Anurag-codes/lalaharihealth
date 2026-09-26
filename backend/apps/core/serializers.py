from rest_framework import serializers

from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'phone_number', 'email', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']
