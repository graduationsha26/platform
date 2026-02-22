# Implementation Plan: Frontend Patient Role Cleanup (E-1.5 + E-1.6)

**Branch**: `016-frontend-patient-cleanup` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/016-frontend-patient-cleanup/spec.md`

## Summary

Remove all patient-role references from the frontend. The backend dropped the `patient` role in E-1.1; the frontend still offers a "Patient" registration option, routes to a `PatientDashboard`, and has role-helper utilities with patient branches. This feature brings the frontend into alignment: 6 files are modified/deleted, no backend changes, no migrations, no new dependencies.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework (no backend changes for this feature)
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (no database changes)
**Authentication**: JWT (SimpleJWT) with roles: `doctor` and `admin`
**Testing**: Not requested — no test tasks generated
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: N/A — no WebSocket changes
**Integration**: N/A — no MQTT changes
**AI/ML**: N/A — no model changes
**Performance Goals**: No new performance requirements
**Constraints**: Local development only; no migrations needed
**Scale/Scope**: 5 files modified, 1 file deleted; no new endpoints; no schema changes

## Constitution Check

- [x] **Monorepo Architecture**: Feature modifies only `frontend/` files — fits monorepo structure
- [x] **Tech Stack Immutability**: No new frameworks; changes are within existing React + React Hook Form + React Router stack
- [x] **Database Strategy**: No database changes — pure code change
- [x] **Authentication**: JWT roles updated to `doctor` / `admin` in constitution — this aligns the frontend to the constitution's current role model
- [x] **Security-First**: No secrets touched; no `.env` changes
- [x] **Real-time Requirements**: N/A — no real-time features involved
- [x] **MQTT Integration**: N/A — no sensor data involved
- [x] **AI Model Serving**: N/A — no ML inference involved
- [x] **API Standards**: No API endpoint changes — no impact on API standards
- [x] **Development Scope**: Local development only — no deployment config changes

**Result**: ✅ PASS — no violations

## Project Structure

### Documentation (this feature)

```text
specs/016-frontend-patient-cleanup/
├── spec.md                         ✅ Created
├── plan.md                         ✅ This file
├── research.md                     ✅ Created
├── quickstart.md                   ✅ Created
└── checklists/
    └── requirements.md             ✅ Created
```

Note: No `data-model.md` (no data entities changed) and no `contracts/` (no API endpoints changed).

### Source Code (files to modify)

```text
frontend/src/
├── utils/
│   ├── validators.js               MODIFY: roleValidation — change ['doctor','patient'] to ['doctor','admin']
│   └── roleHelpers.js              MODIFY: remove patient branch; add admin branch; fix getDashboardPath
├── components/auth/
│   └── RegisterForm.jsx            MODIFY: default role 'doctor'; remove Patient radio; add Admin radio
├── contexts/
│   └── AuthContext.jsx             MODIFY: post-login redirect — admin → /doctor/dashboard
├── routes/
│   └── AppRoutes.jsx               MODIFY: remove PatientDashboard import and /patient/dashboard route
└── pages/
    └── PatientDashboard.jsx        DELETE: file removed entirely
```

**No backend files are modified.**

## Implementation Details

### Change 1: `frontend/src/utils/validators.js`

**Update `roleValidation`** — change allowed roles from `['doctor', 'patient']` to `['doctor', 'admin']`:

```js
// Before:
export const roleValidation = {
  required: 'Please select a role',
  validate: (value) =>
    ['doctor', 'patient'].includes(value) || 'Role must be either doctor or patient',
};

// After:
export const roleValidation = {
  required: 'Please select a role',
  validate: (value) =>
    ['doctor', 'admin'].includes(value) || 'Role must be either doctor or admin',
};
```

**Why first**: RegisterForm imports this. If the Admin radio submits `value="admin"`, the old validator would reject it. Fix the validator before touching the form.

---

### Change 2: `frontend/src/components/auth/RegisterForm.jsx`

**Three sub-changes in this file:**

**2a** — Change `defaultValues.role` from `'patient'` to `'doctor'`:
```js
// Before:
defaultValues: {
  role: 'patient',
}
// After:
defaultValues: {
  role: 'doctor',
}
```

**2b** — Remove the entire Patient radio button `<label>` block:
```jsx
// DELETE this block:
<label className="flex items-center p-3 border border-neutral-300 rounded-lg ...">
  <input type="radio" value="patient" {...register('role', roleValidation)} ... />
  <div>
    <p className="font-medium text-neutral-900">Patient</p>
    <p className="text-sm text-neutral-600">I use the smart glove for tremor suppression</p>
  </div>
