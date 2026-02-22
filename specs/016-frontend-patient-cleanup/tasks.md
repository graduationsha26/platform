# Tasks: Frontend Patient Role Cleanup (E-1.5 + E-1.6)

**Input**: Design documents from `specs/016-frontend-patient-cleanup/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: This feature has 3 implementation phases (US1, US2, US3). Tasks are grouped by user story to enable independent implementation and testing. T001 is a shared foundational task that blocks US1 (RegisterForm imports roleValidation); US2 and US3 tasks are independent of each other after T001.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 2: Foundational — Role Validator (Blocking Prerequisite)

**Purpose**: Fix the client-side role validation constant that is imported by `RegisterForm.jsx`. Must be correct before the form is updated, or selecting "Admin" would fail form validation.

**⚠️ CRITICAL**: T001 must complete before T002 (same import chain). T003–T006 are technically independent of T001 but should run after for logical ordering.

- [x] T001 Update `roleValidation` in `frontend/src/utils/validators.js` — change `['doctor', 'patient'].includes(value)` to `['doctor', 'admin'].includes(value)` and update the error message from "Role must be either doctor or patient" to "Role must be either doctor or admin"

**Checkpoint**: `validators.js` now accepts `'doctor'` and `'admin'` — rejects `'patient'`. RegisterForm can safely be updated.

---

## Phase 3: User Story 1 — Registration Form Shows Only Doctor and Admin (Priority: P1) 🎯

**Goal**: Remove the Patient radio button, add an Admin radio button, and change the default role from `'patient'` to `'doctor'` in the registration form.

**Independent Test**: Open the registration page → role selector shows exactly two options ("Doctor" and "Admin"), default selection is Doctor, no "Patient" option anywhere.

### Implementation for User Story 1

- [x] T002 [US1] Update `frontend/src/components/auth/RegisterForm.jsx` — three changes in one edit: (1) change `defaultValues: { role: 'patient' }` to `defaultValues: { role: 'doctor' }`; (2) delete the Patient radio button `<label>` block (the block with `value="patient"` and text "I use the smart glove for tremor suppression"); (3) add Admin radio button `<label>` block after the existing Doctor radio with `value="admin"` and description "I manage the TremoAI platform" — run after T001

**Checkpoint**: Registration page shows Doctor (default) and Admin options only. Selecting Admin submits `role: "admin"`. Selecting Doctor submits `role: "doctor"`. No validation errors for either choice.

---

## Phase 4: User Story 2 — Patient Dashboard and Routes Removed (Priority: P2)

**Goal**: Remove the `PatientDashboard` lazy import and `/patient/dashboard` route from AppRoutes, delete the `PatientDashboard.jsx` file, and fix the post-login redirect so admin users go to `/doctor/dashboard` instead of the now-deleted `/patient/dashboard`.

**Independent Test**: Navigate directly to `/patient/dashboard` → redirected to `/login`. Codebase has no reference to `PatientDashboard` component.

### Implementation for User Story 2

- [x] T003 [P] [US2] Update `frontend/src/routes/AppRoutes.jsx` — (1) delete the line `const PatientDashboard = lazy(() => import('../pages/PatientDashboard'));`; (2) delete the entire `<Route path="/patient/dashboard" element={<ProtectedRoute><PatientDashboard /></ProtectedRoute>} />` block (lines ~40–47) — parallel with T002 (different file)

- [x] T004 [US2] Delete `frontend/src/pages/PatientDashboard.jsx` — remove the entire file; confirm the lazy import in AppRoutes is gone (T003) before deleting — run sequentially after T003

- [x] T005 [P] [US2] Update `frontend/src/contexts/AuthContext.jsx` — replace the ternary at line ~92 (`userData.role === 'doctor' ? '/doctor/dashboard' : '/patient/dashboard'`) with a direct assignment `targetPath = '/doctor/dashboard'` — parallel with T003 (different file)

**Checkpoint**: `/patient/dashboard` route is gone. `PatientDashboard.jsx` file is deleted. Admin login redirects to `/doctor/dashboard`. The catch-all route (`path="*"`) handles any direct navigation to former patient URLs → redirects to `/login`.

---

## Phase 5: User Story 3 — Role Utilities Purged of Patient Logic (Priority: P3)

**Goal**: Remove the `if (role === 'patient')` menu branch from `roleHelpers.js`, add an admin branch that delegates to the doctor menu, and simplify `getDashboardPath()` to return `/doctor/dashboard` unconditionally.

**Independent Test**: `grep -r "patient" frontend/src/utils/roleHelpers.js` → no output.

### Implementation for User Story 3

- [x] T006 [P] [US3] Update `frontend/src/utils/roleHelpers.js` — three changes: (1) delete the entire `if (role === 'patient') { return [...]; }` block (lines ~44–72) from `getMenuItems()`; (2) insert `if (role === 'admin') { return getMenuItems('doctor'); }` after the existing `if (role === 'doctor')` block in `getMenuItems()`; (3) replace `getDashboardPath()` body from `return role === 'doctor' ? '/doctor/dashboard' : '/patient/dashboard'` to `return '/doctor/dashboard'` — parallel with T002/T003 (different file)

**Checkpoint**: `getMenuItems('admin')` returns doctor menu items. `getDashboardPath()` returns `/doctor/dashboard` for any role. No `/patient/` paths in any return value.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T007 Verify no patient references remain — run `grep -r "patient" frontend/src/utils/ frontend/src/contexts/ frontend/src/routes/ frontend/src/components/auth/ frontend/src/pages/` and confirm output is empty (or contains only non-role occurrences like comments/JSDoc describing what the field monitors); confirm `PatientDashboard.jsx` file is deleted

**Checkpoint**: Zero role-conditional `patient` references remain in the frontend source. The codebase is fully aligned with the backend's `doctor`/`admin` role model.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No blocking prerequisites — T001 starts immediately
- **Phase 3 (US1)**: T002 depends on T001 completing (RegisterForm imports roleValidation)
- **Phase 4 (US2)**: T003 and T005 can start after T001 (or in parallel with T002); T004 is sequential after T003 (same file chain)
- **Phase 5 (US3)**: T006 is independent — can start after T001 or in parallel with T002/T003
- **Phase 6 (Polish)**: T007 depends on T001–T006 completing

### Within Each User Story

- **US1**: T001 → T002 (sequential — import dependency)
- **US2**: T003 [P], T005 [P] can run in parallel; T004 sequential after T003
- **US3**: T006 [P] is independent — no internal dependencies

### Parallel Opportunities

After T001 completes, the following can run in parallel (all different files):
- T002 → `frontend/src/components/auth/RegisterForm.jsx`
- T003 → `frontend/src/routes/AppRoutes.jsx`
- T005 → `frontend/src/contexts/AuthContext.jsx`
- T006 → `frontend/src/utils/roleHelpers.js`

T004 (delete file) must wait for T003 to finish.

---

## Parallel Example: After T001

```
T001 (validators.js) COMPLETES
    ↓
    ├── T002 [US1] RegisterForm.jsx
    ├── T003 [US2] AppRoutes.jsx ──→ T004 [US2] Delete PatientDashboard.jsx
    ├── T005 [US2] AuthContext.jsx
    └── T006 [US3] roleHelpers.js
         ↓
        T007 Verify (after all above complete)
