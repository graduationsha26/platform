#!/usr/bin/env python
"""Create sample biometric sessions for analytics testing."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tremoai_backend.settings')
django.setup()

from biometrics.models import BiometricSession
from patients.models import Patient
from devices.models import Device
from authentication.models import CustomUser
from django.utils import timezone
from datetime import timedelta
import random

# Get test patient and doctor
patient = Patient.objects.get(id=1)
doctor = CustomUser.objects.get(email='doctor@test.com')
print(f'Creating sample data for patient: {patient.full_name} (ID: {patient.id})')

# Create or get a test device
device, created = Device.objects.get_or_create(
    serial_number='GLV00001',  # 8 chars, alphanumeric uppercase
    defaults={
        'patient': patient,
        'status': 'online',  # Valid status choices: 'online' or 'offline'
        'registered_by': doctor  # Must be doctor role
    }
)
print(f'Device {"created" if created else "found"}: {device.serial_number} (ID: {device.id})')

# Create 15 sample sessions over the past 10 days
print('\nCreating biometric sessions...')
base_date = timezone.now() - timedelta(days=10)

for i in range(15):
    # Distribute sessions across 10 days
    session_date = base_date + timedelta(days=i * 10 / 15, hours=random.randint(8, 18))

    # Simulate improving tremor over time (amplitude decreases)
    base_amplitude = 0.55 - (i * 0.015)  # Start at 0.55, decrease to ~0.33
    tremor_intensities = [
        round(base_amplitude + random.uniform(-0.05, 0.05), 2)
        for _ in range(10)
    ]

    # Frequency stays relatively stable around 4-5 Hz
    frequency = round(4.2 + random.uniform(-0.3, 0.8), 1)

    # ML prediction based on current amplitude
    if base_amplitude > 0.5:
        severity = 'severe'
    elif base_amplitude > 0.4:
        severity = 'moderate'
    else:
        severity = 'mild'

    session = BiometricSession.objects.create(
        patient=patient,
        device=device,
        session_start=session_date,
        session_duration=timedelta(minutes=random.randint(10, 20)),
        sensor_data={
            'tremor_intensity': tremor_intensities,
            'frequency': frequency,
            'timestamps': [session_date.isoformat() for _ in range(10)]
        },
        ml_prediction={
            'severity': severity,
            'confidence': round(random.uniform(0.75, 0.95), 2)
        },
        ml_predicted_at=session_date + timedelta(seconds=5),
        received_via_mqtt=True
    )
    print(f'  Session {i+1}: {session.session_start.strftime("%Y-%m-%d %H:%M")} - Amplitude: {base_amplitude:.2f}, Severity: {severity}')

print(f'\nSuccessfully created {BiometricSession.objects.filter(patient=patient).count()} sessions for patient {patient.id}')
print('Sample data ready for analytics testing!')
