from django.contrib import admin

from .models import Consultation, ConsultationReview, PrescriptionDocument, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


class PrescriptionDocumentInline(admin.TabularInline):
    model = PrescriptionDocument
    extra = 0
    fields = ('original_name', 'uploaded_by', 'uploaded_at')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'patient_name', 'patient_relation', 'doctor', 'condition', 'status', 'mode', 'fee_charged', 'created_at')
    list_filter = ('status', 'mode', 'recommended_system')
    search_fields = ('patient__username', 'doctor__username', 'patient_name')
    raw_id_fields = ('family_member',)
    inlines = [PrescriptionItemInline, PrescriptionDocumentInline]


@admin.register(ConsultationReview)
class ConsultationReviewAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'doctor', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('doctor__username', 'doctor__first_name', 'reviewer__username', 'feedback')
    readonly_fields = ('consultation', 'reviewer', 'doctor', 'rating', 'feedback', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
