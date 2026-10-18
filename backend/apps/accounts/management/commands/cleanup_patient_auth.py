from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import AuthRateLimit, EmailOtpChallenge, UsedFirebaseToken


class Command(BaseCommand):
    help = 'Remove expired email OTP records older than one day, expired Firebase replay records and stale rate buckets.'

    def handle(self, *args, **options):
        now = timezone.now()
        challenges, _ = EmailOtpChallenge.objects.filter(expires_at__lt=now - timedelta(days=1)).delete()
        tokens, _ = UsedFirebaseToken.objects.filter(expires_at__lt=now).delete()
        buckets, _ = AuthRateLimit.objects.filter(window_start__lt=now - timedelta(hours=2)).delete()
        self.stdout.write(f'Removed {challenges} OTP records, {tokens} expired token records and {buckets} stale rate buckets.')
