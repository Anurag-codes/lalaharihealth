from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment, notify_doctor
from apps.payments.models import Payment
from .availability import booking_time_error
from .models import Appointment, AppointmentSlot

FREED_STATUSES = (Appointment.Status.CANCELLED, Appointment.Status.COMPLETED)


def assignment_doctors(consultation):
    return DoctorProfile.objects.filter(
        is_active=True, user__is_active=True, user__role='doctor', verification_status='verified',
        speciality_id=consultation.speciality_id,
    )


@dataclass
class AssignmentPlan:
    appointment: Appointment
    profile: DoctorProfile
    starts_at: datetime
    slot: AppointmentSlot | None


def prepare_assignment(appointment_id, doctor_id, starts_at=None):
    """Validate and lock an assignment inside the caller's transaction without saving changes."""
    snapshot = get_object_or_404(Appointment.objects.only('consultation_id', 'status'), pk=appointment_id)
    if snapshot.status != Appointment.Status.FINDING_DOCTOR:
        raise ValidationError('Only paid appointments awaiting matching can be assigned.')
    # Match clinical-record completion's consultation -> appointment lock order.
    consultation = get_object_or_404(Consultation.objects.select_for_update(), pk=snapshot.consultation_id)
    appointment = get_object_or_404(
        Appointment.objects.select_for_update(of=('self',)).select_related('patient'), pk=appointment_id,
    )
    if appointment.status != Appointment.Status.FINDING_DOCTOR:
        raise ValidationError('Only paid appointments awaiting matching can be assigned.')
    if not Payment.objects.filter(consultation=consultation, status=Payment.Status.SUCCESS).exists():
        raise ValidationError('Confirmed payment is required.')
    if starts_at is not None:
        error = booking_time_error(starts_at)
        if error:
            raise ValidationError({'starts_at': error})
    target_time = starts_at if starts_at is not None else appointment.slot_time
    profile = get_object_or_404(
        assignment_doctors(consultation).select_for_update().select_related('user'), user_id=doctor_id,
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
    appointment.consultation = consultation
    return AssignmentPlan(appointment, profile, target_time, slot)


def apply_assignment(plan):
    """Save a previously validated, still-locked plan inside the caller's transaction."""
    appointment = plan.appointment
    changed_time = appointment.slot_time != plan.starts_at
    appointment.doctor, appointment.slot, appointment.slot_time = plan.profile.user, plan.slot, plan.starts_at
    update_fields = ['doctor', 'slot', 'slot_time'] + appointment.set_status(Appointment.Status.CONFIRMED)
    if changed_time:
        appointment.reminder_sent_at = None
        update_fields.append('reminder_sent_at')
    appointment.save(update_fields=update_fields)
    consultation = appointment.consultation
    consultation.doctor, consultation.scheduled_at = plan.profile.user, plan.starts_at
    consultation.save(update_fields=['doctor', 'scheduled_at'])
    notify_appointment(appointment, Notification.Kind.DOCTOR_ASSIGNED)
    notify_doctor(appointment, Notification.Kind.APPOINTMENT_ASSIGNED)
    return appointment


def assign_doctor(appointment_id, doctor_id, starts_at=None):
    with transaction.atomic():
        return apply_assignment(prepare_assignment(appointment_id, doctor_id, starts_at))
