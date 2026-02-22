# Feature Specification: Update Registration Logic

**Feature Branch**: `013-registration-logic`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-1.2 Update Registration Logic - Remove 'patient' from registration role options. Only doctor and admin can register. Update RegisterSerializer validation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registration Restricted to Doctor and Admin Roles (Priority: P1)

A person attempting to register a new platform account can only select `doctor` or `admin` as their role. The `patient` option is not available, and submitting a registration request with `patient` as the role results in a clear validation error. This ensures the registration flow enforces the platform's user model.

**Why this priority**: The registration endpoint is the entry point for all new users. If it allows `patient` registrations, the role change from E-1.1 is bypassed. Enforcing this at the registration layer completes the role restriction end-to-end.

**Independent Test**: Submit a registration request with `role: "patient"` → expect a validation error with a message indicating `patient` is not a valid role. Submit with `role: "doctor"` and `role: "admin"` → both succeed.

**Acceptance Scenarios**:

1. **Given** a registration request with `role: "doctor"`, **When** submitted, **Then** the account is created with the `doctor` role and a success response is returned.
2. **Given** a registration request with `role: "admin"`, **When** submitted, **Then** the account is created with the `admin` role and a success response is returned.
3. **Given** a registration request with `role: "patient"`, **When** submitted, **Then** the system rejects the request with a validation error message indicating `patient` is not a valid registration role.
4. **Given** a registration request with an unrecognised or empty role value, **When** submitted, **Then** the system rejects the request with a descriptive validation error.

---

### User Story 2 - Registration Without Role Defaults to Doctor (Priority: P2)

A person registering a new account without specifying a role has their account created with the `doctor` role by default. This matches the system's primary user type and reduces friction for the most common registration scenario.

**Why this priority**: Defaulting to `doctor` prevents incomplete registrations from failing unexpectedly and makes the API easier to use for the common case. Depends on US1's role restriction being in place.

**Independent Test**: Submit a registration request without any `role` field → account is created with `role: "doctor"`.

**Acceptance Scenarios**:

1. **Given** a registration request with no `role` field provided, **When** submitted with all other required fields, **Then** the account is created successfully with `role: "doctor"`.
2. **Given** a registration request that explicitly sets `role: "doctor"`, **When** submitted, **Then** the account is created with `role: "doctor"` (explicit value matches default).

---

### Edge Cases

- What happens when `role` is provided as an empty string `""`? The system must return a validation error — empty string is not a valid role.
- What happens when `role` is provided in a different case (e.g., `"Doctor"`, `"ADMIN"`)? The system should reject these with a validation error, as roles are case-sensitive lowercase values.
- What happens when the same email is used to register twice? The system must reject the second attempt with an error indicating the email is already taken (existing behaviour, unaffected by this feature).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registration process MUST only accept `doctor` and `admin` as valid role values. Any other value, including `patient`, MUST be rejected with a descriptive validation error.
- **FR-002**: When a registration request is submitted without a role, the system MUST assign `doctor` as the default role and complete the registration successfully.
- **FR-003**: When a registration request is submitted with `role: "patient"`, the system MUST return a validation error with a message that clearly indicates `patient` is not a valid registration role.
- **FR-004**: Validation errors MUST be returned in a structured format that identifies the field name (`role`) and provides a human-readable error message.
- **FR-005**: All other registration validation rules (password strength, email uniqueness, required fields) MUST continue to work without regression.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of registration attempts with `role: "patient"` are rejected with a validation error — zero such registrations succeed.
- **SC-002**: 100% of registration attempts without a `role` field result in accounts with `role: "doctor"`.
- **SC-003**: All validation errors returned for invalid roles include a clear, human-readable message in the `role` field of the error response.
- **SC-004**: All existing registration behaviour for valid roles (`doctor`, `admin`) continues to work correctly — zero regression.

## Assumptions

- This feature formalises the registration-layer enforcement of the role restriction introduced at the model layer in E-1.1. The two features together complete the end-to-end role restriction.
- Role values are case-sensitive and lowercase; `doctor`, `admin` are valid, `Doctor`, `DOCTOR`, `patient`, etc. are not.
- No change is made to who is allowed to trigger the registration endpoint (it remains open to any caller); only the role value submitted is validated.
- No frontend changes are in scope — this feature covers the server-side registration validation only.
