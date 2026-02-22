"""
Management command to purge old MotorTelemetry rows.

Deletes telemetry records older than --days (default 30) in batches to avoid
long-running DELETE locks on the cmg_motor_telemetry table.

Usage:
    python manage.py purge_cmg_telemetry
    python manage.py purge_cmg_telemetry --days 7
    python manage.py purge_cmg_telemetry --days 30 --batch-size 5000

Feature 027: CMG Brushless Motor & ESC Initialization
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from cmg.models import MotorTelemetry


class Command(BaseCommand):
    help = 'Purge MotorTelemetry rows older than N days (default 30) in batches.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete telemetry older than this many days (default: 30).',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='Number of rows to delete per batch (default: 10000).',
        )

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(
            f'Purging MotorTelemetry rows older than {days} days '
            f'(before {cutoff.isoformat()}) in batches of {batch_size}...'
        )

        total_deleted = 0
        while True:
            # Fetch a batch of PKs to delete (avoids full-table DELETE scan)
            pks = list(
                MotorTelemetry.objects.filter(timestamp__lt=cutoff)
                .values_list('id', flat=True)[:batch_size]
            )
            if not pks:
                break

            deleted_count, _ = MotorTelemetry.objects.filter(id__in=pks).delete()
            total_deleted += deleted_count
            self.stdout.write(f'  Deleted {total_deleted} rows so far...')

        if total_deleted == 0:
            self.stdout.write(self.style.SUCCESS('No rows to purge.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Done. Purged {total_deleted} MotorTelemetry rows.')
            )
