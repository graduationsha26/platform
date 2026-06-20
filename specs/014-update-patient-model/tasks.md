# Tasks: Update Patient Model

**Input**: Design documents from `specs/014-update-patient-model/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: This feature has one implementation phase (US1). US2 (clinical fields) and US3 (doctor assignment) are already fully implemented — no tasks required for those stories.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 3: User Story 1 — Patient Records Exist Without Login Accounts (Priority: P1) 🎯

**Goal**: Remove `Patient.user` OneToOneField entirely; fix all 4 code locations that reference it; generate and apply the DROP COLUMN migration. After this phase, the Patient model has no link to the authentication system.

**Independent Test**: `POST /api/patients/` with clinical data only (no user reference) → 201. `GET /api/patients/{id}/` → response contains no `user` field. `python manage.py check` → no system errors.

### Implementation for User Story 1

- [x] T001 [US1] Remove the `user = models.OneToOneField(...)` field definition (lines 13–19) from `backend/patients/models.py`

- [x] T002 [P] [US1] Fix `backend/analytics/services/report_generator.py` line 122: replace `f"{self.patient.user.first_name} {self.patient.user.last_name}"` with `self.patient.full_name`

- [x] T003 [P] [US1] Fix `backend/authentication/permissions.py` line 43: remove the dead condition `if hasattr(obj, 'patient') and hasattr(obj.patient, 'user') and obj.patient.user == request.user: return True` from `IsOwnerOrDoctor.has_object_permission()`

- [x] T004 [P] [US1] Fix first dead patient-role branch in `backend/biometrics/views.py` (lines 47–55): remove the entire `if user.role == 'patient':` block and change the subsequent `elif user.role == 'doctor':` to `if user.role == 'doctor':`

- [x] T005 [US1] Fix second dead patient-role branch in `backend/biometrics/views.py` (lines 175–186): remove the entire `if user.role == 'patient':` block and change the subsequent `elif user.role == 'doctor':` to `if user.role == 'doctor':` — sequential after T004 (same file)

- [x] T006 [US1] Run `python manage.py makemigrations patients` from `backend/` to generate `backend/patients/migrations/0002_remove_patient_user.py` — run after T001

- [x] T007 [US1] Run `python manage.py migrate` from `backend/` to apply `0002_remove_patient_user` — run after T006

**Checkpoint**: `Patient.user` is gone. Migration applied. All 4 code locations updated. `python manage.py check` outputs no errors.

---

## Phase 4: User Story 2 — Patient Records Store Required Clinical Fields (Priority: P2)

**Status**: ✅ Already implemented. The Patient model already contains all required fields:
- `full_name` (CharField, required) — exact match for "full_name" requirement
- `contact_phone` (CharField, optional) — covers "phone" requirement
- `medical_notes` (TextField, optional) — covers "notes" requirement

**No implementation tasks required for this story.**

---

## Phase 5: User Story 3 — Patients Remain Assignable to Doctors (Priority: P3)

**Status**: ✅ Already implemented. The `DoctorPatientAssignment` junction model provides a fully operational many-to-many doctor-patient relationship. Assignment endpoints (`POST /api/patients/{id}/assign-doctor/`) are working. No changes needed.

**No implementation tasks required for this story.**

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T008 Run `python manage.py check` from `backend/` to confirm no system errors after field removal and code cleanup

**Checkpoint**: Zero errors from Django system checks — the project is consistent after all changes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No blocking prerequisites — start immediately
- **Phase 4 (US2)**: Already complete — no tasks
- **Phase 5 (US3)**: Already complete — no tasks
- **Phase 6 (Polish)**: T008 depends on T001–T007 completing

### Within User Story 1

- T001: Execute first — removes field definition from models.py
- T002, T003, T004: Parallel with each other — different files, no inter-dependencies; start after T001 for logical ordering
- T005: Sequential after T004 — same file (`biometrics/views.py`)
- T006: Sequential after T001 — `makemigrations` reads models.py after the field is removed
- T007: Sequential after T006 — applies the generated migration

### Parallel Opportunities

T002, T003, T004 can run in parallel (different files):
- T002 → analytics/services/report_generator.py
- T003 → authentication/permissions.py
- T004 → biometrics/views.py (first branch)

---

## Implementation Strategy

### MVP First

1. Execute T001 (remove field from models.py)
2. Execute T002–T005 (fix code references)
3. Execute T006–T007 (generate and apply migration)
4. **STOP and VALIDATE**: Run `python manage.py check` → zero errors; run the server; confirm `GET /api/patients/` works
5. Execute T008 (polish checkpoint)

---

## Notes

- T001 is the anchor change — everything else follows from it
- T002–T005 are code fixes, not feature additions; they exist to prevent `AttributeError` after the field is dropped
- T006 (`makemigrations`) MUST come after T001. Running it before removing the field produces no migration.
- T005 is sequential after T004 (same file — both in `biometrics/views.py`)
- No database migration for US2 or US3 — all those fields/tables already exist
- `contact_phone` and `medical_notes` satisfy the "phone" and "notes" requirements without any renaming — changing names would require a separate API contract change
