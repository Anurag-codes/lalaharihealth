from django.contrib import admin

from .models import Payment


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
