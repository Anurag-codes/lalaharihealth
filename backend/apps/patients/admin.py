from django.contrib import admin

from .models import FamilyMember, PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'city', 'date_of_birth', 'preferred_language')
    list_filter = ('preferred_language', 'gender')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relation', 'owner', 'gender', 'date_of_birth', 'created_at')
    list_filter = ('relation', 'gender')
    search_fields = ('full_name', 'owner__username', 'owner__email', 'owner__phone_number')
    raw_id_fields = ('owner',)
