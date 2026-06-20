# Data Model: Patient Distribution (Admin)

**Feature**: 048-patient-distribution
**Date**: 2026-06-14
**Phase**: 1 (Design)

> **No schema changes.** This feature reuses existing models and tables. No migration is generated. This document describes the entities as they are used by the feature.

---

## Entity: Patient (existing — `patients.Patient`, table `patients`)

| Field | Type | Notes for this feature |
|-------|------|------------------------|
| `id` | AutoField (PK) | Identifies a patient on the roster and in `/assign/`. |
| `full_name` | CharField(200) | **Required** at registration. Displayed in roster. |
| `date_of_birth` | DateField | **Required** at registration. Validated: not in the future. |
| `contact_phone` | CharField(20), blank | Optional intake field. Regex-validated by model. |
| `contact_email` | EmailField, blank | Optional intake field. Shown in roster subtext / search. |
| `medical_notes` | TextField, blank | Optional intake field. |
| `avatar_url` | URLField, blank | Not set by this feature. |
| `created_by` | FK → CustomUser, PROTECT | Set to the **admin** performing registration. No role restriction in model. |
| `created_at` / `updated_at` | DateTime | Auto-managed. `created_at` shown on roster. |

**Validation rules used**: `date_of_birth` not in future (model `clean()` + serializer mirror). Registration creates the row via the serializer (which sets `created_by`).

**No fields added or changed.**

---

## Entity: DoctorPatientAssignment (existing — `patients.DoctorPatientAssignment`, table `doctor_patient_assignments`)

| Field | Type | Notes for this feature |
|-------|------|------------------------|
| `id` | AutoField (PK) | — |
| `doctor` | FK → CustomUser, CASCADE, `related_name='patient_assignments'` | The assigned doctor. Must have role `doctor` (model `clean()`). Drives roster "assigned doctor". |
| `patient` | FK → Patient, CASCADE, `related_name='doctor_assignments'` | The assigned patient. |
| `assigned_at` | DateTime (auto) | Default ordering `-assigned_at` → "most recent" is the effective assignment. |
| `assigned_by` | FK → CustomUser, SET_NULL, null/blank | **Set to `None`** for admin-initiated assignments (admin isn't a doctor; model `clean()` only checks role when truthy). |

**Constraints used**:
- `unique_together = [['doctor','patient']]` — prevents duplicate doctor-patient pairs.
- `clean()` enforces `doctor.role == 'doctor'`; and `assigned_by.role == 'doctor'` **only when `assigned_by` is set** → `None` is valid.

**Lifecycle in this feature**:
- **Register with doctor**: create one row (`doctor=chosen`, `patient=new`, `assigned_by=None`).
- **Register without doctor**: create no row → patient is Unassigned.
- **Assign / reassign**: inside `transaction.atomic()`, delete all rows for the patient, then create one row to the chosen doctor (`assigned_by=None`). Reassign-to-same-doctor nets the same single row.

---

## Entity: CustomUser (existing — `authentication.CustomUser`, table `users`)

Used read-only by this feature in two ways:
- **As the assignment target (doctor)**: filtered to `role='doctor'` and (for the dropdown) `is_active=True`. Displayed as `get_full_name()`.
- **As the registrant (admin)**: `request.user` with `role='admin'`; becomes `Patient.created_by`. Access enforced by `IsAdmin`.

No changes.

---

## Derived / computed shapes (not persisted)

### `assigned_doctor` (roster column)
Computed per patient from `doctor_assignments` ordered by `-assigned_at`, first row:

```json
{ "id": 1, "name": "Dr. John Smith", "email": "doctor@test.com" }
```
or `null` when the patient has no assignment (→ UI shows "Unassigned").

---

## Relationship diagram (textual)

```
CustomUser(role=admin) ──creates──▶ Patient.created_by
CustomUser(role=doctor) ◀─doctor─── DoctorPatientAssignment ──patient──▶ Patient
                                     (assigned_by = NULL for admin actions)

Roster row  = Patient  +  (its most-recent DoctorPatientAssignment.doctor | null)
```

---

## Requirement → data mapping

| FR | Data behavior |
|----|---------------|
| FR-001 | `Patient.objects.all()` (center-wide), prefetch assignments |
| FR-002 | `assigned_doctor` from `doctor_assignments`, else `null` → "Unassigned" |
| FR-004/FR-006 | Create `Patient` (+ optional `DoctorPatientAssignment`) |
| FR-007 | Serializer validation; `full_name` + `date_of_birth` required; nothing saved on failure (atomic) |
| FR-008/FR-009 | Transactional delete-then-create on `DoctorPatientAssignment` |
| FR-010 | `validate_doctor_id` (exists + role doctor); 404 on missing patient |
| FR-011 | Only assignment rows change; `Patient` row untouched on reassign |
| FR-012 | `AdminPatientPagination` (page_size 50) → `{count,next,previous,results}` |
