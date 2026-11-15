from django import forms
from django.contrib import admin
from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.consultations.models import Consultation
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment
from apps.payments.models import Payment

from .models import Appointment, AppointmentCall, AppointmentSlot, FreeConsultationOffer
from .assignment import apply_assignment, appointment_assignment_doctors, assignment_lock_reason, prepare_assignment


class DoctorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return f'Dr. {user.get_full_name() or user.username} (User ID: {user.pk})'


class FreeConsultationOfferForm(forms.ModelForm):
    doctor = DoctorChoiceField(queryset=User.objects.filter(
        role='doctor', is_active=True, doctor_profile__is_active=True,
        doctor_profile__verification_status='verified', doctor_profile__speciality__isnull=True,
    ))

    class Meta:
        model = FreeConsultationOffer
        fields = '__all__'


@admin.register(FreeConsultationOffer)
class FreeConsultationOfferAdmin(admin.ModelAdmin):
    form = FreeConsultationOfferForm
    list_display = ('coupon_code', 'doctor', 'is_active', 'valid_from', 'valid_until')
    list_filter = ('is_active',)
    list_select_related = ('doctor',)


class AppointmentAssignmentForm(forms.ModelForm):
    doctor = DoctorChoiceField(
        queryset=User.objects.none(), required=False,
        help_text='Assign an active, verified doctor of this booking category. Confirmed appointments may be changed only before the consultation or a call starts and before video join credentials are issued.',
    )

    class Meta:
        model = Appointment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_slot_time = self.instance.slot_time
        self.assignment_plan = None
        if self.instance.pk and 'doctor' in self.fields:
            self.fields['doctor'].queryset = User.objects.filter(
                Q(doctor_profile__in=appointment_assignment_doctors(self.instance)) | Q(pk=self.instance.doctor_id),
            )
            if self.instance.status == Appointment.Status.CONFIRMED:
                self.fields['doctor'].required = True

    def clean(self):
        cleaned = super().clean()
        if 'doctor' not in self.fields or self.instance.status not in (Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED):
            return cleaned
        doctor, starts_at = cleaned.get('doctor'), cleaned.get('slot_time')
        if doctor is None:
            if starts_at and starts_at != self.original_slot_time:
                self.add_error('doctor', 'Choose a doctor when changing the appointment time.')
            return cleaned
        if starts_at is None:
            return cleaned
        try:
            self.assignment_plan = prepare_assignment(
                self.instance.pk, doctor.pk, starts_at if starts_at != self.original_slot_time else None,
            )
        except Http404:
            self.add_error('doctor', 'Choose an active, verified doctor of the appointment category.')
        except ValidationError as error:
            if isinstance(error.detail, dict):
                for field, messages in error.detail.items():
                    form_field = {'doctor_id': 'doctor', 'starts_at': 'slot_time'}.get(field)
                    values = messages if isinstance(messages, (list, tuple)) else [messages]
                    self.add_error(form_field, [str(message) for message in values])
            else:
                self.add_error(None, [str(message) for message in error.detail])
        return cleaned


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('starts_at', 'doctor', 'capacity', 'is_active')
    list_filter = ('is_active', 'doctor')
    list_select_related = ('doctor',)
    date_hierarchy = 'starts_at'


class AppointmentCallInline(admin.TabularInline):
    model = AppointmentCall
    extra = 0
    fields = ('mode', 'provider', 'external_call_id', 'status', 'started_at', 'ended_at', 'duration_seconds', 'end_reason', 'metadata')
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
    form = AppointmentAssignmentForm
    list_display = ('id', 'patient', 'doctor', 'slot_time', 'status', 'completed_at', 'completion_confirmed_at')
    list_filter = ('status', CompletionConfirmedFilter)
    readonly_fields = (
        'status', 'doctor', 'patient', 'consultation', 'slot', 'slot_time', 'completed_at',
        'completion_confirmed_at', 'completion_confirmed_by', 'assignment_edit_notice',
        'coupon_code', 'free_consultation_doctor',
    )
    inlines = [AppointmentCallInline]
    actions = ['release_unstarted_reservations', 'confirm_completion']

    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        if obj is not None and request.method == 'POST' and connection.in_atomic_block:
            # Serialize admin saves with API assignment before binding editable fields.
            consultation = Consultation.objects.select_for_update().filter(pk=obj.consultation_id).first()
            if consultation is None:
                return None
            return self.get_queryset(request).select_for_update().filter(pk=obj.pk).first()
        return obj

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not obj or obj.status != Appointment.Status.CONFIRMED or not assignment_lock_reason(obj):
            fields = tuple(field for field in fields if field != 'assignment_edit_notice')
        if obj and obj.status in (Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED) and self.has_change_permission(request, obj):
            locked = obj.status == Appointment.Status.CONFIRMED and assignment_lock_reason(obj)
            submitted_assignment = request.method == 'POST' and any(
                key in request.POST for key in ('doctor', 'slot_time_0', 'slot_time_1')
            )
            if not locked or submitted_assignment:
                return tuple(field for field in fields if field not in ('doctor', 'slot_time'))
        return fields

    @admin.display(description='Assignment editing locked')
    def assignment_edit_notice(self, obj):
        return assignment_lock_reason(obj) or ''

    def save_model(self, request, obj, form, change):
        if form.assignment_plan is not None:
            assigned = apply_assignment(form.assignment_plan)
            # Keep the admin's bound instance in sync before its normal model save.
            for field in ('doctor', 'slot', 'slot_time', 'status', 'doctor_assigned_at', 'reminder_sent_at'):
                setattr(obj, field, getattr(assigned, field))
        super().save_model(request, obj, form, change)

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