</label>
```

**2c** — Add Admin radio button after the existing Doctor radio:
```jsx
<label className="flex items-center p-3 border border-neutral-300 rounded-lg cursor-pointer hover:bg-neutral-50 transition-colors duration-200">
  <input
    type="radio"
    value="admin"
    {...register('role', roleValidation)}
    className="mr-3 text-primary-600 focus:ring-primary-500"
  />
  <div>
    <p className="font-medium text-neutral-900">Admin</p>
    <p className="text-sm text-neutral-600">
      I manage the TremoAI platform
    </p>
  </div>
</label>
```

---

### Change 3: `frontend/src/contexts/AuthContext.jsx`

**Update post-login redirect logic** — admin must redirect to `/doctor/dashboard` (not `/patient/dashboard`):

```js
// Before:
targetPath = userData.role === 'doctor'
  ? '/doctor/dashboard'
  : '/patient/dashboard';

// After:
targetPath = '/doctor/dashboard';
```

The ternary falls back to `/patient/dashboard` for any non-doctor role — replace with a direct assignment since all valid roles (doctor, admin) now use the doctor dashboard.

---

### Change 4: `frontend/src/utils/roleHelpers.js`

**4a** — Remove the `if (role === 'patient')` block in `getMenuItems()` (lines 44–72). The function already returns `[]` for unknown roles at the end — no replacement needed. Admins get doctor menu items (see 4b).

**4b** — Add an `admin` branch to `getMenuItems()` — admins get the same navigation as doctors:
```js
if (role === 'admin') {
  return getMenuItems('doctor'); // admin shares doctor navigation
}
```
Insert this after the `if (role === 'doctor')` block, before the patient block being deleted.

**4c** — Fix `getDashboardPath()`:
```js
// Before:
export const getDashboardPath = (role) => {
  return role === 'doctor' ? '/doctor/dashboard' : '/patient/dashboard';
};

// After:
export const getDashboardPath = (role) => {
  return '/doctor/dashboard';
};
```
All valid roles use the doctor dashboard path. Simplify to a constant return.

---

### Change 5: `frontend/src/routes/AppRoutes.jsx`

**5a** — Remove the `PatientDashboard` lazy import:
```js
// DELETE:
const PatientDashboard = lazy(() => import('../pages/PatientDashboard'));
```

**5b** — Remove the `/patient/dashboard` Route block:
```jsx
// DELETE:
<Route
  path="/patient/dashboard"
  element={
    <ProtectedRoute>
      <PatientDashboard />
    </ProtectedRoute>
  }
/>
```

The existing catch-all `<Route path="*" element={<Navigate to="/login" replace />} />` handles any attempt to visit `/patient/dashboard` after removal — redirect to login. ✅

---

### Change 6: Delete `frontend/src/pages/PatientDashboard.jsx`

Delete the entire file. It will no longer be imported anywhere after Change 5 removes the lazy import.

```bash
# Verify no remaining imports after deletion:
grep -r "PatientDashboard" frontend/src/
# Expected: no output
```

---

## Dependencies & Execution Order

```
T001 → T002 → T003 → T004 → T005 → T006
```

- **T001**: Fix `validators.js` — must come first (RegisterForm imports roleValidation)
- **T002**: Update `RegisterForm.jsx` — depends on T001 (validator must accept 'admin')
- **T003**: Fix `AuthContext.jsx` — independent of T001/T002 (different file, no dependency on validator); run after T002 for logical grouping
- **T004**: Update `roleHelpers.js` — independent; no cross-file dependencies
- **T005**: Update `AppRoutes.jsx` — remove PatientDashboard import and route
- **T006**: Delete `PatientDashboard.jsx` — must come after T005 (T005 removes the only import)

**Parallel opportunities**: T003 and T004 can run in parallel with T002 (different files).

## Implementation Strategy

### MVP First (US1 — Registration Form)

1. Execute T001 (fix validator)
2. Execute T002 (fix RegisterForm — remove Patient option, add Admin, fix default)
3. **STOP and VALIDATE**: Open registration page, confirm only Doctor and Admin options appear

### Then UI Removal (US2 — Patient Routes)

4. Execute T005 (remove route from AppRoutes)
5. Execute T006 (delete PatientDashboard.jsx)
6. **VALIDATE**: Navigate to `/patient/dashboard` — confirm redirect to login

### Then Utility Cleanup (US3 — Role Helpers)

7. Execute T003 (fix AuthContext post-login redirect)
8. Execute T004 (fix roleHelpers)
9. **VALIDATE**: `grep -r "patient" frontend/src/` → only legitimate non-role uses (if any)
