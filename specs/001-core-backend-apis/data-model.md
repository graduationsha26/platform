# Data Model: Core Backend APIs

**Feature**: 001-core-backend-apis
**Date**: 2026-02-15
**Database**: Supabase PostgreSQL
**ORM**: Django 5.x ORM

## Overview

This document defines the Django models for the Core Backend APIs feature. All models map to PostgreSQL tables via Django ORM and follow Django conventions for field types, relationships, and constraints.

## Entity Relationship Diagram

```
CustomUser (extends AbstractUser)
    ├── role: 'doctor' | 'patient'
    └── created_at, updated_at

Doctor (CustomUser with role='doctor')
    └── assigned_patients (M2M via DoctorPatientAssignment)

Patient (CustomUser with role='patient')
    ├── full_name, date_of_birth, contact_info, medical_notes
    ├── assigned_doctors (M2M via DoctorPatientAssignment)
    ├── paired_device (1-to-1 via Device FK)
    └── biometric_sessions (1-to-M)

DoctorPatientAssignment
    ├── doctor (FK → CustomUser where role='doctor')
    ├── patient (FK → Patient)
    └── assigned_at

Device
    ├── serial_number (unique)
    ├── status: 'online' | 'offline'
    ├── last_seen
    ├── patient (FK → Patient, nullable)
    └── registered_at

BiometricSession
    ├── patient (FK → Patient)
    ├── device (FK → Device)
    ├── session_start, session_duration
    ├── sensor_data (JSONField)
    └── created_at
```

## Models

### 1. CustomUser (authentication app)

Extends Django's AbstractUser to add role-based authentication.

**Purpose**: Represent platform users (doctors and patients) with role-based access control

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Django auto-generated primary key |
| email | EmailField | UNIQUE, NOT NULL | User email (used for login) |
| password | CharField | NOT NULL | Hashed password (Django AbstractUser) |
| first_name | CharField(150) | NOT NULL | User first name (Django AbstractUser) |
| last_name | CharField(150) | NOT NULL | User last name (Django AbstractUser) |
| role | CharField(10) | CHOICES, NOT NULL | User role: 'doctor' or 'patient' |
| is_active | BooleanField | DEFAULT True | Account active status (Django AbstractUser) |
| date_joined | DateTimeField | AUTO_NOW_ADD | Account creation timestamp (Django AbstractUser) |
| last_login | DateTimeField | NULLABLE | Last login timestamp (Django AbstractUser) |

**Relationships**:
- **Patients assigned to (if doctor)**: Many-to-Many with Patient via DoctorPatientAssignment
- **Assigned doctors (if patient)**: Many-to-Many with Doctor via DoctorPatientAssignment

**Validation Rules**:
- `email` must be valid email format (Django EmailField validation)
- `email` must be unique across all users
- `password` must be hashed before storage (Django password hashers)
- `role` must be exactly 'doctor' or 'patient' (CHOICES enforcement)

**Django Model**:
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]

    username = None  # Remove username field
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    USERNAME_FIELD = 'email'  # Use email for login instead of username
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
```

---

### 2. Patient (patients app)

Stores patient profile information and medical notes.

**Purpose**: Represent patients being monitored with the TremoAI platform

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Patient unique identifier |
| user | OneToOneField | FK → CustomUser, NULLABLE | Link to user account (if patient has login) |
| full_name | CharField(200) | NOT NULL | Patient full name |
| date_of_birth | DateField | NOT NULL | Patient date of birth (for age calculation) |
| contact_phone | CharField(20) | NULLABLE | Patient contact phone number |
| contact_email | EmailField | NULLABLE | Patient contact email |
| medical_notes | TextField | NULLABLE | Doctor's notes about patient condition |
| created_by | ForeignKey | FK → CustomUser(doctor) | Doctor who created patient record |
| created_at | DateTimeField | AUTO_NOW_ADD | Record creation timestamp |
| updated_at | DateTimeField | AUTO_NOW | Record last update timestamp |

**Relationships**:
- **User Account**: One-to-One with CustomUser (patient role) - optional, patient may not have login
- **Created By**: Foreign Key to CustomUser (doctor role)
- **Assigned Doctors**: Many-to-Many with CustomUser (doctor role) via DoctorPatientAssignment
- **Paired Device**: One-to-One with Device (via device.patient FK)
- **Biometric Sessions**: One-to-Many with BiometricSession

**Validation Rules**:
- `full_name` required, max 200 characters
- `date_of_birth` required, cannot be future date
- `contact_phone` optional, format validation if provided
- `contact_email` optional, email format validation if provided
- `created_by` must be a user with role='doctor'

**Django Model**:
```python
from django.db import models
from django.core.validators import RegexValidator

