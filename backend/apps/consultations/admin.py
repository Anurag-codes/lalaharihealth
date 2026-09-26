from django.contrib import admin

from .models import Consultation


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'condition', 'status', 'mode', 'fee_charged', 'created_at')
    list_filter = ('status', 'mode', 'recommended_system')
    search_fields = ('patient__username', 'doctor__username')
