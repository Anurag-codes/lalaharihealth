from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, VerifiedIdentity


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'city', 'is_active')
    list_filter = ('role', 'is_active', 'is_phone_verified', 'is_email_verified')
    readonly_fields = ('is_email_verified', 'is_phone_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('LalahariHealth Profile', {'fields': ('role', 'phone_number', 'is_phone_verified', 'is_email_verified', 'city')}),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            kinds = set(obj.verified_identities.values_list('kind', flat=True))
            if 'email' in kinds:
                fields.append('email')
            if 'phone' in kinds:
                fields.append('phone_number')
        return fields


@admin.register(VerifiedIdentity)
class VerifiedIdentityAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'value', 'verified_at')
    search_fields = ('value', 'user__username')
    readonly_fields = ('user', 'kind', 'value', 'firebase_uid', 'verified_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