class Patient(models.Model):
    user = models.OneToOneField('authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile')
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    contact_phone = models.CharField(max_length=20, blank=True, validators=[RegexValidator(r'^\+?1?\d{9,15}$')])
    contact_email = models.EmailField(blank=True)
    medical_notes = models.TextField(blank=True)
    created_by = models.ForeignKey('authentication.CustomUser', on_delete=models.PROTECT, related_name='created_patients')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patients'
        ordering = ['-created_at']
```

---

### 3. DoctorPatientAssignment (patients app)

Many-to-many relationship between doctors and patients for access control.

**Purpose**: Track which doctors are assigned to monitor which patients

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Assignment unique identifier |
| doctor | ForeignKey | FK → CustomUser(doctor), NOT NULL | Doctor assigned to patient |
| patient | ForeignKey | FK → Patient, NOT NULL | Patient assigned to doctor |
| assigned_at | DateTimeField | AUTO_NOW_ADD | Assignment timestamp |
| assigned_by | ForeignKey | FK → CustomUser(doctor), NULLABLE | Doctor who made the assignment |

**Relationships**:
- **Doctor**: Foreign Key to CustomUser (role='doctor')
- **Patient**: Foreign Key to Patient
- **Assigned By**: Foreign Key to CustomUser (role='doctor') - tracks who made assignment

**Validation Rules**:
- `doctor` must have role='doctor'
- Unique constraint on (doctor, patient) - prevent duplicate assignments
- Cannot assign patient to themselves if patient has user account

**Django Model**:
```python
class DoctorPatientAssignment(models.Model):
    doctor = models.ForeignKey('authentication.CustomUser', on_delete=models.CASCADE, related_name='patient_assignments')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='doctor_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey('authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments_made')

    class Meta:
        db_table = 'doctor_patient_assignments'
        unique_together = [['doctor', 'patient']]
        ordering = ['-assigned_at']
