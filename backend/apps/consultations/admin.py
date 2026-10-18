from django.contrib import admin

from .models import Consultation, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'patient_name', 'patient_relation', 'doctor', 'condition', 'status', 'mode', 'fee_charged', 'created_at')
    list_filter = ('status', 'mode', 'recommended_system')
    search_fields = ('patient__username', 'doctor__username', 'patient_name')
    raw_id_fields = ('family_member',)
    inlines = [PrescriptionItemInline]
