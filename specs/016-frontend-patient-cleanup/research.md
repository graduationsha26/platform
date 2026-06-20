# Research: Frontend Patient Role Cleanup (E-1.5 + E-1.6)

**Branch**: `016-frontend-patient-cleanup`
**Date**: 2026-02-18

No NEEDS CLARIFICATION markers were present in the spec. Research focused on confirming the scope of patient references in the frontend codebase and resolving four design decisions.

---

## Decision 1: Admin Post-Login Redirect Path

**Decision**: Admin users redirect to `/doctor/dashboard` after login (same as doctors). No separate `/admin/dashboard` route is created.

**Rationale**: No admin-specific dashboard page exists, and creating one is explicitly out of scope for this feature. `AuthContext.login()` currently has a fallback that sends any non-doctor role to `/patient/dashboard`. Replacing that with a direct `/doctor/dashboard` assignment serves both doctor and admin roles correctly.

**Alternatives considered**:
- Create `/admin/dashboard` — out of scope for E-1.5/E-1.6; deferred to a future feature
- Leave fallback logic — would cause admin users to navigate to a now-deleted route

**Evidence**: `AuthContext.jsx:92-94` — `userData.role === 'doctor' ? '/doctor/dashboard' : '/patient/dashboard'`

---

## Decision 2: Admin Navigation Menu

**Decision**: Admin users get the same navigation menu as doctors (`getMenuItems('admin')` delegates to `getMenuItems('doctor')`).

**Rationale**: No admin-specific navigation exists. Admins need to navigate the platform just like doctors (they can view patients, analytics, reports, settings). An empty menu would break the sidebar for admin users.

**Alternatives considered**:
- Return `[]` for admin — admin would have no navigation items (broken UX)
- Separate admin menu items pointing to `/admin/` paths — out of scope; no admin-specific routes exist

**Evidence**: `roleHelpers.js:44-72` — patient block to remove; doctor block at lines 14-42 is the template for admin

---

## Decision 3: Delete vs. Empty PatientDashboard

**Decision**: Delete `frontend/src/pages/PatientDashboard.jsx` entirely. The file is not replaced with an empty module or redirect component.

**Rationale**: FR-004 requires the component to be "removed from the codebase entirely." After `AppRoutes.jsx` removes the lazy import and the route, there are zero references to this file. Deleting it prevents confusion and fulfills the spec requirement. The catch-all route `path="*" → /login` already handles any direct navigation attempt.

**Alternatives considered**:
- Replace with a redirect component — unnecessary, the catch-all already handles this
- Leave file but remove imports — violates FR-004; dead file clutters the codebase

---

## Decision 4: Role Validator Must Be Updated

**Decision**: Update `roleValidation` in `validators.js` from `['doctor', 'patient']` to `['doctor', 'admin']`.

**Rationale**: The `RegisterForm` uses `roleValidation` from `validators.js` for client-side validation. If the Admin radio button submits `value="admin"` and the validator only accepts `['doctor', 'patient']`, the Admin option would fail validation with "Role must be either doctor or patient." This would silently block admin registrations despite the UI appearing correct.

**Evidence**: `validators.js:82-86` — `['doctor', 'patient'].includes(value)` with error message "Role must be either doctor or patient"

**Alternatives considered**:
- Remove role validation entirely — worse security; allows any string to be submitted as role
- Add 'admin' to the existing array alongside 'patient' — 'patient' would remain valid, which contradicts FR-001

---

## Codebase Survey: All Patient References Found

| File | Patient Reference | Action |
|------|------------------|--------|
| `utils/validators.js:84-85` | `['doctor', 'patient']` in roleValidation | Update to `['doctor', 'admin']` |
| `components/auth/RegisterForm.jsx:48` | `role: 'patient'` default value | Change to `'doctor'` |
| `components/auth/RegisterForm.jsx:154-167` | Patient radio button block | Delete block |
| `contexts/AuthContext.jsx:92-94` | `: '/patient/dashboard'` redirect fallback | Replace with `/doctor/dashboard` |
| `routes/AppRoutes.jsx:15` | `PatientDashboard` lazy import | Delete |
| `routes/AppRoutes.jsx:40-47` | `/patient/dashboard` Route | Delete |
| `utils/roleHelpers.js:44-72` | `if (role === 'patient')` block in getMenuItems | Delete block |
| `utils/roleHelpers.js:83` | `': '/patient/dashboard'` in getDashboardPath | Simplify to return `/doctor/dashboard` |
| `pages/PatientDashboard.jsx` | Entire file | Delete file |

**Total**: 5 files modified, 1 file deleted, 9 patient references removed.

No patient references found in:
- `components/layout/` files (AppLayout, Sidebar, TopBar, MobileMenu)
- `services/api.js`, `services/authService.js`
- `hooks/useAuth.js`
- `utils/tokenStorage.js`
- `main.jsx`, `App.jsx`
