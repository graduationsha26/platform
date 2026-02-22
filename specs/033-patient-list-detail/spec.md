# Feature Specification: Patient List & Detail Pages

**Feature Branch**: `033-patient-list-detail`
**Created**: 2026-02-20
**Status**: Draft
**Input**: User description: "N-4.2.2 Patient List and Detail Pages - Paginated patient table with search. Detail page: patient profile and session history. Doctors create/edit patients (no patient self-service)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Search Patient List (Priority: P1)

A doctor navigates to the patients section and sees a paginated table of all their assigned patients. They can type a name into a search box to filter the list, and page through results. Each row shows enough information to identify the patient and navigate to their detail page.

**Why this priority**: The patient list is the central navigation hub — without it, doctors cannot access any individual patient's data. It is the most frequently visited page and the entry point for all patient-related workflows.

**Independent Test**: Can be tested by loading the patient list page with at least one assigned patient and verifying that the table renders rows with patient names, the search field filters results in real time, and pagination controls appear when there are more patients than the page size.

**Acceptance Scenarios**:

1. **Given** a doctor is logged in and has 5 assigned patients, **When** they navigate to the patient list page, **Then** a table is displayed showing all 5 patients with at minimum their full name, date of birth, and last session date.

2. **Given** a doctor is on the patient list page, **When** they type part of a patient's name into the search field, **Then** the table updates to show only matching patients; non-matching patients are hidden.

3. **Given** a doctor has more patients than the page size (e.g., 25 patients, page size 20), **When** they view the first page, **Then** 20 patients are shown and pagination controls allow navigating to the next page.

4. **Given** a doctor has no patients assigned, **When** they view the patient list, **Then** an empty state is displayed with a clear message (e.g., "No patients yet. Add your first patient.") rather than a blank table.

5. **Given** a doctor's search query matches no patients, **When** the table updates, **Then** a "No patients found" message is shown with no table rows.

6. **Given** a doctor is on the patient list, **When** they click a patient's name or row, **Then** they are navigated to that patient's detail page.

---

### User Story 2 - View Patient Detail Page (Priority: P2)

A doctor clicks a patient from the list and is taken to a detail page showing the patient's complete profile (name, date of birth, contact information, medical notes) and a chronological list of their past biometric monitoring sessions. Each session entry shows the date, duration, and ML-predicted tremor severity.

**Why this priority**: The detail page is where doctors review a patient's clinical history and make monitoring decisions. It delivers core medical value and is the destination for most patient list navigations.

**Independent Test**: Can be tested by navigating directly to `/patients/:id` for an existing patient and verifying that the profile section and session history list both render with correct data. Delivers standalone value as a read-only patient record view.

**Acceptance Scenarios**:

1. **Given** a doctor navigates to a patient detail page, **When** the page loads, **Then** the patient's full profile is displayed: full name, date of birth, contact phone (if set), contact email (if set), and medical notes (if set).

2. **Given** a patient has 3 biometric sessions, **When** the doctor views that patient's detail page, **Then** a session history list is shown with 3 entries, each displaying the session date, duration, and ML prediction severity (e.g., "mild", "moderate", "severe" — or "No prediction" if not yet analysed).

3. **Given** a patient has no biometric sessions, **When** the doctor views their detail page, **Then** the session history section shows an empty state message (e.g., "No monitoring sessions recorded yet.").

4. **Given** a doctor attempts to view a detail page for a patient not assigned to them, **When** the page loads, **Then** an access denied message is shown and the patient's data is not displayed.

5. **Given** a patient has more than 10 sessions, **When** the doctor views the detail page, **Then** sessions are paginated with 10 per page and the doctor can navigate between pages.

---

### User Story 3 - Create a New Patient (Priority: P3)

A doctor fills out a form with a new patient's details (name, date of birth, and optionally contact info and medical notes) and submits it. The new patient appears in their patient list and is automatically assigned to the creating doctor.

**Why this priority**: Creating patients is the prerequisite for all patient monitoring work. Without this, the list would always be empty. It is less frequently used than browsing (done once per patient) but essential for the system to hold data.

**Independent Test**: Can be tested by submitting the create-patient form with valid data and verifying that the patient appears in the list and can be navigated to via their detail page. Independently delivers the ability to onboard new patients.

**Acceptance Scenarios**:

1. **Given** a doctor is on the create patient form, **When** they fill in a valid full name and date of birth and submit, **Then** a new patient record is created, the doctor is redirected to that patient's detail page, and the patient appears in their patient list.

2. **Given** a doctor submits the form with the full name field empty, **When** the form is submitted, **Then** validation prevents submission and an error message identifies the missing required field.

3. **Given** a doctor submits the form with a date of birth set to tomorrow's date, **When** the form is submitted, **Then** validation prevents submission and an error message states that date of birth cannot be in the future.

4. **Given** a doctor submits the form with an invalid phone number format, **When** the form is submitted, **Then** validation prevents submission and an error message describes the expected format.

5. **Given** a newly created patient, **When** the creating doctor views their patient list, **Then** that patient is listed (the assignment is automatic and immediate).

---

### User Story 4 - Edit Patient Profile (Priority: P4)

A doctor opens a patient's detail page, clicks an "Edit" button, modifies one or more profile fields (name, DOB, contact info, medical notes), and saves. The patient's detail page reflects the updated information immediately.

**Why this priority**: Profile editing corrects data entry errors and keeps patient records accurate over time. It is less critical than viewing (US2) and creating (US3) but necessary for data quality.

**Independent Test**: Can be tested by loading an existing patient's edit form, changing the medical notes field, saving, and verifying the detail page shows the updated notes. Does not require US3 to be implemented first (a pre-seeded patient can be used).

**Acceptance Scenarios**:

