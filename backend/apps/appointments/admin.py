from django.contrib import admin
from django.db import transaction

from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment
from apps.payments.models import Payment

from .models import Appointment, AppointmentSlot


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('starts_at', 'doctor', 'capacity', 'is_active')
    list_filter = ('is_active', 'doctor')
    list_select_related = ('doctor',)
    date_hierarchy = 'starts_at'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'slot_time', 'status')
    list_filter = ('status',)
    readonly_fields = ('status', 'doctor', 'patient', 'consultation', 'slot', 'slot_time')
    actions = ['release_unstarted_reservations']

    @admin.action(description='Release unpaid reservations that have no gateway order')
    def release_unstarted_reservations(self, request, queryset):
        released = 0
        for appointment_id in queryset.values_list('id', flat=True):
            with transaction.atomic():
                appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
                if appointment.status != Appointment.Status.AWAITING_PAYMENT:
                    continue
                payment = Payment.objects.filter(consultation=appointment.consultation).first()
                if payment and (payment.gateway_order_id or payment.status != Payment.Status.PENDING):
                    continue
                appointment.save(update_fields=appointment.set_status(Appointment.Status.CANCELLED))
                appointment.consultation.status = 'cancelled'
                appointment.consultation.save(update_fields=['status'])
                notify_appointment(appointment, Notification.Kind.APPOINTMENT_CANCELLED)
                released += 1
        self.message_user(request, f'Released {released} unpaid reservation(s).')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
