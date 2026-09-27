from django.contrib import admin

from .models import Hospital, HospitalApplication, HospitalApplicationDocument, HospitalRecommendation


class HospitalRecommendationInline(admin.TabularInline):
    model = HospitalRecommendation
    extra = 1


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'is_partner', 'partner_discount_percentage', 'is_active')
    list_filter = ('is_partner', 'is_active', 'city')
    search_fields = ('name', 'city')
    inlines = [HospitalRecommendationInline]


class HospitalApplicationDocumentInline(admin.TabularInline):
    model = HospitalApplicationDocument
    extra = 0


@admin.register(HospitalApplication)
class HospitalApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'facility_name',
        'contact_person_name',
        'city',
        'phone_number',
        'email',
        'status',
        'is_priority',
        'created_at',
    )
    list_filter = ('status', 'is_priority')
    search_fields = ('facility_name', 'contact_person_name', 'email', 'phone_number', 'city')
    inlines = [HospitalApplicationDocumentInline]
