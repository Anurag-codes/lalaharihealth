from django.contrib import admin

from .models import Payment, Subscription


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'method', 'status', 'created_at')
    list_filter = ('status', 'method')
    search_fields = ('user__username', 'transaction_id')
    readonly_fields = (
        'user', 'consultation', 'amount', 'currency', 'method', 'status',
        'transaction_id', 'gateway_order_id', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Read-only finance record. The price is set as Subscription fee in Country pricing."""

    list_display = ('id', 'user', 'amount', 'currency', 'status', 'starts_at', 'ends_at', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('user__username', 'user__phone_number', 'transaction_id', 'gateway_order_id')
    readonly_fields = (
        'user', 'country_code', 'amount', 'currency', 'method', 'status', 'gateway_order_id', 'transaction_id',
        'starts_at', 'ends_at', 'paid_at', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
