from django.contrib import admin

from .models import CountryPricing


@admin.register(CountryPricing)
class CountryPricingAdmin(admin.ModelAdmin):
    list_display = (
        'country_name', 'country_code', 'currency', 'currency_symbol', 'general_fee',
        'specialist_fee_min', 'specialist_fee_max', 'specialist_fee_step', 'is_default', 'is_active', 'updated_at',
    )
    list_editable = ('general_fee', 'is_active')
    list_filter = ('is_active', 'currency')
    search_fields = ('country_name', 'country_code', 'currency')

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_default:
            return False
        return super().has_delete_permission(request, obj)
