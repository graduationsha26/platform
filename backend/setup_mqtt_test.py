#!/usr/bin/env python
"""
One-time setup: create test doctor, patient, and register GLOVE001A.

Run once before starting the MQTT subscriber:
    python setup_mqtt_test.py
"""
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tremoai_backend.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from authentication.models import CustomUser
from patients.models import Patient, DoctorPatientAssignment
from devices.models import Device

# ── Doctor ─────────────────────────────────────────────────────────────────────
doctor, created = CustomUser.objects.get_or_create(
    email='doctor@test.com',
    defaults={
        'password': make_password('doctor123'),
        'first_name': 'Dr. John',
        'last_name': 'Smith',
        'role': 'doctor',
        'is_active': True,
        'is_staff': True,
    }
)
print(f'Doctor {"created" if created else "found"}: {doctor.email} (ID: {doctor.id})')

# ── Patient ─────────────────────────────────────────────────────────────────────
patient, created = Patient.objects.get_or_create(
    full_name='Ziyad Ashraf',
    defaults={
        'date_of_birth': date(1990, 1, 1),
        'contact_email': 'ziyad@test.com',
        'medical_notes': 'Test patient for GLOVE001A MQTT ingestion.',
        'created_by': doctor,
    }
)
print(f'Patient {"created" if created else "found"}: {patient.full_name} (ID: {patient.id})')

# ── Doctor-Patient Assignment ──────────────────────────────────────────────────
assignment, created = DoctorPatientAssignment.objects.get_or_create(
    doctor=doctor,
    patient=patient,
    defaults={'assigned_by': doctor}
)
print(f'Assignment {"created" if created else "found"} (ID: {assignment.id})')

# ── Device ─────────────────────────────────────────────────────────────────────
device, created = Device.objects.get_or_create(
    serial_number='GLOVE001A',
    defaults={
        'patient': patient,
        'registered_by': doctor,
        'status': 'online',
    }
)
if not created and device.patient != patient:
    device.patient = patient
    device.save(update_fields=['patient'])
    print(f'Device re-paired to patient {patient.id}')
else:
    print(f'Device {"created" if created else "found"}: {device.serial_number} -> patient {device.patient_id}')

print('\nSetup complete.')
print(f'  Doctor:   doctor@test.com / doctor123')
print(f'  Patient:  {patient.full_name} (ID: {patient.id})')
print(f'  Device:   GLOVE001A → patient {patient.id}')
