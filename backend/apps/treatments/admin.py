from django.contrib import admin

from .models import Condition, TreatmentOption


class TreatmentOptionInline(admin.TabularInline):
    model = TreatmentOption
    extra = 1


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TreatmentOptionInline]


@admin.register(TreatmentOption)
class TreatmentOptionAdmin(admin.ModelAdmin):
    list_display = ('condition', 'system', 'estimated_cost_min', 'estimated_cost_max', 'is_recommended')
    list_filter = ('system', 'is_recommended')
