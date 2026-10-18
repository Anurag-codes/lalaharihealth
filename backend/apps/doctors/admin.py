from django.contrib import admin
from django.utils.html import format_html

from .models import DoctorApplication, DoctorApplicationDocument, DoctorDocument, DoctorProfile, Speciality


@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'fee', 'display_order', 'is_active')
    list_editable = ('fee', 'display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'short_name')


class DoctorDocumentInline(admin.TabularInline):
    model = DoctorDocument
    extra = 0


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'speciality', 'specialization', 'city', 'verification_status', 'consultation_fee', 'is_active')
    list_filter = ('verification_status', 'speciality', 'is_active', 'city')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'registration_number')
    inlines = [DoctorDocumentInline]


class DoctorApplicationDocumentInline(admin.TabularInline):
    model = DoctorApplicationDocument
    extra = 0


@admin.register(DoctorApplication)
class DoctorApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'photo_thumbnail',
        'full_name',
        'specialization',
        'consultation_category',
        'consultation_fee',
        'currency',
        'experience_years',
        'phone_number',
        'email',
        'status',
        'is_priority',
        'created_at',
    )
    list_display_links = ('photo_thumbnail', 'full_name')
    list_filter = ('status', 'is_priority')
    list_editable = ('status',)
    search_fields = ('full_name', 'email', 'phone_number', 'specialization')
    readonly_fields = ('photo_preview',)
    inlines = [DoctorApplicationDocumentInline]

    @admin.display(description='Photo')
    def photo_thumbnail(self, obj):
        if not obj.photo:
            return '-'
        return format_html('<img src="{}" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:50%">', obj.photo.url)

    @admin.display(description='Photo preview')
    def photo_preview(self, obj):
        if not obj.photo:
            return 'No photo uploaded. The website shows the default image.'
        return format_html('<img src="{}" alt="" style="max-width:240px;max-height:240px;border-radius:12px">', obj.photo.url)
