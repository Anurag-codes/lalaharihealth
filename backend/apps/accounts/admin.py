from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'city', 'is_active')
    list_filter = ('role', 'is_active', 'is_phone_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('LalahariHealth Profile', {'fields': ('role', 'phone_number', 'is_phone_verified', 'city')}),
    )
