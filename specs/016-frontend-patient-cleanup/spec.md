# Feature Specification: Frontend Patient Role Cleanup

**Feature Branch**: `016-frontend-patient-cleanup`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-1.5 Update Frontend Registration — Remove 'patient' role option from registration form. Only show doctor/admin. Update role dropdown/selector. E-1.6 Remove Patient-Facing UI — Remove any patient dashboard, patient self-view, or patient-specific routes/components. All views are doctor/admin facing."

## Background

The backend no longer supports a `patient` role (removed in E-1.1). The frontend registration form still offers a "Patient" option, and patient-specific routes/pages still exist in the application. This feature removes all patient-facing elements to bring the frontend into alignment with the backend's doctor/admin-only role model.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Registration Form Shows Only Doctor and Admin Roles (Priority: P1)

A new user visiting the registration page sees only two role options: "Doctor" and "Admin". There is no "Patient" option anywhere on the registration screen. When a user selects a role and submits, the submitted role is either `doctor` or `admin` — never `patient`.

**Why this priority**: The registration form is the entry point for all new users. If "Patient" remains as a selectable option, a user could submit a registration with `role: 'patient'`, which the backend will reject or misbehave on. This is a data-integrity issue and must be fixed first.

**Independent Test**: Open the registration page and verify the role selector lists exactly two options ("Doctor" and "Admin") with no "Patient" option visible anywhere on the page.

**Acceptance Scenarios**:

1. **Given** a visitor loads the registration page, **When** they view the role selection, **Then** they see exactly two role options — "Doctor" and "Admin" — with no "Patient" option present.
2. **Given** a user selects "Doctor" and submits the form, **When** the form data is sent, **Then** the submitted role value is `doctor`.
3. **Given** a user selects "Admin" and submits the form, **When** the form data is sent, **Then** the submitted role value is `admin`.
4. **Given** the registration page loads for the first time, **When** no role has been selected yet, **Then** the default pre-selected role is `doctor` (not `patient` or empty).

---

### User Story 2 — Patient Dashboard and Routes Are Removed (Priority: P2)

No patient-specific pages, routes, or navigation entries exist in the application. Navigating directly to a patient URL (e.g., `/patient/dashboard`) results in a redirect to the login page or a not-found page — not a rendered patient screen. The application routing and navigation only contain doctor- and admin-facing destinations.

**Why this priority**: Patient pages are unreachable for any real user (no valid patient role exists), but they still consume code and create confusion. They must be removed after the registration form is fixed to ensure no dead routes or orphaned pages remain.

**Independent Test**: Attempt to navigate directly to `/patient/dashboard` — the application must not render the patient dashboard. Verify no route with a `/patient/` path prefix is defined in the application.

**Acceptance Scenarios**:

1. **Given** the application routing is configured, **When** all defined routes are inspected, **Then** no route with a `/patient/` path prefix exists.
2. **Given** a user navigates to `/patient/dashboard` directly, **When** the router processes the request, **Then** the user sees a redirect or not-found page — the patient dashboard is never rendered.
3. **Given** a doctor logs in and views the navigation menu, **When** they inspect all available menu items, **Then** no patient self-view links appear.
4. **Given** the application codebase, **When** searching for the patient dashboard page component, **Then** it no longer exists in the project.

---

### User Story 3 — Role Utilities No Longer Reference Patient (Priority: P3)

Shared utility functions (menu item generation, dashboard path resolution, route access checks) only operate on `doctor` and `admin` roles. Any `patient` branch in these helpers is removed. This ensures no residual logic silently handles a role that cannot exist.

**Why this priority**: Dead code in utilities is lower risk than live UI, but it creates maintenance confusion and can mask future bugs. It should be cleaned up after the UI is fixed.

**Independent Test**: Search the entire frontend codebase for `'patient'` in role-conditional logic — no occurrences should remain in menu generators, path resolvers, or access checkers.

**Acceptance Scenarios**:

1. **Given** the role-helper utilities, **When** called with any role value, **Then** no code path handles a `'patient'` role value.
2. **Given** the dashboard-path resolver, **When** called with role `doctor`, **Then** it returns the doctor dashboard path; for `admin`, it returns the admin dashboard path (or doctor dashboard as fallback).
3. **Given** the menu-item generator, **When** called with any valid role, **Then** it produces no menu items pointing to `/patient/` paths.

---

### Edge Cases

- What if a user bookmarked `/patient/dashboard` before the removal? They should be gracefully redirected (login page or not-found), not shown a broken page.
- What if the registration form default role was `patient` and it is removed without setting a new default? The form must default to `doctor` — never submit with an empty or undefined role.
- What if role helpers are called with an unrecognized role string? They should return safe defaults (empty menu list, doctor dashboard path) without crashing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registration form MUST NOT include a "Patient" option in the role selector — only "Doctor" and "Admin" are valid selectable roles.
- **FR-002**: The registration form MUST default to the `doctor` role on load (not `patient` and not empty/undefined).
- **FR-003**: The application MUST NOT define any route with a `/patient/` path prefix.
- **FR-004**: The `PatientDashboard` page component MUST be removed from the codebase entirely.
- **FR-005**: Role-based utility functions MUST NOT contain any conditional branch that handles `role === 'patient'`.
- **FR-006**: Navigation generated for any authenticated user MUST NOT include links to patient-specific destinations.
- **FR-007**: Accessing any removed patient route MUST result in a redirect or not-found response — never a rendered patient page.

### Scope Boundaries

**In scope**:
- Registration form role selector (remove Patient option, fix default)
- Application routing (remove all `/patient/` routes)
- `PatientDashboard` page component (delete file)
- Role helper utilities (remove all patient branches)
- Any navigation/menu code that generates patient-specific links

**Out of scope**:
- Backend API changes (already complete in E-1.1 through E-1.4)
- Admin-specific dashboard UI (separate feature)
- Doctor dashboard content changes
- Authentication or JWT token handling

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of role options visible on the registration page are valid backend roles (`doctor` or `admin`) — zero `patient` options remain visible.
- **SC-002**: 0 routes in the application routing configuration have a `/patient/` path prefix.
- **SC-003**: A search for `'patient'` in role-conditional frontend logic returns 0 matches.
- **SC-004**: Navigating directly to any former patient URL results in a redirect or not-found — 0% chance of rendering a patient dashboard.

## Assumptions

- The application currently has exactly one patient-specific page (`PatientDashboard`). If additional patient pages exist they are all in scope for removal.
- The registration form currently offers "Doctor" and "Patient" as role options. An "Admin" option may or may not already exist — if missing, it must be added.
- Doctors and admins share the same doctor dashboard view (no separate admin-specific dashboard page is required by this feature).
- Role helpers returning a safe default for unknown roles (e.g., doctor dashboard path, empty menu) is acceptable behavior.

## Dependencies

- **E-1.1** (012-update-user-roles): Backend role model changed to `doctor`/`admin` only. ✅ Complete.
- **E-1.4** (015-patient-permissions): Backend API permission layer updated. ✅ Complete.
- No other features block this work.
