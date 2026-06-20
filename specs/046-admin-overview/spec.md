# Feature Specification: Admin Global Overview

**Feature Branch**: `046-admin-overview`
**Created**: 2026-06-14
**Status**: Draft
**Input**: User description: "5.1 Admin Global Overview Build Admin dashboard page with summary metric cards: Total Doctors and Total Center Patients. AdminDashboard page. 5.2 Admin Global Overview Create GET /api/admin/stats/ returning total_doctors and total_patients. analytics/views.py"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Admin Dashboard Summary Cards (Priority: P1)

An admin (institutional manager or receptionist) logs in and lands on the Admin Dashboard page. They see two metric cards displaying the current total number of doctors registered in the center and the total number of patients enrolled across all doctors. The numbers update each time the page loads, giving the admin an accurate picture of the center's scale at a glance.

**Why this priority**: The Admin Dashboard is the first screen an admin sees after login. Without summary metrics, the page provides no actionable information. This is the MVP for the admin experience.

**Independent Test**: Log in as an admin-role user, navigate to the Admin Dashboard page. Verify that two cards appear — one labeled "Total Doctors" and one labeled "Total Center Patients" — each showing a non-negative integer. The numbers must reflect the actual user counts in the system. Call the stats endpoint without a token → 401. Call it with a doctor token → 403.

**Acceptance Scenarios**:

1. **Given** an authenticated admin, **When** they navigate to the Admin Dashboard, **Then** they see a "Total Doctors" card and a "Total Center Patients" card, each showing the correct count.
2. **Given** an authenticated admin with no doctors or patients in the system, **When** they view the dashboard, **Then** both cards show zero rather than empty or error states.
3. **Given** an unauthenticated request to the stats endpoint, **When** the request is made, **Then** the server returns a 401 Unauthorized response.
4. **Given** a doctor-role user requests the stats endpoint, **When** the request is made, **Then** the server returns a 403 Forbidden response.
5. **Given** the stats endpoint returns an error, **When** the Admin Dashboard loads, **Then** the cards show an error indicator rather than crashing the page.

---

### Edge Cases

- What happens when there are zero doctors registered? → "Total Doctors" card shows 0.
- What happens when there are zero patients enrolled? → "Total Center Patients" card shows 0.
- What happens if the stats endpoint is temporarily unavailable? → Cards display an error state; the rest of the page remains functional.
- What happens if an admin has a stale auth token? → Redirected to login; the dashboard never loads.
- What happens when the admin refreshes the page? → Fresh data is fetched on every page load.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an Admin Dashboard page accessible only to admin-role users.
- **FR-002**: System MUST display a "Total Doctors" metric card showing the total number of doctor accounts in the center.
- **FR-003**: System MUST display a "Total Center Patients" metric card showing the total number of patient records enrolled in the system.
- **FR-004**: System MUST expose a stats endpoint that returns `total_doctors` and `total_patients` as integers.
- **FR-005**: System MUST restrict the stats endpoint to admin-role users only, returning 401 for unauthenticated requests and 403 for non-admin authenticated requests.
- **FR-006**: System MUST show a loading state on each metric card while data is being fetched.
- **FR-007**: System MUST show an error indicator on metric cards if the stats endpoint fails, without crashing the dashboard.
- **FR-008**: System MUST show a count of 0 on metric cards when the system has no doctors or patients, rather than showing an empty or broken state.

### Key Entities

- **Admin User**: A user with role `admin`. Can view center-wide aggregate stats but cannot see individual patient data.
- **Total Doctors**: The count of all users with role `doctor` in the system.
- **Total Center Patients**: The count of all patient records in the system, regardless of doctor assignment.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin user can view the Admin Dashboard and see accurate doctor and patient counts within one page load — no additional user actions required.
- **SC-002**: The dashboard metric cards accurately reflect the current database counts — zero tolerance for stale or incorrect values on page load.
- **SC-003**: The stats endpoint rejects non-admin access 100% of the time (401 for no auth, 403 for wrong role).
- **SC-004**: The dashboard renders in under 2 seconds on a standard development machine with the local dev server running.
- **SC-005**: The dashboard remains functional (graceful error state, no crash) when the stats endpoint returns an error.

## Assumptions

- "Total doctors" counts all users with `role = 'doctor'` regardless of assignment status.
- "Total patients" counts all patient records regardless of which doctor they are assigned to.
- The Admin Dashboard page lives at `/admin/dashboard` in the frontend routing.
- The stats endpoint is added to the existing analytics app; the final URL path is confirmed during planning to fit the existing URL namespace (e.g., `/api/analytics/admin-stats/`).
- No pagination is needed — the response is two integers.
- The Admin Dashboard shows only aggregate counts, not lists of individual doctors or patients.
- The existing `SummaryCard` component used by the Doctor Dashboard can be reused for the admin metric cards.
