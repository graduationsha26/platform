# Feature Specification: Patient Distribution (Admin)

**Feature Branch**: `048-patient-distribution`
**Created**: 2026-06-14
**Status**: Draft
**Input**: User description: "7.1 Register New Patient form (admin-side) with doctor assignment dropdown (RegisterPatientForm). 7.2 Full patient list table (admin view) showing all patients across the center with their assigned doctor (AdminPatientTable). 7.3 POST /api/admin/patients/ to register a new patient (admin role required). 7.4 POST /api/admin/patients/<id>/assign/ to assign or reassign a patient to a doctor. 7.5 GET /api/admin/patients/ returning all center-wide patients with their assigned doctor info."

## User Scenarios & Testing *(mandatory)*

This feature gives the **administrator** (institutional manager / receptionist role) the tools to oversee patient distribution across the whole center: see every patient and which doctor cares for them, register newly arriving patients and hand them to a doctor, and move a patient from one doctor to another. Doctors only ever see their own assigned patients; the administrator sees the entire center.

### User Story 1 - Center-wide patient roster (Priority: P1)

As an administrator, I want to see a single table of every patient registered at the center alongside the doctor each one is assigned to, so that I understand how patients are distributed across the medical staff and can spot patients who have no doctor.

**Why this priority**: This is the foundational oversight view and the simplest standalone slice of value. Without it the administrator has no visibility into the center's caseload. It is viable on its own as an MVP — even before registration or reassignment exist, simply seeing the distribution is useful.

