from django.contrib import admin

from .models import Condition, ConditionType, ConditionVariant, TreatmentOption


class TreatmentOptionInline(admin.TabularInline):
    model = TreatmentOption
    extra = 1


class ConditionTypeInline(admin.TabularInline):
    model = ConditionType
    extra = 1
    fields = ('name', 'display_order', 'is_active')
    show_change_link = True


class ConditionVariantInline(admin.TabularInline):
    model = ConditionVariant
    extra = 1
    fields = ('name', 'display_order', 'is_active')


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'type_label', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ConditionTypeInline, TreatmentOptionInline]


@admin.register(ConditionType)
class ConditionTypeAdmin(admin.ModelAdmin):
    """Second level of the booking Symptoms dropdown; variants are the third level."""

    list_display = ('name', 'condition', 'display_order', 'is_active')
    list_filter = ('is_active', 'condition')
    search_fields = ('name', 'condition__name')
    inlines = [ConditionVariantInline]


@admin.register(TreatmentOption)
class TreatmentOptionAdmin(admin.ModelAdmin):
    list_display = ('condition', 'system', 'estimated_cost_min', 'estimated_cost_max', 'is_recommended')
    list_filter = ('system', 'is_recommended')
