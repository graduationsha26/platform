# Data Model: Patient Overview Grid

**Branch**: `045-patient-overview-grid` | **Phase**: 1 Design | **Date**: 2026-06-14

## No New Models

This feature reads existing entities. One existing model is modified (Patient) with an additive field.

---

## Modified Entity: Patient

**Model file**: `backend/patients/models.py`

### Change

Add one optional field:

| Field | Type | Constraints | Default | Notes |
|-------|------|-------------|---------|-------|
| `avatar_url` | URLField | max_length=500, blank=True | `''` (empty string) | URL to patient avatar photo; empty means use initials fallback |

### Migration

A Django migration is required. It is a purely additive change (new column with a default).

```
backend/patients/migrations/
  → new auto-generated migration file: 000X_patient_avatar_url.py
```

### After change — Patient field summary (relevant fields only)

| Field | Notes |
|-------|-------|
| `id` | Primary key |
| `full_name` | Single CharField (e.g., "Ahmed Karim Nour") |
| `avatar_url` | NEW — optional URL to photo |
| `doctor_assignments` | Reverse FK to DoctorPatientAssignment |
| `devices` | Reverse FK to Device |

---

## Read-Only Entity: Device

**Model file**: `backend/devices/models.py` — **no changes**

Fields read by this feature:

| Field | Type | Notes |
|-------|------|-------|
| `patient` | ForeignKey | Links device to a patient |
| `last_seen` | DateTimeField | Timestamp of last telemetry packet; null if never seen |

### device_online derivation

```
device_online = (
    patient has at least one Device where last_seen is not null
    AND last_seen >= timezone.now() - 60 seconds
)
```

Implemented via Django ORM annotation:
```python
.annotate(latest_device_seen=Max('devices__last_seen'))
```
Then: `device_online = latest_device_seen is not None and latest_device_seen >= threshold`

---

## Derived Read Model: PatientsOverviewItem (API response shape)

Not a database model — this is the shape returned by `GET /api/patients/overview/`.

| Field | Type | Source |
|-------|------|--------|
| `id` | integer | `Patient.id` |
| `full_name` | string | `Patient.full_name` |
| `avatar_url` | string (nullable) | `Patient.avatar_url` (empty string if no photo) |
| `device_online` | boolean | Computed: `Max(devices__last_seen) >= now - 60s` |

---

## Entity Relationships (relevant to this feature)

```
Doctor (CustomUser, role='doctor')
    │
    └── DoctorPatientAssignment (M2M join)
            │
            └── Patient
                    │
                    ├── avatar_url (new field)
                    │
                    └── Device (0 or more via FK)
                              └── last_seen  →  device_online computation
```
