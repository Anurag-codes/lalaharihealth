from django.contrib import admin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    DoctorApplication, DoctorApplicationDocument, DoctorAvailability, DoctorDocument, DoctorProfile, Speciality,
)


@admin.register(Speciality)
class SpecialityAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'fee', 'display_order', 'is_active')
    list_editable = ('fee', 'display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'short_name')


class DoctorDocumentInline(admin.TabularInline):
    model = DoctorDocument
    extra = 0
    fields = ('document_type', 'file', 'original_name', 'uploaded_at', 'download')
    readonly_fields = ('uploaded_at', 'download')

    @admin.display(description='Open')
    def download(self, obj):
        if not obj.pk:
            return '-'
        url = reverse('admin:doctors_doctorprofile_document', args=[obj.pk])
        return format_html('<a href="{}" target="_blank" rel="noopener">Download</a>', url)


class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 0


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'speciality', 'specialization', 'city', 'verification_status', 'consultation_fee', 'is_active')
    list_filter = ('verification_status', 'speciality', 'is_active', 'city')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__phone_number', 'registration_number')
    list_select_related = ('user', 'speciality')
    raw_id_fields = ('application',)
    inlines = [DoctorDocumentInline, DoctorAvailabilityInline]

    @admin.display(description='Phone', ordering='user__phone_number')
    def phone(self, obj):
        return obj.user.phone_number

    def get_urls(self):
        return [
            path('document/<int:document_id>/', self.admin_site.admin_view(self.download_document), name='doctors_doctorprofile_document'),
        ] + super().get_urls()

    def download_document(self, request, document_id):
        if not self.has_view_permission(request):
            raise Http404
        document = get_object_or_404(DoctorDocument, pk=document_id)
        try:
            handle = document.file.open('rb')
        except FileNotFoundError:
            raise Http404('File missing') from None
        return FileResponse(handle, as_attachment=True, filename=document.original_name or None)

    def save_model(self, request, obj, form, change):
        from apps.notifications.service import notify_doctor_verification

        if not obj.registration_number:
            obj.registration_number = None
        super().save_model(request, obj, form, change)
        if change and 'verification_status' in form.changed_data:
            notify_doctor_verification(obj)


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
