from apps.consultations.models import Consultation

from .models import Appointment


def complete_appointment(appointment):
    """Mark a locked, confirmed appointment and its consultation completed and notify the patient. Returns False if already done."""
    from apps.notifications.models import Notification
    from apps.notifications.service import notify_appointment

    if appointment.status == Appointment.Status.COMPLETED:
        return False
    appointment.save(update_fields=appointment.set_status(Appointment.Status.COMPLETED))
    consultation = appointment.consultation
    if consultation.status != Consultation.Status.COMPLETED:
        consultation.status = Consultation.Status.COMPLETED
        consultation.save(update_fields=['status'])
    notify_appointment(appointment, Notification.Kind.CONSULTATION_COMPLETED)
    return True
