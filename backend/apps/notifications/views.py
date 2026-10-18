from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DeviceToken, Notification
from .serializers import (
    DeviceTokenRemoveSerializer, DeviceTokenSerializer, MarkAllReadResultSerializer,
    NotificationQuerySerializer, NotificationSerializer, UnreadCountSerializer,
)

NOTIFICATION_EXAMPLE = {
    'id': 91, 'kind': 'doctor_assigned', 'kind_label': 'Doctor assigned', 'title': 'Appointment confirmed',
    'body': 'Dr. Ananya Sharma will consult Rahul Sharma on 18 Oct 2026 at 10:00 AM.',
    'appointment_id': 12345, 'consultation_id': 42, 'is_read': False, 'read_at': None,
    'created_at': '2026-10-17T15:02:00+05:30',
}
TAG = ['Notifications']


def unread(user):
    return Notification.objects.filter(user=user, read_at__isnull=True)


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        query = NotificationQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        queryset = Notification.objects.filter(user=self.request.user)
        if query.validated_data.get('unread'):
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    @extend_schema(
        tags=TAG, summary='Bell: my notifications, newest first',
        description=(
            'Kinds: payment_success, doctor_assigned, appointment_reminder, consultation_completed, '
            'appointment_cancelled, announcement. Text is in the language chosen in Profile (en/hi). '
            'Tap -> open appointment_id when set.'
        ),
        parameters=[NotificationQuerySerializer],
        examples=[OpenApiExample('Notifications', response_only=True, value={
            'count': 1, 'next': None, 'previous': None, 'results': [NOTIFICATION_EXAMPLE],
        })],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UnreadCountView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UnreadCountSerializer

    @extend_schema(
        tags=TAG, summary='Bell red dot: unread notification count',
        examples=[OpenApiExample('Unread', response_only=True, value={'unread_count': 2})],
    )
    def get(self, request):
        return Response({'unread_count': unread(request.user).count()})


class NotificationReadView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(tags=TAG, summary='Mark one notification as read', request=None, responses=NotificationSerializer)
    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(self.get_serializer(notification).data)


class NotificationReadAllView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkAllReadResultSerializer

    @extend_schema(
        tags=TAG, summary='Mark all notifications as read', request=None,
        examples=[OpenApiExample('Marked', response_only=True, value={'marked_read': 2})],
    )
    def post(self, request):
        return Response({'marked_read': unread(request.user).update(read_at=timezone.now())})


class DeviceTokenView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    @extend_schema(
        tags=TAG, summary='Register this device for push notifications',
        description=(
            'Call after login and whenever Firebase Messaging gives a new token. '
            'A token already registered to another account moves to the current one.'
        ),
        responses={200: DeviceTokenSerializer},
        examples=[OpenApiExample('Android', request_only=True, value={'token': 'fcm-registration-token-from-firebase-messaging', 'platform': 'android'})],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, _ = DeviceToken.objects.update_or_create(
            token=serializer.validated_data['token'],
            defaults={'user': request.user, 'platform': serializer.validated_data['platform'], 'is_active': True},
        )
        return Response(self.get_serializer(device).data)


class DeviceTokenRemoveView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenRemoveSerializer

    @extend_schema(
        tags=TAG, summary='Stop push notifications on this device (call on logout)', responses={204: None},
        examples=[OpenApiExample('Logout', request_only=True, value={'token': 'fcm-registration-token-from-firebase-messaging'})],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.objects.filter(user=request.user, token=serializer.validated_data['token']).delete()
        return Response(status=204)
