from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment
from apps.payments.models import Payment

from .models import Appointment, AppointmentCall, AppointmentSlot


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('starts_at', 'doctor', 'capacity', 'is_active')
    list_filter = ('is_active', 'doctor')
    list_select_related = ('doctor',)
    date_hierarchy = 'starts_at'


class AppointmentCallInline(admin.TabularInline):
    model = AppointmentCall
    extra = 0
    fields = ('mode', 'provider', 'external_call_id', 'started_at', 'ended_at', 'duration_seconds', 'end_reason', 'metadata')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CompletionConfirmedFilter(admin.SimpleListFilter):
    title = 'completion confirmed'
    parameter_name = 'completion_confirmed'

    def lookups(self, request, model_admin):
        return [('no', 'Completed, awaiting confirmation'), ('yes', 'Confirmed')]

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(status=Appointment.Status.COMPLETED, completion_confirmed_at__isnull=True)
        if self.value() == 'yes':
            return queryset.filter(completion_confirmed_at__isnull=False)
        return queryset


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'slot_time', 'status', 'completed_at', 'completion_confirmed_at')
    list_filter = ('status', CompletionConfirmedFilter)
    readonly_fields = (
        'status', 'doctor', 'patient', 'consultation', 'slot', 'slot_time', 'completed_at',
        'completion_confirmed_at', 'completion_confirmed_by',
    )
    inlines = [AppointmentCallInline]
    actions = ['release_unstarted_reservations', 'confirm_completion']

    @admin.action(description='Confirm completion of consultations the doctor marked completed')
    def confirm_completion(self, request, queryset):
        updated = queryset.filter(status=Appointment.Status.COMPLETED, completion_confirmed_at__isnull=True).update(
            completion_confirmed_at=timezone.now(), completion_confirmed_by=request.user,
        )
        self.message_user(request, f'Confirmed {updated} completed consultation(s).')

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
