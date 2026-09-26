from django.contrib import admin

from .models import FAQ, ContactMessage, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'patient_city', 'money_saved', 'is_published')
    list_filter = ('is_published',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'display_order', 'is_published')
    list_editable = ('display_order', 'is_published')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)
