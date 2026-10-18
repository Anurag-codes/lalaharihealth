from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', views.UnreadCountView.as_view(), name='notification-unread-count'),
    path('read-all/', views.NotificationReadAllView.as_view(), name='notification-read-all'),
    path('<int:notification_id>/read/', views.NotificationReadView.as_view(), name='notification-read'),
    path('devices/', views.DeviceTokenView.as_view(), name='device-register'),
    path('devices/remove/', views.DeviceTokenRemoveView.as_view(), name='device-remove'),
]
