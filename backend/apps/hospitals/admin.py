from django.contrib import admin

from .models import Hospital, HospitalRecommendation


class HospitalRecommendationInline(admin.TabularInline):
    model = HospitalRecommendation
    extra = 1


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'is_partner', 'partner_discount_percentage', 'is_active')
    list_filter = ('is_partner', 'is_active', 'city')
    search_fields = ('name', 'city')
    inlines = [HospitalRecommendationInline]