1. **Given** a doctor is on a patient's detail page, **When** they click "Edit", **Then** an edit form is displayed pre-populated with the patient's current profile data.

2. **Given** a doctor edits the medical notes field and clicks "Save", **When** the save completes, **Then** they are returned to the patient's detail page and the updated notes are displayed.

3. **Given** a doctor clears the required full name field and tries to save, **When** the form is submitted, **Then** validation prevents saving and an error message identifies the missing field.

4. **Given** a doctor sets a date of birth to a future date and tries to save, **When** the form is submitted, **Then** validation prevents saving and an error message states the date cannot be in the future.

5. **Given** a doctor tries to access the edit form for a patient not assigned to them, **When** the page loads, **Then** an access denied message is shown and the form is not displayed.

---

### Edge Cases

- What happens when the doctor has no patients? (Empty state on list page — covered in US1)
- What happens when a patient has no sessions? (Empty session history — covered in US2)
- What happens when a search query matches 0 patients? (No-results message — covered in US1)
- What if a doctor tries to navigate directly to another doctor's patient detail URL?
- What if two doctors share the same patient (via assignment)? Both should be able to view but only assigned doctors can edit.
- What if a patient's name contains special characters (e.g., accents, hyphens)?
- What if the session history is very long (hundreds of sessions)? (Pagination — covered in US2)
- What if a required field is submitted as whitespace only?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a paginated list of patients assigned to the logged-in doctor, showing each patient's full name, date of birth, and most recent session date (or "No sessions" if none).
- **FR-002**: The patient list MUST be searchable by patient full name; the list MUST update to show only matching patients as the doctor types.
- **FR-003**: The patient list MUST paginate results with a default page size of 20 patients per page.
- **FR-004**: The patient list MUST display an empty state message when no patients are assigned to the doctor.
- **FR-005**: The system MUST display a patient detail page accessible by patient identifier.
- **FR-006**: The patient detail page MUST show the complete patient profile: full name, date of birth, contact phone (if provided), contact email (if provided), and medical notes (if provided).
- **FR-007**: The patient detail page MUST display a session history list showing all of the patient's biometric sessions, ordered from most recent to oldest, paginated at 10 sessions per page.
- **FR-008**: Each session history entry MUST show at minimum: session date and time, session duration, and ML prediction severity (or "No prediction" if unavailable).
- **FR-009**: Only doctors assigned to a patient MUST be able to view that patient's detail page; attempting to access an unassigned patient's page MUST result in an access denied response.
- **FR-010**: The system MUST provide a form for doctors to create a new patient with the following fields: full name (required), date of birth (required), contact phone (optional), contact email (optional), medical notes (optional).
- **FR-011**: The system MUST validate on creation: full name is non-empty and not whitespace-only; date of birth is a valid date not in the future; contact phone matches a valid phone number format if provided; contact email is a valid email format if provided.
- **FR-012**: A newly created patient MUST be automatically assigned to the doctor who created them.
- **FR-013**: The system MUST provide a form for doctors to edit an existing patient's profile, pre-populated with current values.
- **FR-014**: The same validation rules that apply to patient creation (FR-011) MUST apply to patient editing.
- **FR-015**: Only a doctor assigned to a patient MUST be able to edit that patient's profile.
- **FR-016**: Patients MUST NOT have access to any patient creation, edit, or management interface; these pages are exclusively for doctors.
- **FR-017**: Only authenticated doctors MUST be able to access any patient list, detail, create, or edit page; unauthenticated users are redirected to login.

### Key Entities

- **Patient**: A person receiving tremor treatment under a doctor's care. Profile fields: full name, date of birth, contact phone (optional), contact email (optional), medical notes (optional). Has a creation timestamp and an owning doctor.
- **Doctor-Patient Assignment**: The relationship that grants a doctor access to a patient's records. Created automatically when a doctor creates a patient. Can exist for multiple doctors per patient.
- **Biometric Session**: A timestamped monitoring recording for a patient. Summary attributes relevant to the detail page: session date and time, duration, and ML-predicted tremor severity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A doctor can locate any assigned patient by name in under 10 seconds using the search field.
- **SC-002**: The patient list page loads and displays within 3 seconds for a cohort of up to 100 patients.
- **SC-003**: Search results visibly update within 1 second of the doctor typing in the search field.
- **SC-004**: A doctor can complete new patient registration (filling the form and saving) in under 2 minutes.
- **SC-005**: The patient detail page (profile + session history) loads within 3 seconds.
- **SC-006**: No doctor can view or edit a patient they are not assigned to (0% unauthorised access rate, verified by direct URL navigation attempts).
- **SC-007**: A doctor can update a patient's profile and return to the detail page in under 2 minutes.
- **SC-008**: All required field validation errors are visible to the doctor before they submit (inline, not after page reload).

## Assumptions

- The patient list shows only patients assigned to the logged-in doctor via Doctor-Patient Assignment — not all patients in the system.
- Search is by patient full name only (substring match, case-insensitive); searching by contact email or ID is not in scope.
- "Session history" on the detail page shows summary-level data (date, duration, severity) — detailed sensor waveforms and analytics are handled by the analytics features (N-4.2.x).
- Session history is sorted newest-first (most recent session at the top).
- Deleting patients is out of scope for this feature.
- Patient profile photo or avatar is out of scope.
- Bulk patient import (e.g., CSV upload) is out of scope.
- There is no duplicate-patient prevention by name+DOB; data quality is the doctor's responsibility.
- A patient assigned to multiple doctors: all assigned doctors can view the detail page; any assigned doctor can edit the profile (last write wins, no conflict resolution needed at this stage).
- The admin role's patient management capabilities are handled separately; this feature focuses on the doctor role.
- Session history pagination defaults to 10 sessions per page.
