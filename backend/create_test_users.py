#!/usr/bin/env python
"""Create test users for analytics testing."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tremoai_backend.settings')
django.setup()

from authentication.models import CustomUser
from patients.models import Patient, DoctorPatientAssignment
from datetime import date
from django.contrib.auth.hashers import make_password

# Create doctor user
doctor, created = CustomUser.objects.get_or_create(
    email='doctor@test.com',
    defaults={
        'password': make_password('doctor123'),
        'first_name': 'Dr. John',
        'last_name': 'Smith',
        'role': 'doctor',
        'is_active': True,
        'is_staff': True
    }
)
print(f'Doctor {"created" if created else "found"}: {doctor.email} (ID: {doctor.id})')

# Create patient user
patient_user, created = CustomUser.objects.get_or_create(
    email='patient@test.com',
    defaults={
        'password': make_password('patient123'),
        'first_name': 'Jane',
        'last_name': 'Doe',
        'role': 'patient',
        'is_active': True
    }
)
print(f'Patient user {"created" if created else "found"}: {patient_user.email} (ID: {patient_user.id})')

# Create patient profile
patient, created = Patient.objects.get_or_create(
    user=patient_user,
    defaults={
        'full_name': 'Jane Doe',
        'date_of_birth': date(1970, 5, 15),
        'contact_phone': '+1234567890',
        'contact_email': 'patient@test.com',
        'medical_notes': 'Diagnosed with Parkinsons Disease in 2020. Currently on Levodopa treatment.',
        'created_by': doctor
    }
)
print(f'Patient profile {"created" if created else "found"}: {patient.full_name} (ID: {patient.id})')

# Assign doctor to patient
assignment, created = DoctorPatientAssignment.objects.get_or_create(
    doctor=doctor,
    patient=patient,
    defaults={
        'assigned_by': doctor
    }
)
print(f'Doctor assignment {"created" if created else "found"} (ID: {assignment.id})')

print('\nTest users created successfully!')
print(f'Doctor: doctor@test.com / doctor123')
print(f'Patient: patient@test.com / patient123')
print(f'Patient ID: {patient.id}')
