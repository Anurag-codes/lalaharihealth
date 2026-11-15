from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment, notify_doctor
from apps.payments.models import Payment
from .availability import booking_time_error
from .models import Appointment, AppointmentCall, AppointmentSlot, AppointmentVideoRoom

FREED_STATUSES = (Appointment.Status.CANCELLED, Appointment.Status.COMPLETED)
CONSULTATION_LOCKED = 'The consultation has started or is completed or cancelled; its assignment cannot be changed.'
CALL_LOCKED = 'A call has started or completed; its appointment assignment cannot be changed.'
VIDEO_LOCKED = 'Issued video join credentials forbid rescheduling or changing the doctor; contact support.'
LOCKED_CONSULTATION_STATUSES = (Consultation.Status.ONGOING, Consultation.Status.COMPLETED, Consultation.Status.CANCELLED)


def call_started(call):
    return bool(
        call.started_at or (call.duration_seconds or 0) > 0
        or call.status in (AppointmentCall.Status.IN_PROGRESS, AppointmentCall.Status.COMPLETED)
    )


def assignment_doctors(consultation):
    return DoctorProfile.objects.filter(
        is_active=True, user__is_active=True, user__role='doctor', verification_status='verified',
        speciality_id=consultation.speciality_id,
    )


def appointment_assignment_doctors(appointment):
    profiles = assignment_doctors(appointment.consultation)
    if appointment.free_consultation_doctor_id:
        profiles = profiles.filter(user_id=appointment.free_consultation_doctor_id)
    return profiles


@dataclass
class AssignmentPlan:
    appointment: Appointment
    profile: DoctorProfile | None
    starts_at: datetime
    slot: AppointmentSlot | None
    unchanged: bool = False


def assignment_lock_reason(appointment, consultation=None):
    consultation = consultation or appointment.consultation
    if consultation.status in LOCKED_CONSULTATION_STATUSES:
        return CONSULTATION_LOCKED
    if appointment.calls.filter(
        Q(started_at__isnull=False) | Q(status__in=(AppointmentCall.Status.IN_PROGRESS, AppointmentCall.Status.COMPLETED))
        | Q(duration_seconds__gt=0),
    ).exists():
        return CALL_LOCKED
    if AppointmentVideoRoom.objects.filter(appointment=appointment, room_id__isnull=False).exclude(room_id='').exists():
        return VIDEO_LOCKED
    return None


def prepare_assignment(appointment_id, doctor_id=None, starts_at=None):
    """Validate and lock an assignment inside the caller's transaction without saving changes."""
    snapshot = get_object_or_404(Appointment.objects.only('consultation_id', 'status'), pk=appointment_id)
    # Match clinical-record completion's consultation -> appointment lock order.
    consultation = get_object_or_404(Consultation.objects.select_for_update(), pk=snapshot.consultation_id)
    appointment = get_object_or_404(
        Appointment.objects.select_for_update(of=('self',)).select_related('patient'), pk=appointment_id,
    )
    if appointment.status not in (Appointment.Status.FINDING_DOCTOR, Appointment.Status.CONFIRMED):
        raise ValidationError('Only paid or approved free appointments awaiting matching, or confirmed appointments, can be assigned.')
    target_time = starts_at if starts_at is not None else appointment.slot_time
    if doctor_id is None:
        if appointment.status == Appointment.Status.FINDING_DOCTOR or appointment.doctor_id is None:
            raise ValidationError({'doctor_id': 'Choose a doctor for this appointment.'})
        doctor_id = appointment.doctor_id
    if appointment.free_consultation_doctor_id and doctor_id != appointment.free_consultation_doctor_id:
        raise ValidationError({'doctor_id': 'A free coupon booking must be assigned to its selected offer doctor.'})
    appointment.consultation = consultation
    if (appointment.status == Appointment.Status.CONFIRMED and doctor_id == appointment.doctor_id
            and target_time == appointment.slot_time):
        return AssignmentPlan(appointment, None, target_time, appointment.slot, unchanged=True)
    if appointment.status == Appointment.Status.CONFIRMED:
        reason = assignment_lock_reason(appointment, consultation)
        if reason:
            raise ValidationError(reason)
    if not appointment.is_free_consultation and not Payment.objects.filter(consultation=consultation, status=Payment.Status.SUCCESS).exists():
        raise ValidationError('Confirmed payment is required.')
    if starts_at is not None or appointment.status == Appointment.Status.CONFIRMED:
        error = booking_time_error(target_time)
        if error:
            raise ValidationError({'starts_at': error})
    # Serialize swaps in the same doctor order, including the previous doctor.
    list(DoctorProfile.objects.select_for_update(of=('self',)).filter(
        user_id__in={doctor_id, appointment.doctor_id} - {None},
    ).order_by('user_id'))
    profile = get_object_or_404(
        appointment_assignment_doctors(appointment).select_related('user'), user_id=doctor_id,
    )
    if Appointment.objects.filter(
        doctor=profile.user, slot_time=target_time,
    ).exclude(pk=appointment.pk).exclude(status__in=FREED_STATUSES).exists():
        raise ValidationError({'doctor_id': 'Doctor already has an appointment at this time.'})
    slot = AppointmentSlot.objects.select_for_update().filter(
        doctor=profile.user, starts_at=target_time, is_active=True,
    ).first()
    if slot is not None and slot.appointments.exclude(pk=appointment.pk).exclude(status__in=FREED_STATUSES).count() >= slot.capacity:
        slot = None
    return AssignmentPlan(appointment, profile, target_time, slot)


def apply_assignment(plan):
    """Save a previously validated, still-locked plan inside the caller's transaction."""
    appointment = plan.appointment
    if plan.unchanged:
        return appointment
    changed_time = appointment.slot_time != plan.starts_at
    changed_doctor = appointment.doctor_id != plan.profile.user_id
    appointment.doctor, appointment.slot, appointment.slot_time = plan.profile.user, plan.slot, plan.starts_at
    update_fields = ['doctor', 'slot', 'slot_time']
    if appointment.status != Appointment.Status.CONFIRMED:
        update_fields += appointment.set_status(Appointment.Status.CONFIRMED)
    if changed_time or changed_doctor:
        appointment.reminder_sent_at = None
        update_fields.append('reminder_sent_at')
    appointment.save(update_fields=update_fields)
    consultation = appointment.consultation
    consultation.doctor, consultation.scheduled_at = plan.profile.user, plan.starts_at
    consultation.save(update_fields=['doctor', 'scheduled_at'])
    notify_appointment(appointment, Notification.Kind.DOCTOR_ASSIGNED)
    notify_doctor(appointment, Notification.Kind.APPOINTMENT_ASSIGNED)
    return appointment


def assign_doctor(appointment_id, doctor_id=None, starts_at=None):
    with transaction.atomic():
        return apply_assignment(prepare_assignment(appointment_id, doctor_id, starts_at))
