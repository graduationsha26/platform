# Feature Specification: Update Patient API Permissions

**Feature Branch**: `015-patient-permissions`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-1.4 Update Patient API Permissions Only authenticated doctors/admins can CRUD patients. Remove any patient-self-access logic. Update viewset permissions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Users Can Fully Manage All Patients (Priority: P1)

An admin user needs to view, create, update, and delete any patient record in the system, regardless of which doctor created it. Currently, admin-role users are blocked from the patient management API (only doctors can access it). This story corrects that gap so admins have full, unrestricted patient record access.

**Why this priority**: Admin access is a blocking gap — without it, the platform has no super-user oversight of patient records. This is the core change requested by E-1.4.

**Independent Test**: Log in as an admin-role user → `GET /api/patients/` returns all patients in the system → `POST /api/patients/` creates a patient → `PUT /api/patients/{id}/` and `DELETE /api/patients/{id}/` succeed for any patient.

**Acceptance Scenarios**:

1. **Given** an admin user is authenticated, **When** they request the patient list, **Then** the response contains all patient records in the system (not filtered by creator).
2. **Given** an admin user is authenticated, **When** they create a new patient record, **Then** the record is created successfully and returned with status 201.
3. **Given** an admin user is authenticated, **When** they update or delete any patient (including one created by another doctor), **Then** the operation succeeds.

---

### User Story 2 - Doctor Access Remains Scoped to Their Own Patients (Priority: P2)

A doctor user should continue to see only the patients they created or are assigned to. As permissions are updated to add admin access, doctor scoping must not regress — doctors must never gain visibility into other doctors' patients.

**Why this priority**: Data privacy between doctors is critical. This story ensures the admin addition does not accidentally widen doctor access.

**Independent Test**: Log in as a doctor → `GET /api/patients/` returns only patients created by or assigned to that doctor → Requesting a patient belonging to a different doctor returns 404 (not found in queryset).

**Acceptance Scenarios**:

1. **Given** a doctor is authenticated, **When** they request the patient list, **Then** only patients they created or are assigned to are returned.
2. **Given** a doctor is authenticated, **When** they attempt to access a patient record belonging to another doctor, **Then** the request is rejected (patient not visible in their queryset).
3. **Given** a doctor is authenticated, **When** they create a new patient, **Then** the patient is created with them recorded as the creator.

---

### User Story 3 - Unauthorized Users Are Completely Blocked (Priority: P3)

Any user who is not authenticated, or who holds an unrecognized role, must be denied access to all patient endpoints. This story confirms the hard boundary: only the two explicit roles (doctor, admin) are permitted.

**Why this priority**: Defense in depth — ensures no accidental access path exists for unauthenticated callers or any edge-case role.

**Independent Test**: Send requests to `GET /api/patients/` without authentication token → 401 response. Send with a valid token for a non-doctor, non-admin role → 403 response.

**Acceptance Scenarios**:

1. **Given** no authentication credentials, **When** any request is made to a patient endpoint, **Then** a 401 Unauthorized response is returned.
2. **Given** an authenticated user with neither doctor nor admin role, **When** any request is made to a patient endpoint, **Then** a 403 Forbidden response is returned.

---

### Edge Cases

- What happens when an admin user tries to access a patient that does not exist? → 404 Not Found.
- What happens if a doctor creates a patient and an admin later updates it? → Update succeeds; `created_by` remains the original doctor.
- What happens if a request provides a valid authentication credential but the user account has been deleted from the system? → The request is rejected as unauthorized.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The patient management API MUST deny access to any request that is not authenticated.
- **FR-002**: The patient management API MUST deny access to any authenticated user whose role is neither `doctor` nor `admin`.
- **FR-003**: Admin-role users MUST be able to list, create, retrieve, update, and delete any patient record in the system without restriction.
- **FR-004**: Doctor-role users MUST only be able to access patients they created or are formally assigned to — no cross-doctor data visibility.
- **FR-005**: The system MUST remove all dead code that previously allowed patient-role users to self-access patient records (such code became unreachable after the patient role was removed in a prior change).

### Key Entities

- **Patient**: A data record representing a monitored individual; no longer linked to a user account. Accessible only to authorized staff.
- **Doctor**: A staff user who creates and manages patient records for their own caseload.
- **Admin**: A staff user with full visibility across all patient records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of requests to patient endpoints from unauthenticated callers receive a rejection response — zero unauthorized data leaks.
- **SC-002**: 100% of doctor-role requests are limited to that doctor's own patients — no cross-doctor record leakage.
- **SC-003**: Admin-role users can successfully perform all patient CRUD operations on any patient record — 100% access coverage.
- **SC-004**: Zero dead "patient-self-access" permission code blocks remain in the codebase after the change.

## Assumptions

- The two permitted roles in the system are `doctor` and `admin` (established in a prior change); these are the only roles that should be granted patient record access.
- Admin users see **all** patients (no scoping by assignment or creator) — this is the natural expectation for a super-user role.
- The `doctor` access scoping rule (created_by OR assigned-to) is already implemented correctly and must be preserved unchanged.
- The patient-role user concept no longer exists in the system (removed in E-1.1); dead code referencing it is being cleaned up here.
- No new data fields or API endpoint routes are introduced — this feature is permissions-only.
