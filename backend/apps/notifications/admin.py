from django.contrib import admin, messages

from .models import Announcement, DeviceToken, Notification
from .service import send_announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'sent_at', 'recipient_count', 'created_at')
    list_filter = ('audience',)
    readonly_fields = ('created_by', 'sent_at', 'recipient_count', 'created_at')
    actions = ['send_now']

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.sent_at:
            return ('title', 'body', 'title_hi', 'body_hi', 'audience', *self.readonly_fields)
        return self.readonly_fields

    @admin.action(description='Send selected announcements to the bell (and push)')
    def send_now(self, request, queryset):
        delivered = sum(send_announcement(announcement) for announcement in queryset.filter(sent_at__isnull=True))
        self.message_user(request, f'Delivered to {delivered} user inbox(es). Already-sent announcements were skipped.', messages.SUCCESS)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'kind', 'read_at', 'created_at')
    list_filter = ('kind',)
    search_fields = ('user__username', 'user__email', 'user__phone_number', 'title')
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'updated_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__username', 'user__email', 'user__phone_number')
    readonly_fields = ('user', 'token', 'platform', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False
