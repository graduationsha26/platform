# Feature Specification: Update Patient Model

**Feature Branch**: `014-update-patient-model`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-1.3    Update Patient Model    Patient is now a data-only model (no linked User account for patients). Remove user OneToOneField if it points to patient-role users. Keep assigned_doctor FK. Add fields: full_name, phone, notes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Patient Records Exist Without Login Accounts (Priority: P1)

A doctor uses the platform to manage patient clinical records. Patients themselves never log into the system — they are people with a condition who are monitored by doctors. The patient record is a pure data container: it stores clinical information about the patient but is not tied to any login account. Doctors can create, view, and update patient records freely without needing to first create a login account for the patient.

**Why this priority**: This is the core architectural change. The previous model incorrectly linked patient records to user authentication accounts (a concept now removed since "patient" is no longer a valid login role). Until this link is severed, the Patient model carries dead weight that could cause confusion or future bugs.

**Independent Test**: Create a patient record with only clinical information (full name, phone, notes) and no user account reference. The record is saved and retrievable. No user account is required or referenced.

**Acceptance Scenarios**:

1. **Given** the system has no user account for a person, **When** a doctor creates a patient record for that person, **Then** the patient record is saved successfully with no link to any user account.
2. **Given** an existing patient record that previously had a user account link, **When** the system is updated, **Then** the patient record still exists and is fully accessible, with the user account link removed gracefully.
3. **Given** a patient record, **When** a doctor retrieves the record, **Then** no user account information appears — only clinical data is returned.

---

### User Story 2 - Patient Records Store Required Clinical Fields (Priority: P2)

A doctor needs to store key contact and clinical information on each patient record. At minimum, every patient record must contain: the patient's full name, a contact phone number, and free-form clinical notes. These fields must be present and accessible via the patient management interface.

**Why this priority**: Without accurate contact and clinical data, patient records provide no clinical value. This story ensures the data model is fit for purpose.

**Independent Test**: Create a patient record with `full_name`, `phone`, and `notes` populated. Retrieve the record and confirm all three fields are returned correctly. Update each field individually and confirm changes persist.

**Acceptance Scenarios**:

1. **Given** a doctor creates a patient record, **When** they provide full name, phone number, and clinical notes, **Then** all three values are stored and returned on retrieval.
2. **Given** an existing patient record, **When** a doctor updates the phone number or clinical notes, **Then** the updated values are persisted and the other fields remain unchanged.
3. **Given** a patient record is created without phone or notes, **When** the record is retrieved, **Then** phone and notes return as empty (not an error) — only full name is mandatory.

---

### User Story 3 - Patients Remain Assignable to Doctors (Priority: P3)

After removing the user account link, patients must still be assignable to one or more doctors. A doctor can see which patients they are responsible for, and a patient record shows which doctor(s) are managing it.

**Why this priority**: Doctor-patient assignment is the primary operational relationship on the platform. It must be preserved regardless of changes to the authentication link.

**Independent Test**: Assign a patient to a doctor. Retrieve the doctor's patient list — the patient appears. Retrieve the patient record — the assigned doctor appears. Remove the assignment — the patient is no longer in the doctor's list.

**Acceptance Scenarios**:

1. **Given** a patient record exists, **When** a doctor is assigned to the patient, **Then** the assignment is recorded and the patient appears in that doctor's patient list.
2. **Given** a patient with no user account link, **When** a doctor-patient assignment is created, **Then** the assignment is saved successfully — the absence of a user link does not affect assignment.
3. **Given** a patient assigned to a doctor, **When** the patient record is retrieved, **Then** the assigned doctor information is included in the response.

---

### Edge Cases

- What happens if a patient record was previously linked to a user account (legacy data)? The system must gracefully handle removal of that link — existing patient records must remain intact with all clinical data preserved.
- What happens if code elsewhere in the system references the now-removed user link on Patient? Those references must be identified and updated to prevent runtime errors.
- What if `phone` is omitted when creating a patient? Phone should be optional — only full name is required.
- What if `notes` is omitted? Notes should be optional and default to empty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Patient record MUST NOT contain a link to a user authentication account. The `user` relationship (if it exists as a field on Patient) MUST be removed entirely.
- **FR-002**: Every Patient record MUST store a `full_name` field (required, non-empty string identifying the patient).
- **FR-003**: Every Patient record MUST store a `phone` field (optional string for patient contact phone number).
- **FR-004**: Every Patient record MUST store a `notes` field (optional free-text field for clinical observations).
- **FR-005**: The Patient model MUST retain its relationship to doctor(s) — whether via a direct assigned-doctor reference or an assignment relationship. This relationship MUST NOT be removed.
- **FR-006**: Removing the user account link MUST NOT cause data loss — all existing patient records and their clinical data MUST remain intact after the change.
- **FR-007**: All system references to the removed user account link on Patient (in views, serializers, permissions, or other code) MUST be updated so no runtime errors occur.

### Key Entities

- **Patient**: A clinical record representing a person being monitored on the platform. Contains: identity (full name), contact information (phone), clinical observations (notes), and metadata (who created it, when). Has no login credentials — is not a system user. Is associated with one or more doctors.
- **Doctor-Patient Relationship**: The association between a doctor (who has a login account) and a patient record (which does not). Doctors manage and monitor the patients assigned to them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of patient records are accessible after the change — no existing patient data is lost or inaccessible.
- **SC-002**: A doctor can create a complete patient record (with name, phone, notes) in a single operation without any user account reference.
- **SC-003**: 0 runtime errors occur from code paths that previously accessed the user account link on a Patient record — all such references are resolved.
- **SC-004**: Doctor-patient assignments continue to work — a doctor can assign themselves to a patient and see that patient in their list.

## Assumptions

- The `assigned_doctor` reference in the feature description refers to the existing doctor-patient relationship mechanism (whether it is a direct foreign key or a many-to-many junction). The planning phase will determine the current state and whether any change is needed.
- `full_name`, `phone`, and `notes` may already exist on the Patient model under the same or similar field names. The planning phase will verify this and add only missing fields.
- The patient's `phone` field is optional (not all patients have a contact number on file).
- The patient's `notes` field is optional and defaults to empty.
- No frontend changes are in scope for this feature — only the data model and any backend code referencing the removed user link.
- Dependencies: E-1.1 (Update User Model Roles) must be complete, as it removed `patient` from the valid role list, making the user account link on Patient a dead reference.