```

---

## Implementation Strategy

### MVP First (US1 — Registration Form Fix)

1. Execute T001 (fix validator)
2. Execute T002 (fix RegisterForm)
3. **STOP and VALIDATE**: Open `/register` — confirm only Doctor (default) and Admin options appear

### Then Route Removal (US2)

4. Execute T003 (remove PatientDashboard from AppRoutes)
5. Execute T004 (delete PatientDashboard.jsx file)
6. Execute T005 (fix AuthContext redirect)
7. **VALIDATE**: Navigate to `/patient/dashboard` → redirected to `/login`

### Then Utility Cleanup (US3)

8. Execute T006 (clean roleHelpers.js)
9. Execute T007 (grep verification)
10. **VALIDATE**: `grep -r "patient" frontend/src/utils/ frontend/src/contexts/ frontend/src/routes/ frontend/src/components/auth/` → no output

---

## Notes

- T001 is the anchor — T002 depends on it (import chain); T003–T006 are logically dependent but technically file-independent
- T004 (file deletion) is the only irreversible operation — verify T003 is complete first
- No migrations required — pure frontend code change
- `backend/` files are intentionally left unchanged — E-1.1 through E-1.4 already handled all backend work
- The catch-all route `path="*" → /login` already handles deleted patient URLs — no new redirect component needed
- `getDashboardPath()` simplified to a constant return — the role parameter is retained in the signature for API compatibility but ignored (all roles use doctor dashboard)
