from django.contrib import admin

from .models import DoctorApplication, DoctorApplicationDocument, DoctorDocument, DoctorProfile


class DoctorDocumentInline(admin.TabularInline):
    model = DoctorDocument
    extra = 0


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'city', 'verification_status', 'consultation_fee', 'is_active')
    list_filter = ('verification_status', 'is_active', 'city')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'registration_number')
    inlines = [DoctorDocumentInline]


class DoctorApplicationDocumentInline(admin.TabularInline):
    model = DoctorApplicationDocument
    extra = 0


@admin.register(DoctorApplication)
class DoctorApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'specialization',
        'experience_years',
        'phone_number',
        'email',
        'status',
        'is_priority',
        'created_at',
    )
    list_filter = ('status', 'is_priority')
    search_fields = ('full_name', 'email', 'phone_number', 'specialization')
    inlines = [DoctorApplicationDocumentInline]