```

---

### 4. Device (devices app)

Represents physical glove hardware devices.

**Purpose**: Track registered glove devices, their pairing status, and online/offline state

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Device unique identifier |
| serial_number | CharField(50) | UNIQUE, NOT NULL | Hardware serial number from manufacturer |
| status | CharField(10) | CHOICES, DEFAULT 'offline' | Device connection status |
| last_seen | DateTimeField | NULLABLE | Last time device was online |
| patient | ForeignKey | FK → Patient, NULLABLE | Patient this device is paired to |
| registered_by | ForeignKey | FK → CustomUser(doctor) | Doctor who registered device |
| registered_at | DateTimeField | AUTO_NOW_ADD | Registration timestamp |

**Relationships**:
- **Patient**: Foreign Key to Patient (nullable - device may be registered but not paired)
- **Registered By**: Foreign Key to CustomUser (doctor role)
- **Biometric Sessions**: One-to-Many with BiometricSession

**Validation Rules**:
- `serial_number` must be unique across all devices
- `serial_number` format: alphanumeric, 8-20 characters
- `status` must be 'online' or 'offline' (CHOICES enforcement)
- `patient` nullable - allows device registration before pairing
- Cannot pair device to multiple patients simultaneously (enforced at model level)

**State Transitions**:
- Registered → offline (default state)
- offline → online (device connects)
- online → offline (device disconnects or timeout)

**Django Model**:
```python
class Device(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    serial_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(null=True, blank=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    registered_by = models.ForeignKey('authentication.CustomUser', on_delete=models.PROTECT, related_name='registered_devices')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'devices'
        ordering = ['-registered_at']
```

---

### 5. BiometricSession (biometrics app)

Stores sensor data recording sessions from glove devices.

**Purpose**: Store tremor sensor measurements collected during recording sessions

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Session unique identifier |
| patient | ForeignKey | FK → Patient, NOT NULL | Patient this data belongs to |
| device | ForeignKey | FK → Device, NOT NULL | Device that collected this data |
| session_start | DateTimeField | NOT NULL | Session recording start time |
| session_duration | DurationField | NOT NULL | Total session duration |
| sensor_data | JSONField | NOT NULL | Sensor measurements (JSON format) |
| created_at | DateTimeField | AUTO_NOW_ADD | Record creation timestamp |

**Relationships**:
- **Patient**: Foreign Key to Patient
- **Device**: Foreign Key to Device

**sensor_data JSON Structure**:
```json
{
  "tremor_intensity": [0.5, 0.7, 0.6, 0.8, ...],  // Array of tremor intensity values (0-1 scale)
  "timestamps": [0, 20, 40, 60, ...],             // Milliseconds from session_start
  "frequency": 50,                                 // Sampling frequency (Hz)
  "metadata": {
    "firmware_version": "1.2.3",
    "battery_level": 85
  }
}
```

**Validation Rules**:
- `patient` and `device` must both be set
- `device.patient` must equal `patient` (enforced in serializer)
- `session_start` cannot be in future
- `session_duration` must be positive
- `sensor_data` must be valid JSON with required keys: tremor_intensity, timestamps, frequency

**Aggregation Support**:
- Average tremor intensity: `AVG(sensor_data->>'tremor_intensity')`
- Session count: `COUNT(*)`
- Total duration: `SUM(session_duration)`

**Django Model**:
```python
class BiometricSession(models.Model):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='biometric_sessions')
    device = models.ForeignKey('devices.Device', on_delete=models.PROTECT, related_name='biometric_sessions')
    session_start = models.DateTimeField()
    session_duration = models.DurationField()
    sensor_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'biometric_sessions'
        ordering = ['-session_start']
        indexes = [
            models.Index(fields=['patient', 'session_start']),  # Fast date range queries
            models.Index(fields=['device', 'session_start']),
        ]
```

## Database Indexes

Performance-critical indexes beyond Django defaults:

- `biometric_sessions`: Composite index on (patient_id, session_start) for date range queries
- `biometric_sessions`: Composite index on (device_id, session_start) for device-specific queries
- `patients`: Index on full_name for search performance (Django auto-creates for CharField)
- `devices`: Index on serial_number for lookup (Django auto-creates for unique fields)

## Migrations Strategy

1. Initial migration creates all tables
2. Populate CustomUser with two test users (doctor, patient) in data migration
3. No data migrations needed for other models (empty initially)
4. Future migrations will be created per app (authentication, patients, devices, biometrics)

## Data Integrity Rules

- **Cascading Deletes**:
  - Delete Patient → cascade delete BiometricSessions, DoctorPatientAssignments
  - Delete Device → protect (cannot delete if BiometricSessions exist)
  - Delete Doctor → protect (cannot delete if created_by or assigned to patients)

- **Soft Deletes** (Future Enhancement):
  - Not implemented in MVP
  - Consider adding `deleted_at` field for audit compliance

- **Constraints**:
  - Unique constraints: CustomUser.email, Device.serial_number
  - Unique together: (doctor, patient) in DoctorPatientAssignment
  - Check constraints: Future enhancement for sensor_data JSON schema validation

## Constitutional Compliance

✅ **Database Strategy**: Uses Supabase PostgreSQL (remote) via Django ORM
✅ **No local SQLite**: All models connect to Supabase via DATABASE_URL
✅ **Security-First**: No secrets in models (all in .env)
✅ **Data Isolation**: Role-based access enforced in views/permissions, not database-level
