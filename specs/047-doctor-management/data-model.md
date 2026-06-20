# Data Model: Staff (Doctor) Management

**Feature**: 047-doctor-management
**Date**: 2026-06-14
**Phase**: 1 (Design)

> **No new entities or migrations.** This feature reads and writes existing tables. The entities below document how existing models are used by this feature, not new schema.

---

## Entity: Doctor account (existing — `authentication.CustomUser`)

Table: `users`. A doctor is a `CustomUser` row with `role='doctor'`. This feature lists, creates, edits, and activates/deactivates these rows.

| Field | Type | Used as | Notes |
|-------|------|---------|-------|
| `id` | Integer (PK) | Row identifier for edit/toggle (`/api/admin/doctors/<id>/`) | Read-only |
| `first_name` | CharField | First token of the form's `name` | Written by splitting `name` |
| `last_name` | CharField | Remainder of the form's `name` | Written by splitting `name` |
| `email` | EmailField, `unique=True`, indexed | Login identifier / form `email` | Uniqueness enforced on create + edit |
| `is_active` | Boolean (from `AbstractUser`) | Account status (Active/Inactive) | `False` blocks sign-in (Django + SimpleJWT) |
| `role` | CharField (`doctor`/`admin`) | Roster filter (`role='doctor'`); set to `doctor` on create | Not editable via this feature |
| `password` | Hashed (from `AbstractUser`) | Set on create; optionally reset on edit | Write-only, never returned |
| `date_joined` | DateTime | Informational (read) | Read-only |

**Derived (read-only, not a column):**

| Field | Source | Notes |
|-------|--------|-------|
| `name` | `get_full_name()` → `"{first_name} {last_name}".strip()` | Single display name for table/form |
| `patient_count` | `Count('patient_assignments', distinct=True)` annotation | Number of patients currently assigned to this doctor |

**Validation rules** (enforced in serializer / model):
- `name`: required on create; non-empty after trim (FR-010).
- `email`: required on create; valid email format; unique across all `CustomUser` excluding self on edit (FR-004).
- `password`: required on create, optional on edit; passes Django `validate_password` when present (FR-005, FR-010).
- `is_active`: boolean; defaults to `True` on create if omitted.
- `role`: forced to `'doctor'` on create (not client-controllable).

**State transitions** (account status — FR-006, FR-007):

```
        deactivate (PATCH is_active=false)
Active  ───────────────────────────────────►  Inactive
  ▲                                               │
  └───────────────────────────────────────────────┘
        reactivate (PATCH is_active=true)
```

- Active → can sign in; appears as "Active" in roster.
- Inactive → sign-in refused by auth backend; account + assignments preserved (US3-3, US3-4).
- Transition is reversible and idempotent; no data is deleted in either direction.

---

## Entity: Doctor–patient assignment (existing — `patients.DoctorPatientAssignment`)

Table: `doctor_patient_assignments`. **Read-only** for this feature — used solely to derive `patient_count`. Not created, modified, or deleted by staff management.

| Field | Type | Relevance |
|-------|------|-----------|
| `doctor` | FK → `CustomUser`, `related_name='patient_assignments'` | The reverse relation counted for `patient_count` |
| `patient` | FK → `Patient` | The assigned patient |
| `assigned_at` | DateTime | n/a to this feature |

- `unique_together = (doctor, patient)` guarantees one row per doctor–patient pair, so a plain `Count` (with `distinct=True` as a safeguard) is accurate.
- Deactivating a doctor leaves these rows intact (FR-007).

---

## Entity: Administrator (existing — `authentication.CustomUser`, `role='admin'`)

The privileged actor. Not part of the roster (`role='doctor'` filter excludes admins) and never the target of create/edit/toggle. Enforced by the `IsAdmin` permission on both endpoints (FR-008).

---

## API field shapes

**Doctor (read — list item / response after create/update):**
```json
{
  "id": 12,
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "is_active": true,
  "patient_count": 7,
  "date_joined": "2026-05-01T09:30:00Z"
}
```

**Create request (`POST /api/admin/doctors/`):**
```json
{
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "password": "S0me-Strong-Pass",
  "is_active": true
}
```

**Update request (`PATCH /api/admin/doctors/<id>/`)** — any subset; password optional:
```json
{ "name": "Jane A. Smith", "is_active": false }
```

**List response (paginated):**
```json
{
  "count": 23,
  "next": null,
  "previous": null,
  "results": [ /* array of Doctor read objects */ ]
}
```

**Error (validation / access):**
```json
{ "email": ["doctor with this email already exists."] }
```
```json
{ "error": "Only admins can perform this action." }
```
