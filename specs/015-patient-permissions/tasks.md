# Tasks: Update Patient API Permissions

**Input**: Design documents from `specs/015-patient-permissions/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: This feature has 2 implementation phases (US1 and US3). US2 (doctor scoping) is already fully implemented and confirmed unaffected by the US1 changes — no tasks required for that story.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 3: User Story 1 — Admin Users Can Fully Manage All Patients (Priority: P1) 🎯

**Goal**: Add `IsDoctorOrAdmin` permission class and wire it into `PatientViewSet` so that admin-role users can list, create, retrieve, update, and delete any patient in the system.

**Independent Test**: `GET /api/patients/` with admin token → 200 with all patients. `POST /api/patients/` with admin token → 201. `GET /api/patients/{id}/` with admin token (patient created by different doctor) → 200.

### Implementation for User Story 1

- [x] T001 [US1] Add `IsDoctorOrAdmin` class to `backend/authentication/permissions.py` — insert after the `IsDoctor` class with `has_permission` checking `user.role in ('doctor', 'admin')`

- [x] T002 [P] [US1] Update import line and `permission_classes` in `backend/patients/views.py`: replace `from authentication.permissions import IsDoctor` with `from authentication.permissions import IsDoctorOrAdmin`; change `permission_classes = [IsAuthenticated, IsDoctor]` to `permission_classes = [IsAuthenticated, IsDoctorOrAdmin]` — run after T001

- [x] T004 [US1] Update `PatientViewSet.get_queryset()` in `backend/patients/views.py` — add an `if user.role == 'admin': return Patient.objects.all().select_related(...).prefetch_related(...)` branch before the existing `if user.role != 'doctor'` guard — sequential after T002 (same file)

**Checkpoint**: Admin-role user can CRUD any patient. Doctor-role user is unaffected (their branch unchanged). `python manage.py check` outputs no errors.

---

## Phase 4: User Story 2 — Doctor Access Remains Scoped (Priority: P2)

**Status**: ✅ Already implemented. The `get_queryset()` doctor branch (`created_by=user OR doctor_assignments__doctor=user`) is preserved unchanged by T004 — the admin branch is inserted **before** it, not replacing it.

**No implementation tasks required for this story.**

---

## Phase 5: User Story 3 — Unauthorized Users Completely Blocked (Priority: P3)

**Goal**: Remove the dead `IsPatient` class from `backend/authentication/permissions.py`. This class checks `role == 'patient'`, which no longer exists as a valid role (removed in E-1.1). No user can hold this role, making the class permanently dead code.

**Independent Test**: `grep -r "IsPatient" backend/` → no output (class fully removed). `python manage.py check` → no errors.

### Implementation for User Story 3

- [x] T003 [P] [US3] Remove the `IsPatient` class from `backend/authentication/permissions.py` — delete the entire class block (class declaration + docstring + `has_permission` method); confirm no other file imports `IsPatient` (grep confirmed: no usages) — run after T001 (same file as T001)

**Checkpoint**: `IsPatient` class is gone. Grep for `IsPatient` in `backend/` returns no results. `python manage.py check` outputs no errors.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T005 Run `python manage.py check` from `backend/` to confirm no system errors after all permission and viewset changes

**Checkpoint**: Zero errors from Django system checks — the project is consistent after all changes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No blocking prerequisites — T001 starts immediately
- **Phase 4 (US2)**: Already complete — no tasks
- **Phase 5 (US3)**: T003 depends on T001 completing (same file)
- **Phase 6 (Polish)**: T005 depends on T001–T004 completing

### Within User Story 1

- T001: Execute first — adds `IsDoctorOrAdmin` class to `permissions.py`
- T002: After T001 (must import the new class)
- T004: Sequential after T002 — same file (`patients/views.py`)

### Within User Story 3

- T003: After T001 — same file as T001 (`authentication/permissions.py`)

### Parallel Opportunities

T002 and T003 can run in parallel after T001 (different files):
- T002 → `patients/views.py`
- T003 → `authentication/permissions.py`

T004 must be sequential after T002 (same file as T002).

---

## Implementation Strategy

### MVP First

1. Execute T001 (add `IsDoctorOrAdmin` class)
2. Execute T002 (update import + permission_classes in views)
3. Execute T004 (add admin branch to `get_queryset()`)
4. **STOP and VALIDATE**: Confirm admin token → `GET /api/patients/` returns all patients; doctor token remains scoped
5. Execute T003 (remove `IsPatient`)
6. Execute T005 (system check)

---

## Notes

- T001 is the anchor — T002 and T003 both depend on it (T002 imports the class; T003 edits the same file)
- T002 and T003 are parallel with each other (different files) but both sequential after T001
- T004 is sequential after T002 (same file: `patients/views.py`)
- No migrations required — pure Python permission layer change
- `devices/views.py` intentionally left unchanged — it keeps `IsDoctor` (admin device access is out of scope for E-1.4)
- US2 (doctor scoping) requires zero implementation — T004's admin branch is inserted BEFORE the existing doctor logic, which remains byte-for-byte identical
