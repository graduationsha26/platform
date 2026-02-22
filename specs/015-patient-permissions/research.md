# Research: Update Patient API Permissions (E-1.4)

**Branch**: `015-patient-permissions`
**Date**: 2026-02-18

---

## Decision 1: How to Express "Doctor OR Admin" Permission

**Question**: Should we modify the existing `IsDoctor` class, compose permissions at the viewset level, or create a new dedicated class?

**Decision**: Create a new `IsDoctorOrAdmin` class in `backend/authentication/permissions.py`.

**Rationale**:
- `IsDoctor` is also used by `devices/views.py`, which is explicitly out of scope for this change. Modifying `IsDoctor` would silently extend device access to admins — an unreviewed side effect.
- DRF's built-in `IsAdminUser` checks `user.is_staff`, not our custom `user.role == 'admin'`. Using it would check the wrong field.
- DRF's `|` operator (`IsDoctor | IsAdminUser`) would compose the wrong classes with the wrong semantics.
- A named, dedicated class (`IsDoctorOrAdmin`) is explicit, readable, independently testable, and self-documenting at the viewset level.

**Alternatives considered**:
- **Modify `IsDoctor` to allow admin**: Rejected — would silently change `devices/views.py` behavior without review; naming would become misleading.
- **Use DRF's `IsAdminUser | IsDoctor` composition**: Rejected — `IsAdminUser` checks `is_staff` flag, not our domain `role == 'admin'`.
- **Inline lambda permission**: Rejected — not reusable, harder to read, no class-level `message` attribute.

---

## Decision 2: Admin Queryset Scope in `PatientViewSet`

**Question**: Should admin users see all patients, or only patients they explicitly created?

**Decision**: Admin users see **all** patients — `Patient.objects.all()` with no filtering.

**Rationale**:
- Admin is a platform super-user role with system-wide oversight responsibility. Restricting admin to their own subset defeats the purpose of the admin role.
- Doctors are already scoped to their caseload (created_by or assigned). Admin needs a different, broader view for audit/oversight.
- No existing business rule requires admin scoping.

**Alternatives considered**:
- **Admin scoped same as doctors**: Rejected — renders admin no more powerful than a doctor for patient management, which contradicts the role's intent.
- **Admin sees only patients they created**: Rejected — admins are not expected to create patients in normal operation; they need visibility across all doctors' patients.

---

## Decision 3: Remove `IsPatient` Permission Class

**Question**: Should `IsPatient` be removed as part of this change?

**Decision**: Yes — remove `IsPatient` from `backend/authentication/permissions.py`.

**Rationale**:
- The `patient` role was removed from `ROLE_CHOICES` in E-1.1. No user in the system can have `role == 'patient'`.
- A search confirms `IsPatient` is not imported in any other file (`grep` returned no usages outside its definition).
- The feature description explicitly says "Remove any patient-self-access logic."
- Dead code increases maintenance overhead and creates confusion — a future developer may assume the class works.

**Alternatives considered**:
- **Leave `IsPatient` in place**: Rejected — it is permanently dead code; its presence implies the patient role still exists.

---

## Decision 4: Import Cleanup in `patients/views.py`

**Decision**: Replace `from authentication.permissions import IsDoctor` with `from authentication.permissions import IsDoctorOrAdmin`.

**Rationale**: Direct mechanical consequence of switching the permission class. The `IsDoctor` import becomes unused after the change.

---

## Summary: Files to Modify

| File | Change |
|------|--------|
| `backend/authentication/permissions.py` | Add `IsDoctorOrAdmin` class; remove `IsPatient` class |
| `backend/patients/views.py` | Import `IsDoctorOrAdmin`; update `permission_classes`; update `get_queryset()` for admin role |

**No other files need changes.** `devices/views.py` keeps `IsDoctor` — admin device access is out of scope.

**No migrations required** — this is a pure Python/permission change with no database schema impact.
