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

# Create admin user
admin, created = CustomUser.objects.get_or_create(
    email='admin@test.com',
    defaults={
        'password': make_password('admin123'),
        'first_name': 'Admin',
        'last_name': 'Manager',
        'role': 'admin',
        'is_active': True,
        'is_staff': True
    }
)
print(f'Admin {"created" if created else "found"}: {admin.email} (ID: {admin.id})')

# Patient data: (contact_email, full_name, dob, phone, notes)
patients_data = [
    (
        'jane.doe@patient.com', 'Jane Doe',
        date(1970, 5, 15), '+1234567890',
        'Diagnosed with Parkinsons Disease in 2020. Currently on Levodopa treatment.'
    ),
    (
        'robert.johnson@patient.com', 'Robert Johnson',
        date(1955, 3, 22), '+1987654321',
        'Stage 2 Parkinsons. Tremor predominantly in right hand. On Carbidopa-Levodopa.'
    ),
    (
        'margaret.williams@patient.com', 'Margaret Williams',
        date(1948, 11, 8), '+1122334455',
        'Early-onset Parkinsons diagnosed 2018. Bilateral tremor. Uses deep brain stimulation.'
    ),
    (
        'david.brown@patient.com', 'David Brown',
        date(1963, 7, 30), '+1555666777',
        'Stage 3 Parkinsons. History of falls. Physical therapy twice weekly.'
    ),
    (
        'linda.garcia@patient.com', 'Linda Garcia',
        date(1958, 1, 14), '+1444555666',
        'Mild Parkinsons symptoms. Managing well with medication. Annual follow-up scheduled.'
    ),
]

created_patients = []

for email, full_name, dob, phone, notes in patients_data:
    patient, created = Patient.objects.get_or_create(
        contact_email=email,
        defaults={
            'full_name': full_name,
            'date_of_birth': dob,
            'contact_phone': phone,
            'medical_notes': notes,
            'created_by': doctor
        }
    )
    print(f'Patient {"created" if created else "found"}: {patient.full_name} (ID: {patient.id})')

    assignment, created = DoctorPatientAssignment.objects.get_or_create(
        doctor=doctor,
        patient=patient,
        defaults={'assigned_by': doctor}
    )
    print(f'  Assignment {"created" if created else "found"} (ID: {assignment.id})')
    created_patients.append(patient)

print('\nTest users created successfully!')
print(f'Doctor: doctor@test.com / doctor123')
print(f'Admin:  admin@test.com  / admin123')
print(f'\nPatients ({len(created_patients)}):')
for p in created_patients:
    print(f'  [{p.id}] {p.full_name} <{p.contact_email}>')
