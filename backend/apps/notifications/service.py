"""Create inbox notifications for booking events and deliver them by push (Firebase Cloud Messaging)."""
import logging
import threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone

from .models import Announcement, DeviceToken, Notification

logger = logging.getLogger(__name__)
Kind = Notification.Kind

MESSAGES = {
    Kind.PAYMENT_SUCCESS: {
        'en': ('Payment successful', 'We received {amount} for {number}. We are finding a doctor for you and will notify you soon.'),
        'hi': ('भुगतान सफल', '{number} के लिए {amount} का भुगतान मिल गया है। हम आपके लिए डॉक्टर ढूंढ रहे हैं और जल्द ही सूचित करेंगे।'),
    },
    Kind.DOCTOR_ASSIGNED: {
        'en': ('Appointment confirmed', '{doctor} will consult {patient} on {date} at {time}.'),
        'hi': ('अपॉइंटमेंट कन्फर्म', '{doctor} {date} को {time} बजे {patient} से परामर्श करेंगे।'),
    },
    Kind.APPOINTMENT_REMINDER: {
        'en': ('Appointment reminder', 'Your {title} with {doctor} starts at {time}. Please keep your phone ready.'),
        'hi': ('अपॉइंटमेंट रिमाइंडर', '{doctor} के साथ आपका परामर्श {time} बजे शुरू होगा। कृपया अपना फ़ोन तैयार रखें।'),
    },
    Kind.CONSULTATION_COMPLETED: {
        'en': ('Prescription ready', 'Your consultation with {doctor} is complete. View the prescription in Medical Records.'),
        'hi': ('प्रिस्क्रिप्शन तैयार', '{doctor} के साथ आपका परामर्श पूरा हुआ। प्रिस्क्रिप्शन मेडिकल रिकॉर्ड्स में देखें।'),
    },
    Kind.APPOINTMENT_CANCELLED: {
        'en': ('Appointment cancelled', 'Your appointment {number} on {date} at {time} has been cancelled.'),
        'hi': ('अपॉइंटमेंट रद्द', '{date} को {time} बजे का आपका अपॉइंटमेंट {number} रद्द कर दिया गया है।'),
    },
}


def money(amount, currency):
    from apps.pricing.models import CountryPricing
    from apps.pricing.service import format_amount

    symbol = CountryPricing.objects.filter(currency=currency).values_list('currency_symbol', flat=True).first()
    return format_amount(amount, symbol or ('\u20b9' if currency == 'INR' else f'{currency} '.strip()))


def user_language(user):
    profile = getattr(user, 'patient_profile', None)
    return 'hi' if profile is not None and profile.preferred_language == 'hi' else 'en'


def doctor_display_name(doctor):
    if doctor is None:
        return 'your doctor'
    return f'Dr. {doctor.get_full_name() or doctor.username}'


def notify_appointment(appointment, kind):
    """Add an inbox item for the patient of this appointment and queue a push. Call inside the transaction."""
    from apps.appointments.availability import display_date, display_time

    patient = appointment.patient
    consultation = appointment.consultation
    title, body = MESSAGES[kind][user_language(patient)]
    values = {
        'amount': money(consultation.fee_charged, consultation.currency), 'number': f'APT-{appointment.pk:05d}',
        'doctor': doctor_display_name(appointment.doctor), 'patient': consultation.patient_name or 'you',
        'date': display_date(appointment.slot_time), 'time': display_time(appointment.slot_time),
        'title': consultation.title,
    }
    notification = Notification.objects.create(
        user=patient, kind=kind, title=title, body=body.format(**values),
        appointment=appointment, consultation=consultation,
    )
    queue_push([notification.pk])
    return notification


def send_announcement(announcement):
    """Deliver an announcement once to every active user of its audience."""
    with transaction.atomic():
        announcement = Announcement.objects.select_for_update().get(pk=announcement.pk)
        if announcement.sent_at:
            return 0
        users = get_user_model().objects.filter(is_active=True)
        if announcement.audience == Announcement.Audience.PATIENTS:
            users = users.filter(role='patient')
        elif announcement.audience == Announcement.Audience.DOCTORS:
            users = users.filter(role='doctor')
        hindi = set(users.filter(patient_profile__preferred_language='hi').values_list('pk', flat=True))
        rows = []
        for user_id in users.values_list('pk', flat=True):
            use_hindi = user_id in hindi and announcement.title_hi
            rows.append(Notification(
                user_id=user_id, kind=Kind.ANNOUNCEMENT, announcement=announcement,
                title=announcement.title_hi if use_hindi else announcement.title,
                body=(announcement.body_hi or announcement.body) if use_hindi else announcement.body,
            ))
        Notification.objects.bulk_create(rows, batch_size=500)
        announcement.sent_at = timezone.now()
        announcement.recipient_count = len(rows)
        announcement.save(update_fields=['sent_at', 'recipient_count'])
        ids = list(Notification.objects.filter(announcement=announcement).values_list('pk', flat=True))
        queue_push(ids)
    return len(rows)


def queue_push(notification_ids):
    if not notification_ids or not settings.PUSH_NOTIFICATIONS_ENABLED or not settings.FIREBASE_PROJECT_ID:
        return
    transaction.on_commit(lambda: threading.Thread(target=deliver_push, args=(list(notification_ids),), daemon=True).start())


def deliver_push(notification_ids):
    """Send FCM messages for these notifications. Failures are logged; the inbox item always remains."""
    from firebase_admin import messaging

    from apps.accounts.firebase import AuthServiceUnavailable, firebase_app

    try:
        app = firebase_app()
    except AuthServiceUnavailable:
        logger.warning('Push skipped: Firebase is not configured.')
        return
    try:
        notifications = Notification.objects.filter(pk__in=notification_ids).only(
            'id', 'user_id', 'kind', 'title', 'body', 'appointment_id', 'consultation_id',
        )
        for notification in notifications.iterator():
            tokens = list(DeviceToken.objects.filter(user_id=notification.user_id, is_active=True).values_list('token', flat=True))
            if not tokens:
                continue
            data = {
                'notification_id': str(notification.pk), 'kind': notification.kind,
                'appointment_id': str(notification.appointment_id or ''), 'consultation_id': str(notification.consultation_id or ''),
            }
            message = messaging.MulticastMessage(
                tokens=tokens, data=data,
                notification=messaging.Notification(title=notification.title, body=notification.body),
            )
            try:
                result = messaging.send_each_for_multicast(message, app=app)
            except Exception:  # noqa: BLE001 - never let push failures surface to booking/payment callers
                logger.exception('Push delivery failed for notification %s.', notification.pk)
                continue
            stale = [
                token for token, response in zip(tokens, result.responses)
                if isinstance(response.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError))
            ]
            if stale:
                DeviceToken.objects.filter(token__in=stale).update(is_active=False)
    finally:
        # Runs in its own thread, so release that thread's database connection.
        connection.close()
