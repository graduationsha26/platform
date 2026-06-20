# Feature Specification: Personalized Doctor Dashboard Greeting

**Feature Branch**: `001-doctor-greeting`  
**Created**: 2026-06-14  
**Status**: Draft  
**Input**: User description: "1.1 Personalized. Read authenticated doctor's name from auth context/JWT and render it, DoctorDashboard header, Greeting in the dashboard header component. 1.2 Personalized. Ensure GET /api/auth/me/ returns first_name, last_name for the logged-in user."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Personalized Greeting in Dashboard Header (Priority: P1)

When a doctor logs in and navigates to the dashboard, they see a personalized greeting in the header that includes their first and last name (e.g., "Welcome, Dr. Ahmed Hassan"). This confirms the doctor is authenticated as the correct user and creates a welcoming, professional experience.

**Why this priority**: This is the primary visible outcome of the feature. Without this, the doctor has no identity confirmation on the dashboard and the feature delivers no user-facing value.

**Independent Test**: Can be tested by logging in as a specific doctor, navigating to the dashboard, and verifying the header displays that doctor's correct name.

**Acceptance Scenarios**:

1. **Given** a doctor is logged in, **When** they open the dashboard, **Then** the header displays a greeting that includes their first and last name.
2. **Given** a doctor with first name "Ahmed" and last name "Hassan" is logged in, **When** the dashboard loads, **Then** the greeting contains "Ahmed Hassan" (or a styled variant such as "Dr. Ahmed Hassan").
3. **Given** the doctor's name has not yet been fetched, **When** the dashboard is rendering, **Then** a neutral loading placeholder is shown rather than blank or broken text.
4. **Given** the auth session has expired, **When** the dashboard attempts to load, **Then** the doctor is redirected to the login screen rather than showing a broken greeting.

---

### User Story 2 - Auth Endpoint Returns Doctor Name Fields (Priority: P1)

The backend endpoint that returns the profile of the currently authenticated user must include the doctor's first name and last name, so the frontend can personalize the UI without making separate additional requests.

**Why this priority**: Without this data from the backend, the frontend cannot display the personalized greeting. This is the foundational data requirement that enables User Story 1.

**Independent Test**: Can be tested independently by calling the user profile endpoint with a valid authentication token and verifying the response body includes first_name and last_name fields.

**Acceptance Scenarios**:

1. **Given** a doctor is authenticated, **When** the user profile endpoint is called with a valid token, **Then** the response includes first_name and last_name fields with the correct values for that doctor.
2. **Given** a doctor whose first_name is "Nour" and last_name is "Khalil", **When** the profile endpoint is called with their token, **Then** the response body contains `"first_name": "Nour"` and `"last_name": "Khalil"`.
3. **Given** an unauthenticated request is made, **When** the profile endpoint is called without a valid token, **Then** access is denied with an appropriate authorization error response.

---

### Edge Cases

- What happens when the doctor's first_name or last_name is blank or missing in the database?
- How does the greeting display if only the first name is available but the last name is empty?
- What happens if the authentication token is valid but the user profile fetch fails due to a network or server error?
- How does the greeting behave on page refresh vs. client-side navigation to the dashboard?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The user profile endpoint MUST return first_name and last_name for the currently authenticated doctor in its response body.
- **FR-002**: The dashboard header component MUST display a personalized greeting that includes the authenticated doctor's first and last name.
- **FR-003**: The frontend MUST read the doctor's name from the authenticated user's profile (retrieved at or shortly after login) without requiring additional network requests each time the dashboard header renders.
- **FR-004**: The greeting MUST NOT display a blank or visually broken state — a neutral fallback text (e.g., "Doctor") MUST be shown if name fields are unavailable.
- **FR-005**: The user profile endpoint MUST reject unauthenticated requests with an authorization error.

### Key Entities

- **Doctor (User)**: Represents a medical professional. Has first_name and last_name attributes stored in their profile. The dashboard greeting is derived from these fields.
- **Auth Context**: The client-side representation of the authenticated session, which holds the doctor's identity information (including name) and makes it available to UI components without repeated server calls.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of authenticated doctors see their correct first and last name displayed in the dashboard header greeting upon navigating to the dashboard, with no additional action required.
- **SC-002**: The doctor's name appears in the greeting within the same page load as the dashboard — no secondary interaction or page refresh is needed.
- **SC-003**: The user profile endpoint returns first_name and last_name in every successful authenticated response (zero missing fields for valid users).
- **SC-004**: A neutral fallback text is always shown in place of the greeting when name data is unavailable — zero occurrences of a blank or visually broken greeting visible to users.

## Assumptions

- The doctor's first_name and last_name are already stored in the user database for existing accounts — no user profile editing flow is in scope for this feature.
- The frontend has an existing auth context or session mechanism that holds the authenticated user's profile data after login; this feature extends that mechanism to include name fields rather than introducing a new pattern.
- The exact greeting phrase wording (e.g., "Welcome," vs "Good morning,") is an implementation detail and is not constrained by this specification — only the presence of the doctor's name is required.
- Only the `doctor` role is in scope; the `admin` role's dashboard header is out of scope for this feature.
