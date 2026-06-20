# Feature Specification: Staff (Doctor) Management

**Feature Branch**: `047-doctor-management`
**Created**: 2026-06-14
**Status**: Draft
**Input**: User description: "Staff Management — doctor list table (name, assigned patient count, account status), Add/Edit Doctor modal form (name, email, password, status), deactivate/reactivate toggle per row, and admin endpoints: POST create doctor, PATCH update/toggle doctor, GET list doctors with patient_count."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View the doctor roster (Priority: P1)

As a center administrator, I want to see a table of every doctor in the center showing each doctor's name, how many patients are assigned to them, and whether their account is active, so I can understand staff workload and account status at a glance.

**Why this priority**: The roster is the foundation of staff management. Without the ability to *see* the doctors and their state, none of the other management actions (adding, editing, deactivating) have a surface to act on. This story alone delivers value: an admin can audit staff and patient distribution.

**Independent Test**: Log in as an admin, open the Staff Management page, and confirm a table renders one row per doctor with three readable columns — name, assigned patient count, and account status (Active/Inactive). A non-admin user attempting to load the same data is denied.

**Acceptance Scenarios**:

1. **Given** an admin is logged in and the center has several doctors, **When** the admin opens the Staff Management page, **Then** a table lists every doctor with their full name, assigned patient count, and account status.
2. **Given** a doctor has no patients assigned, **When** the roster loads, **Then** that doctor's patient count shows `0` (not blank).
3. **Given** a doctor account has been deactivated, **When** the roster loads, **Then** that doctor's status displays as Inactive and is visually distinguishable from active doctors.
4. **Given** a non-admin (doctor) user, **When** they request the doctor roster, **Then** the request is rejected and no roster data is returned.
5. **Given** the center has no doctors yet, **When** an admin opens the page, **Then** an empty-state message is shown instead of an empty table.

---

### User Story 2 - Add and edit doctor accounts (Priority: P2)

As a center administrator, I want to create a new doctor account and edit an existing doctor's details through a single modal form (name, email, password, status), so I can onboard new staff and correct their information without leaving the roster.

**Why this priority**: Onboarding new doctors and fixing their details is the primary write capability of staff management. It depends on the roster (P1) being present as the launch point, but delivers the core administrative workflow.

**Independent Test**: From the roster, an admin opens the "Add Doctor" form, submits valid name/email/password/status, and the new doctor appears in the roster. Selecting an existing doctor opens the same form pre-filled, and saving changes updates that doctor's row.

**Acceptance Scenarios**:

1. **Given** an admin on the roster, **When** they choose "Add Doctor", fill in a unique email, name, password, and status, and submit, **Then** a new doctor account is created and appears in the roster with patient count `0`.
2. **Given** an admin editing an existing doctor, **When** they open the form, **Then** the form is pre-filled with that doctor's current name, email, and status (the password field is left blank and is optional on edit).
3. **Given** an admin submits the Add form with an email that already belongs to another user, **When** they submit, **Then** the system rejects the submission with a clear "email already in use" message and no account is created.
4. **Given** an admin submits the form with a missing required field (name or email, or password when adding), **When** they submit, **Then** validation messages identify the missing fields and nothing is saved.
5. **Given** an admin edits a doctor and leaves the password blank, **When** they save, **Then** the doctor's other details update and the existing password remains unchanged.
6. **Given** a successful create or edit, **When** the form closes, **Then** the roster reflects the change without requiring a manual full-page reload.

---

### User Story 3 - Deactivate and reactivate doctors (Priority: P3)

As a center administrator, I want to toggle a doctor's account between active and inactive directly from their row in the roster, so I can revoke or restore a doctor's access without deleting their account or their patient history.

**Why this priority**: Deactivation is a safety and lifecycle control (e.g., a doctor leaves the center) that builds on the roster and reuses the same status concept as the form. It is valuable but secondary to seeing and creating doctors.

**Independent Test**: From the roster, an admin clicks the deactivate action on an active doctor's row; the row updates to Inactive. Clicking reactivate on an inactive doctor returns it to Active. A deactivated doctor can no longer sign in.

**Acceptance Scenarios**:

1. **Given** an active doctor in the roster, **When** the admin triggers the deactivate action on that row, **Then** the doctor's status becomes Inactive and the action toggles to a reactivate control.
2. **Given** an inactive doctor in the roster, **When** the admin triggers the reactivate action, **Then** the doctor's status becomes Active.
3. **Given** a doctor has just been deactivated, **When** that doctor attempts to sign in, **Then** their sign-in is refused.
4. **Given** a deactivated doctor with assigned patients, **When** the account is deactivated, **Then** the doctor's assigned patient records and assignments are preserved (deactivation is not deletion).
5. **Given** an admin toggles a doctor's status, **When** the action completes, **Then** the new status is reflected in the row without a manual full-page reload.

