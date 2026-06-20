# Research: Update Patient Model

**Feature**: 014-update-patient-model | **Date**: 2026-02-18

---

## Decision 1: Remove `Patient.user` Entirely vs. Keep Nullable

**Decision**: Remove the `user` OneToOneField from Patient entirely via a DROP COLUMN migration.

**Rationale**: The field's only purpose was to link a patient's record to a patient-role user account. E-1.1 removed 'patient' from `ROLE_CHOICES`, making no new patient-role users possible and making this link permanently dead. A nullable field serving no purpose adds confusion and risk (stale foreign-key references in code can cause `AttributeError` at runtime). Complete removal is the correct clean-up.

**Alternatives considered**:
- Keep nullable (current state, null=True): Rejected. The field will never be set again. Keeping it adds dead ORM surface area and confusing API responses that include `user: null` on every patient record.
- Set to null for all existing rows first, then drop: This is the migration strategy, not an alternative. Since the field is already nullable, DROP COLUMN is safe even if some rows currently have a value (SET_NULL was the on_delete strategy).

---

## Decision 2: Rename `contact_phone` / `medical_notes` vs. Keep Existing Names

**Decision**: Keep existing field names (`contact_phone` and `medical_notes`). Do NOT rename.

**Rationale**: The feature description says "Add fields: full_name, phone, notes." Runtime inspection shows all three fields already exist: `full_name` (exact match), `contact_phone` (covers "phone"), `medical_notes` (covers "notes"). Renaming requires an additional migration, serializer changes, and API contract updates — unnecessary complexity for zero functional gain. The fields are fully operational under their current names.

**Alternatives considered**:
- Rename to `phone` and `notes`: Rejected. Would require migration + API changes + serializer updates. No business requirement for exact name match.

---

## Decision 3: `assigned_doctor` FK vs. Existing Many-to-Many Junction

**Decision**: Keep the existing `DoctorPatientAssignment` junction table (many-to-many relationship). Do NOT replace with a single `assigned_doctor` ForeignKey.

**Rationale**: The feature description says "Keep assigned_doctor FK" — but the existing implementation already uses a many-to-many junction (`DoctorPatientAssignment`), which is architecturally superior. A single FK would mean a patient can only have one doctor, which conflicts with the platform's design (multiple doctors can monitor the same patient). The junction table is already migrated, tested, and operational. No change is needed.

**Alternatives considered**:
- Replace junction with single `assigned_doctor` FK: Rejected. Loses ability to assign multiple doctors per patient. The existing many-to-many is better and already implemented.

---

## Decision 4: Scope of Code Cleanup

**Decision**: Fix all 4 code locations referencing the removed `Patient.user` field, within the scope of this feature.

**Code locations identified**:

| File | Line | Reference | Fix |
|------|------|-----------|-----|
| `analytics/services/report_generator.py` | 122 | `self.patient.user.first_name + last_name` | Replace with `self.patient.full_name` |
| `authentication/permissions.py` | 43 | `obj.patient.user == request.user` | Remove condition (dead code — no patient-role users) |
| `biometrics/views.py` | 47–55 | `if user.role == 'patient': user.patient_profile` | Remove dead branch |
| `biometrics/views.py` | 175–186 | `if user.role == 'patient': user.patient_profile` | Remove dead branch |

**Rationale**: Leaving these references intact will cause `AttributeError` the moment a code path reaches them (after the field is dropped). All 4 must be fixed as part of this feature.

**Note**: `authentication/permissions.py` also contains `IsPatient` class (references `role == 'patient'`). This is dead code from E-1.1 but is out of scope per the same pattern as in that feature. The minimum fix here is removing the `obj.patient.user` reference in `IsOwnerOrDoctor.has_object_permission()`.

---

## Decision 5: Migration Safety

**Decision**: Standard `AlterField`/`RemoveField` Django migration — no data preservation needed.

**Rationale**: The `user` field is nullable (`null=True`). Dropping it does not cause data loss for any other field. All clinical data (full_name, date_of_birth, contact_phone, medical_notes, created_by) remains intact. Since no production database exists (local dev only), migration risk is minimal.

**Migration name**: `0002_remove_patient_user` — drops the `user` column from the `patients` table.