**Independent Test**: Log in as an administrator and open the patient distribution page. Verify every patient in the center appears (not just one doctor's patients), each row shows the patient's name and their assigned doctor, and patients with no doctor are clearly marked as unassigned.

**Acceptance Scenarios**:

1. **Given** the center has patients assigned to several different doctors, **When** the administrator opens the patient distribution page, **Then** all patients across all doctors are listed in one table, each showing the assigned doctor's name.
2. **Given** a patient exists with no doctor assignment, **When** the administrator views the roster, **Then** that patient appears with a clear "Unassigned" indicator instead of a doctor name.
3. **Given** a doctor is logged in instead of an administrator, **When** they attempt to open the center-wide roster, **Then** access is denied.
4. **Given** the center has more patients than fit on one screen, **When** the administrator views the roster, **Then** results are paginated and the total patient count is shown.

---

### User Story 2 - Register a new patient with doctor assignment (Priority: P2)

As an administrator, I want to register a newly arriving patient by entering their details and choosing which doctor to assign them to from a dropdown, so that incoming patients are immediately placed under a doctor's care without needing the doctor to do it themselves.

**Why this priority**: Registration is the primary intake workflow, but it builds on the roster (a newly registered patient should appear there). It is the second most valuable slice and depends conceptually on US1 being the place results are confirmed.

**Independent Test**: As an administrator, open the Register New Patient form, fill in the patient's details, select a doctor from the dropdown, and submit. Verify the patient is created, appears in the center-wide roster, and is shown as assigned to the chosen doctor.

**Acceptance Scenarios**:

1. **Given** the administrator is on the Register New Patient form, **When** they enter valid patient details, pick a doctor from the dropdown, and submit, **Then** the patient is created and assigned to that doctor.
2. **Given** the doctor dropdown, **When** the administrator opens it, **Then** it lists the doctors available for assignment (active doctor accounts).
3. **Given** the administrator submits the form with a required field missing, **When** the form is validated, **Then** a clear validation message is shown and no patient is created.
4. **Given** the administrator submits without choosing a doctor, **When** the form is validated, **Then** the system follows the defined rule for unassigned registration (see Assumptions) — creating the patient as unassigned.
5. **Given** a doctor (non-admin) attempts to register a patient through the admin registration path, **When** the request is made, **Then** it is denied.

---

### User Story 3 - Assign or reassign a patient to a doctor (Priority: P3)

As an administrator, I want to move an existing patient from one doctor to another (or assign a doctor to a previously unassigned patient), so that I can rebalance caseloads, cover for an absent doctor, or correct a wrong assignment.

**Why this priority**: Reassignment is a maintenance/correction capability that is valuable but less frequent than viewing and intake. It depends on patients already existing (US1/US2).

**Independent Test**: As an administrator, pick an existing patient assigned to Doctor A and reassign them to Doctor B. Verify the roster now shows Doctor B for that patient and that Doctor A no longer has them, and that the patient's medical record and history are otherwise unchanged.

**Acceptance Scenarios**:

1. **Given** a patient currently assigned to Doctor A, **When** the administrator reassigns them to Doctor B, **Then** the patient is now assigned only to Doctor B and no longer to Doctor A.
2. **Given** a patient with no doctor, **When** the administrator assigns them to a doctor, **Then** the patient becomes assigned to that doctor.
3. **Given** a reassignment request naming a doctor that does not exist or is not a valid doctor account, **When** it is submitted, **Then** it is rejected with a clear error and the existing assignment is unchanged.
4. **Given** a patient is reassigned, **When** the change completes, **Then** the patient's profile data (name, date of birth, notes, history) is preserved unchanged.

---

### Edge Cases

- **Unassigned patients**: Patients with no doctor assignment must still appear in the center-wide roster, marked clearly as unassigned, never hidden.
- **Reassign to the same doctor**: Reassigning a patient to the doctor they are already assigned to is a no-op and must succeed without creating a duplicate or an error.
- **Inactive / deactivated doctor**: A doctor whose account has been deactivated should not be offered as a new assignment target; existing patients already assigned to a now-inactive doctor still display that doctor on the roster (history is not rewritten).
- **Patient with multiple historical assignments**: If the underlying data ever holds more than one doctor for a patient, the roster must show a single, well-defined "assigned doctor" (see Assumptions) rather than duplicating the patient row.
- **Reassigning a non-existent patient**: An assignment request for a patient ID that does not exist returns a not-found error.
- **Empty center**: When no patients are registered yet, the roster shows a clear empty state, not an error.
- **Concurrent reassignment**: Two administrators reassigning the same patient at nearly the same time must converge to a single, consistent assigned doctor without leaving the patient assigned to two doctors.
- **Non-admin access**: All three capabilities (roster, register, reassign) are administrator-only; doctors and unauthenticated users are denied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide administrators a center-wide patient roster listing every patient registered at the center, regardless of which doctor (if any) they are assigned to.
- **FR-002**: Each roster entry MUST display the patient's name and their currently assigned doctor, showing a clear "Unassigned" indicator when the patient has no doctor.
- **FR-003**: The system MUST restrict the center-wide roster, patient registration, and reassignment capabilities to administrator accounts only; doctors and unauthenticated users MUST be denied.
- **FR-004**: The system MUST allow an administrator to register a new patient by providing the patient's details and selecting an assigned doctor.
- **FR-005**: The patient registration interface MUST present a dropdown of doctors eligible for assignment (active doctor accounts) from which the administrator chooses.
- **FR-006**: On successful registration, the system MUST create the patient record and record the patient's assignment to the chosen doctor so that the patient immediately appears on both the center-wide roster and the assigned doctor's own patient list.
- **FR-007**: The system MUST validate patient registration input and reject submissions missing required patient details with a clear, field-level error, creating no patient record on failure.
- **FR-008**: The system MUST allow an administrator to assign or reassign an existing patient to a doctor.
- **FR-009**: Reassigning a patient MUST result in the patient being assigned to exactly one doctor — the newly chosen one — and no longer assigned to any previous doctor.
- **FR-010**: The system MUST reject assignment requests that reference a non-existent patient or an invalid/non-doctor assignment target, leaving any existing assignment unchanged.
- **FR-011**: Assignment and reassignment MUST preserve all of the patient's existing profile data and clinical history; only the assigned doctor changes.
- **FR-012**: The center-wide roster MUST paginate large result sets and expose the total patient count to the administrator.
- **FR-013**: The system MUST return clear, consistent error messages for denied access, validation failures, and not-found conditions across all three capabilities.

### Key Entities *(include if feature involves data)*

- **Patient**: A person receiving care at the center. Key attributes for this feature: name, the staff member who registered them, and clinical details captured at intake. Already exists in the system; this feature adds an admin-side intake path and center-wide visibility.
- **Doctor**: A medical-professional staff account. Serves as the assignment target. Only active doctor accounts are offered for new assignments.
- **Patient–Doctor Assignment**: The relationship linking a patient to the doctor responsible for them, including who created the assignment and when. Drives both the center-wide roster's "assigned doctor" column and each doctor's own patient list. For this feature a patient is treated as having at most one effective assigned doctor.
- **Administrator**: The institutional manager / receptionist account that performs registration and distribution. Has center-wide visibility, unlike doctors who see only their own patients.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can view the complete center-wide patient roster, with each patient's assigned doctor (or "Unassigned") visible, in a single page load.
- **SC-002**: An administrator can register a new patient and assign them to a doctor in under 1 minute, and the patient appears on the center-wide roster immediately afterward.
- **SC-003**: 100% of patients registered at the center appear on the administrator's roster — no patient is omitted because of which doctor they belong to or because they are unassigned.
- **SC-004**: After a reassignment, the patient appears under the new doctor and no longer under the previous doctor in 100% of cases, with no duplicate patient rows.
- **SC-005**: 100% of attempts by non-administrator (doctor or unauthenticated) users to access the center-wide roster, registration, or reassignment are denied.
- **SC-006**: Reassigning a patient changes only the assigned doctor; the patient's name, intake details, and clinical history are unchanged in 100% of cases.

## Assumptions

- **One effective doctor per patient**: For distribution purposes a patient has at most one assigned doctor. "Reassign" replaces the existing assignment rather than adding a second. The roster shows that single assigned doctor, or "Unassigned" when none exists.
- **Roster scope**: The center-wide roster lists patient accounts across the whole center; it is not filtered to the requesting administrator. Doctors continue to use their existing, separate, own-patients view.
- **Doctor dropdown contents**: The assignment dropdown offers active doctor-role accounts only; deactivated doctors are excluded as new-assignment targets but may still appear as the historical assignee on already-assigned patients.
- **Registration without a doctor**: The default rule is that an administrator may register a patient as **Unassigned** (doctor selection is optional at registration) and assign a doctor later via reassignment; the roster's Unassigned indicator and FR-002 support this. If a stricter "doctor required at registration" rule is preferred, it can be enforced in the form without changing the data model.
- **Patient identity & intake fields**: Registration reuses the center's existing patient profile fields (name, date of birth, contact details, clinical notes). No new patient attributes are introduced by this feature.
- **Assignment authorship**: The system records that an assignment was made during admin distribution in a way that keeps the assignment valid; the administrator is not misrepresented as the treating doctor, and the existing "made by a doctor" clinical semantics of the assignment record are honored.
- **No hard delete**: This feature does not remove patients or doctors. Reassignment only moves the relationship; it never deletes patient data.
- **Local development scope**: Single center, local development only, consistent with the platform constitution (no multi-tenant or production deployment concerns in scope).
