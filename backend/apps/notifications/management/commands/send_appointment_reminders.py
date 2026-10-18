from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.notifications.models import Notification
from apps.notifications.service import notify_appointment


class Command(BaseCommand):
    help = 'Send "Appointment reminder" notifications for confirmed appointments starting soon. Run every 5 minutes.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=None, help='Look-ahead window (default APPOINTMENT_REMINDER_MINUTES)')

    def handle(self, *args, **options):
        minutes = options['minutes'] or settings.APPOINTMENT_REMINDER_MINUTES
        now = timezone.now()
        due = Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED, reminder_sent_at__isnull=True,
            slot_time__gt=now, slot_time__lte=now + timedelta(minutes=minutes),
        ).values_list('pk', flat=True)
        sent = 0
        for appointment_id in list(due):
            with transaction.atomic():
                appointment = Appointment.objects.select_for_update().select_related('consultation', 'patient', 'doctor').get(pk=appointment_id)
                if appointment.reminder_sent_at or appointment.status != Appointment.Status.CONFIRMED:
                    continue
                appointment.reminder_sent_at = timezone.now()
                appointment.save(update_fields=['reminder_sent_at'])
                notify_appointment(appointment, Notification.Kind.APPOINTMENT_REMINDER)
                sent += 1
        self.stdout.write(f'Sent {sent} appointment reminder(s).')
