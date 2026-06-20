# Tasks: Update Registration Logic

**Input**: Design documents from `specs/013-registration-logic/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: This feature has one implementation task and one optional cleanup. US1 (role restriction) is already complete from E-1.1.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 3: User Story 1 — Registration Restricted to Doctor and Admin (Priority: P1) 🎯

**Goal**: Ensure registration only accepts `doctor` and `admin` roles; `patient` is rejected with a validation error.

**Independent Test**: `POST /api/auth/register/` with `role: "patient"` → `400`. With `role: "doctor"` and `role: "admin"` → `201`.

**Status**: ✅ Already implemented in E-1.1 (T003). `RegisterSerializer.validate_role()` updated; `ROLE_CHOICES` restricted. No implementation tasks required for this story.

---

## Phase 4: User Story 2 — Registration Without Role Defaults to Doctor (Priority: P2)

**Goal**: When a registration request omits the `role` field, the account is created with `role: "doctor"`.

**Independent Test**: `POST /api/auth/register/` without `role` field → `201` with `role: "doctor"` in response.

### Implementation for User Story 2

- [x] T001 [US2] Fix `RegisterSerializer.create()` in `backend/authentication/serializers.py`: change `role=validated_data['role']` to `role=validated_data.get('role', 'doctor')` to prevent `KeyError` when `role` is absent from the request

**Checkpoint**: `POST /api/auth/register/` without `role` field creates a user with `role: "doctor"`. No `KeyError` raised.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T002 Remove the now-dead `validate_role()` method from `RegisterSerializer` in `backend/authentication/serializers.py` — DRF's built-in `invalid_choice` validation (from `ChoiceField`) already rejects any value not in `ROLE_CHOICES` before `validate_role()` is ever called, making it unreachable dead code

**Checkpoint**: `RegisterSerializer` is clean — no dead code. DRF's built-in choices validation handles all invalid role rejection.

> **Note**: T002 is optional. The dead method is harmless but adds noise. Omit if you prefer to keep the explicit message for documentation purposes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: Already complete — no tasks
- **Phase 4 (US2)**: No blocking prerequisites — start immediately
- **Phase 5 (Polish)**: T002 depends on T001 completing (same file)

### Within Each User Story

- T001: Only task — execute immediately
- T002: Same file as T001 — sequential after T001

### Parallel Opportunities

No parallel opportunities — only two tasks, both in the same file.

---

## Implementation Strategy

### MVP First

1. Execute T001 (one-line fix in `serializers.py`)
2. **STOP and VALIDATE**: Registration without `role` returns `role: "doctor"` in response
3. Optionally execute T002 (remove dead `validate_role()`)

---

## Notes

- T001 is a **bug fix**, not a new feature. The bug was introduced because E-1.1 added `default='doctor'` to the model field but DRF does not propagate model-level defaults to `validated_data`. The `.get('role', 'doctor')` call applies the default at the application level.
- After T002, the error message for invalid roles will be DRF's built-in `'"patient" is not a valid choice.'` rather than the custom `"Role must be either 'doctor' or 'admin'."`. Both are acceptable per spec FR-003.
- No database migration needed — no model or schema changes.
