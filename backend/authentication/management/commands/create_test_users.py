"""
Django management command to create test users for development.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import CustomUser


class Command(BaseCommand):
    """Create test doctor and patient users for development."""

    help = 'Creates test users (1 doctor, 1 patient) for development and testing'

    def handle(self, *args, **options):
        """Execute the command."""
        try:
            with transaction.atomic():
                # Create test doctor
                doctor_email = 'doctor@test.com'
                if not CustomUser.objects.filter(email=doctor_email).exists():
                    doctor = CustomUser.objects.create_user(
                        email=doctor_email,
                        password='doctor123',
                        first_name='John',
                        last_name='Doe',
                        role='doctor'
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] Created test doctor: {doctor_email} (password: doctor123)'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'[WARN] Doctor already exists: {doctor_email}')
                    )

                # Create test patient
                patient_email = 'patient@test.com'
                if not CustomUser.objects.filter(email=patient_email).exists():
                    patient = CustomUser.objects.create_user(
                        email=patient_email,
                        password='patient123',
                        first_name='Jane',
                        last_name='Smith',
                        role='patient'
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] Created test patient: {patient_email} (password: patient123)'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'[WARN] Patient already exists: {patient_email}')
                    )

                self.stdout.write(
                    self.style.SUCCESS('\n[OK] Test users created successfully!')
                )
                self.stdout.write('\nTest Credentials:')
                self.stdout.write('  Doctor:  doctor@test.com  / doctor123')
                self.stdout.write('  Patient: patient@test.com / patient123')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error creating test users: {str(e)}')
            )
            raise