---

### Edge Cases

- **Duplicate email on create**: Submitting an email already used by any account (doctor or admin) is rejected with a clear message; no partial account is created.
- **Missing password on create**: Creating a doctor with a missing password is rejected; password rules follow the platform's existing account standards.
- **Editing email to one already in use**: Changing a doctor's email to an address owned by another account is rejected.
- **Self-action by admin**: The management surface lists doctor-role accounts only, so an admin cannot accidentally deactivate their own admin account from this screen.
- **Patient count accuracy**: A doctor's patient count reflects currently assigned patients; reassigning or removing a patient updates the count on the next roster load.
- **Concurrent edits**: If two admins edit the same doctor, the last successful save wins; no data corruption results.
- **Backend unreachable**: If the roster or a save/toggle request fails, the admin sees an error state and the page does not crash.
- **Non-admin access**: Any non-admin request to list, create, update, or toggle a doctor is denied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an admin-only roster of all doctor accounts in the center, each entry exposing the doctor's full name, assigned patient count, and account status (active/inactive).
- **FR-002**: System MUST compute each doctor's assigned patient count from current doctor–patient assignments and return it alongside the doctor in the roster.
- **FR-003**: System MUST allow an admin to create a new doctor account by providing name, email, password, and initial status.
- **FR-004**: System MUST enforce email uniqueness across all accounts when creating or editing a doctor, rejecting duplicates with a clear error.
- **FR-005**: System MUST allow an admin to edit an existing doctor's name, email, and status; the password field is optional on edit and, when left blank, leaves the existing password unchanged.
- **FR-006**: System MUST allow an admin to toggle a doctor's account status between active and inactive from the roster without deleting the account.
- **FR-007**: System MUST prevent a deactivated doctor from signing in while preserving that doctor's data and patient assignments.
- **FR-008**: System MUST restrict every staff-management capability (view roster, create, edit, toggle status) to admin-role users and deny all others.
- **FR-009**: System MUST present a single form used for both adding and editing a doctor, pre-filling existing values when editing and starting blank when adding.
- **FR-010**: System MUST validate required fields (name, email, and password on create) before saving and surface field-level validation messages.
- **FR-011**: System MUST reflect successful create, edit, and status-toggle actions in the roster without requiring a manual full-page reload.
- **FR-012**: System MUST show an empty-state message when no doctors exist and an error state when roster or action requests fail.
- **FR-013**: System MUST show an assigned patient count of zero for newly created doctors with no assignments.

### Key Entities *(include if feature involves data)*

- **Doctor account**: A staff member who can sign in and be assigned patients. Key attributes: full name, email (unique login identifier), account status (active/inactive), role (doctor). Has zero or more patient assignments.
- **Doctor–patient assignment**: The link that associates a patient with a doctor. Used to derive a doctor's assigned patient count. Preserved when a doctor is deactivated.
- **Administrator**: The privileged user who manages doctor accounts. Not listed in the doctor roster and not the target of staff-management actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin can view the complete doctor roster with name, patient count, and status for every doctor in a single screen, with the roster loading in under 2 seconds for a center of up to 200 doctors.
- **SC-002**: An admin can create a new doctor account in under 60 seconds from opening the form to seeing the new doctor in the roster.
- **SC-003**: 100% of duplicate-email and missing-required-field submissions are rejected with an actionable message and no account is created or corrupted.
- **SC-004**: An admin can deactivate or reactivate any doctor in two interactions or fewer (open row action, confirm), and the status change is visible in the roster immediately.
- **SC-005**: 100% of non-admin attempts to view or modify doctor accounts are denied.
- **SC-006**: A deactivated doctor is unable to sign in on their next attempt, while their assigned patients and history remain intact.

## Assumptions

- **Doctors are existing user accounts**: A "doctor" is an existing platform user account with the doctor role; this feature manages those accounts and does not introduce a separate staff entity.
- **Name is the person's full name**: "Name" in the form and table refers to the doctor's full name as stored on their account; how it is split or combined internally is an implementation detail.
- **Account status maps to active/inactive sign-in capability**: "Status" means whether the doctor can authenticate; an inactive doctor is blocked from signing in but is not deleted.
- **Patient count is assignment-based**: A doctor's "assigned patient count" is the number of patients currently linked to that doctor through patient assignments.
- **Admin-only scope**: All capabilities in this feature are exclusively for admin-role users, consistent with the platform's existing role model. The roster lists only doctor-role accounts.
- **No bulk operations**: Creating, editing, and toggling act on one doctor at a time; bulk import/deactivation is out of scope.
- **No hard delete**: This feature does not provide permanent deletion of doctor accounts; lifecycle is managed via active/inactive status.
- **Password rules reuse platform standards**: Password validation for new doctors follows the platform's existing account/password policy rather than introducing new rules.
