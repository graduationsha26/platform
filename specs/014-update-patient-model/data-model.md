# Data Model: Update Patient Model

**Feature**: 014-update-patient-model | **Date**: 2026-02-18

---

## Entities

### Patient (Modified)

Represents a clinical record for a person being monitored on the TremoAI platform. Patients do not have login accounts — they are data-only records managed by doctors.

**File**: `backend/patients/models.py`

#### Fields After Change

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | AutoField | auto | Primary key |
| `full_name` | CharField(200) | Yes | Patient's full name |
| `date_of_birth` | DateField | Yes | Must not be in the future |
| `contact_phone` | CharField(20) | No | Validated phone format; covers "phone" requirement |
| `contact_email` | EmailField | No | Patient contact email |
| `medical_notes` | TextField | No | Free-form clinical observations; covers "notes" requirement |
| `created_by` | FK → CustomUser | Yes | Doctor who created the record; protected on delete |
| `created_at` | DateTimeField | auto | Record creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification timestamp |

#### Fields Removed

| Field | Type | Reason |
|-------|------|--------|
| `user` | OneToOneField → CustomUser | Linked to patient-role users, which no longer exist after E-1.1 |

#### Validation Rules
- `date_of_birth` must not be in the future (enforced in `clean()`)
- `contact_phone` must match regex `^\+?1?\d{9,15}$` if provided
- `full_name` is required and must be non-empty
- `created_by` must reference a valid CustomUser

#### Relationships After Change
- `created_by` → `CustomUser` (ForeignKey, PROTECT) — the doctor who created the patient record
- `doctor_assignments` ← `DoctorPatientAssignment` (reverse FK) — many-to-many assignment relationship

---

### DoctorPatientAssignment (Unchanged)

Many-to-many junction table linking doctors to the patients they manage. Unchanged by this feature.

**File**: `backend/patients/models.py`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | AutoField | auto | Primary key |
| `doctor` | FK → CustomUser | Yes | Must have role='doctor'; CASCADE on delete |
| `patient` | FK → Patient | Yes | The patient being assigned; CASCADE on delete |
| `assigned_at` | DateTimeField | auto | Timestamp of assignment |
| `assigned_by` | FK → CustomUser | No | Who made the assignment; SET_NULL on delete |

**Constraint**: `(doctor, patient)` pair must be unique — no duplicate assignments.

---

## Migration

**New Migration**: `backend/patients/migrations/0002_remove_patient_user.py`

- Operation: `RemoveField(model_name='patient', name='user')`
- Effect: Drops the `user_id` column from the `patients` database table
- Safety: Field is nullable (`null=True`) — no data migration needed; all other patient data preserved

---

## Affected Code (Non-Model)

These files reference the removed `Patient.user` field and must be updated:

| File | Change Required |
|------|----------------|
| `backend/analytics/services/report_generator.py:122` | Replace `patient.user.first_name` + `patient.user.last_name` with `patient.full_name` |
| `backend/authentication/permissions.py:43` | Remove `obj.patient.user == request.user` condition from `IsOwnerOrDoctor` |
| `backend/biometrics/views.py:47–55` | Remove dead `if user.role == 'patient': user.patient_profile` branch |
| `backend/biometrics/views.py:175–186` | Remove dead `if user.role == 'patient': user.patient_profile.id` branch |
