# Tasks: Update User Model Roles

**Input**: Design documents from `specs/012-update-user-roles/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks grouped by user story (US1 → US2 → Polish). No Setup or Foundational phases needed — this is a modification-only feature on an existing Django app.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 3: User Story 1 — Role Selection Restricted to Doctor and Admin (Priority: P1) 🎯 MVP

**Goal**: Remove `patient` from valid role choices, add `admin`, update serializer validation to reject `patient`.

**Independent Test**: Call `POST /api/auth/register/` with `role: "patient"` → expect `400` with validation error. Call with `role: "doctor"` and `role: "admin"` → both succeed with `201`.

### Implementation for User Story 1

- [x] T001 [US1] Update ROLE_CHOICES in `backend/authentication/models.py`: change to `[('doctor', 'Doctor'), ('admin', 'Admin')]`, update `help_text` to `'User role: doctor or admin'`
- [x] T002 [US1] Remove `is_patient()` method and add `is_admin()` helper (`return self.role == 'admin'`) in `backend/authentication/models.py`
- [x] T003 [P] [US1] Update `validate_role()` in `backend/authentication/serializers.py`: change accepted values from `['doctor', 'patient']` to `['doctor', 'admin']` and update error message accordingly

**Checkpoint**: `CustomUser.ROLE_CHOICES` contains only `doctor` and `admin`. `RegisterSerializer.validate_role` rejects `patient`. `is_admin()` exists; `is_patient()` is gone.

---

## Phase 4: User Story 2 — New Users Default to Doctor Role (Priority: P2)

**Goal**: When a new user is created without specifying a role, the system assigns `doctor` automatically.

**Independent Test**: Call `POST /api/auth/register/` without a `role` field → user is created with `role: "doctor"`.

### Implementation for User Story 2

- [x] T004 [US2] Add `default='doctor'` to the `role` field definition in `backend/authentication/models.py` (builds on T001's updated ROLE_CHOICES)

**Checkpoint**: Creating a user without specifying `role` results in `role == 'doctor'`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Migration, constitution update.

- [x] T005 Run `python manage.py makemigrations authentication` from `backend/` to generate `backend/authentication/migrations/0002_alter_customuser_role.py` with the updated choices and default
- [x] T006 Run `python manage.py migrate` from `backend/` to apply the migration to Supabase PostgreSQL
- [x] T007 [P] Update `.specify/memory/constitution.md` Principle IV: change "Two roles: `patient` and `doctor`" to "Two roles: `doctor` and `admin`"

**Checkpoint**: All changes are applied to the database. Constitution reflects the new role set.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No blocking prerequisites — start immediately
- **Phase 4 (US2)**: Depends on T001 (US1 model change must be in place first — same file)
- **Phase 5 (Polish)**: T005/T006 depend on T001 + T004 (all model changes must be final before running `makemigrations`); T007 is independent [P]

### User Story Dependencies

- **User Story 1 (P1)**: Start immediately — no prerequisites
- **User Story 2 (P2)**: Depends on T001 (model change to `role` field) completing first — same file

### Within Each User Story

- T001 → T002: Same file (`models.py`) — sequential
- T003: Different file (`serializers.py`) — can run [P] with T001/T002
- T004: Same file as T001/T002 — must be after T001

### Parallel Opportunities

- T003 (`serializers.py`) can run in parallel with T001+T002 (`models.py`)
- T005 and T006 must run sequentially (migrate depends on makemigrations)
- T007 (constitution update) can run in parallel with T005/T006

---

## Parallel Example: User Story 1

```bash
# These two tasks touch different files — run in parallel:
Task A: T001 + T002 — update models.py (ROLE_CHOICES, remove is_patient, add is_admin)
Task B: T003       — update serializers.py (validate_role)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001 + T002 (model: ROLE_CHOICES + method changes)
2. Complete T003 (serializer: validate_role)
3. **STOP and VALIDATE**: Registration with `patient` role is rejected; `doctor` and `admin` are accepted
4. Proceed to US2 + Polish

### Incremental Delivery

1. T001 → T002 → T003: Role restriction in place (US1 complete)
2. T004: Default role in place (US2 complete)
3. T005 → T006: Migration applied (database updated)
4. T007: Constitution updated

---

## Notes

- [P] tasks can run in parallel (different files, no shared state)
- T005 (`makemigrations`) must only be run after ALL model changes (T001, T002, T004) are finalized to produce a single clean migration
- No data migration required — no existing users have `patient` role (per Assumptions in spec.md)
- `is_patient()` removal is safe — no other backend files call this method (confirmed in research.md)
- Dead branches (`role == 'patient'`) in analytics/biometrics/realtime are out of scope per spec
