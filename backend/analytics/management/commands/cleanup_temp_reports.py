"""
Django Management Command: Cleanup Temporary Reports

Feature 003: Analytics and Reporting
Deletes temporary PDF reports older than 24 hours.

Usage:
    python manage.py cleanup_temp_reports

Schedule:
    Run this command daily via cron or system scheduler.
    Example cron: 0 2 * * * cd /path/to/project && python manage.py cleanup_temp_reports
"""

import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Delete temporary PDF reports older than 24 hours'

    def add_arguments(self, parser):
        """
        Add command-line arguments.
        """
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete files older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        """
        T035-T036: Execute cleanup logic.

        Deletes PDF files in media/reports/ directory that are older
        than the specified number of hours (default 24).
        """
        hours_threshold = options['hours']
        dry_run = options['dry_run']

        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')

        # Check if reports directory exists
        if not os.path.exists(reports_dir):
            self.stdout.write(self.style.WARNING(
                f'Reports directory does not exist: {reports_dir}'
            ))
            return

        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=hours_threshold)
        cutoff_timestamp = cutoff_time.timestamp()

        self.stdout.write(
            f'Scanning for PDF reports older than {hours_threshold} hours '
            f'(before {cutoff_time.strftime("%Y-%m-%d %H:%M:%S")})'
        )

        # Scan directory for old PDF files
        deleted_count = 0
        total_size_mb = 0

        for filename in os.listdir(reports_dir):
            filepath = os.path.join(reports_dir, filename)

            # Only process PDF files
            if not filename.endswith('.pdf'):
                continue

            # Check file modification time
            try:
                file_mtime = os.path.getmtime(filepath)

                if file_mtime < cutoff_timestamp:
                    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    total_size_mb += file_size_mb

                    if dry_run:
                        self.stdout.write(
                            f'[DRY RUN] Would delete: {filename} '
                            f'({file_size_mb:.2f} MB, '
                            f'modified: {datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")})'
                        )
                    else:
                        os.remove(filepath)
                        self.stdout.write(self.style.SUCCESS(
                            f'Deleted: {filename} ({file_size_mb:.2f} MB)'
                        ))

                    deleted_count += 1

            except OSError as e:
                self.stdout.write(self.style.ERROR(
                    f'Error processing {filename}: {str(e)}'
                ))

        # Summary
        if deleted_count > 0:
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'\n[DRY RUN] Would delete {deleted_count} file(s), '
                    f'freeing {total_size_mb:.2f} MB'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'\n[OK] Deleted {deleted_count} file(s), '
                    f'freed {total_size_mb:.2f} MB'
                ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n[OK] No old reports to delete'
            ))
