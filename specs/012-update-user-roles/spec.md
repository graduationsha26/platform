# Feature Specification: Update User Model Roles

**Feature Branch**: `012-update-user-roles`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-1.1 Update User Model Roles - Change User.role choices from ['patient','doctor','admin'] to ['doctor','admin']. Remove 'patient' choice. Update default role to 'doctor'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Role Selection Restricted to Doctor and Admin (Priority: P1)

An administrator or system component that creates new user accounts can only assign one of two valid roles: `doctor` or `admin`. The `patient` role is no longer a valid option. Attempting to create or update a user with the `patient` role is rejected with a clear error.

**Why this priority**: This is the core change — restricting the valid role set directly controls who can access the platform and with what permissions. All downstream behavior depends on this constraint being enforced correctly.

**Independent Test**: Can be fully tested by attempting to create a user with each role value (`doctor`, `admin`, and `patient`) and verifying that only the first two are accepted, while `patient` is rejected.

**Acceptance Scenarios**:

1. **Given** a new user is being created, **When** the role `doctor` is specified, **Then** the user is created successfully with the `doctor` role.
2. **Given** a new user is being created, **When** the role `admin` is specified, **Then** the user is created successfully with the `admin` role.
3. **Given** a new user is being created, **When** the role `patient` is specified, **Then** the system rejects the request with a validation error indicating `patient` is not a valid role.
4. **Given** an existing user, **When** an attempt is made to update their role to `patient`, **Then** the system rejects the update with a validation error.

---

### User Story 2 - New Users Default to Doctor Role (Priority: P2)

When a new user account is created without an explicitly specified role, the system automatically assigns the `doctor` role as the default. This removes the need for administrators to always specify the role explicitly when creating standard practitioner accounts.

**Why this priority**: The default role simplifies the common case (creating doctor accounts) and reduces the chance of misconfiguration. It depends on Story 1's valid role set being established first.

**Independent Test**: Can be fully tested by creating a new user without specifying any role and verifying the assigned role is `doctor`.

**Acceptance Scenarios**:

1. **Given** a new user creation request with no role specified, **When** the user is created, **Then** the user's role is set to `doctor`.
2. **Given** a new user creation request with the role explicitly set to `doctor`, **When** the user is created, **Then** the user's role is set to `doctor`.

---

### Edge Cases

- What happens to existing users in the system who currently have the `patient` role? They must be handled (migrated or flagged) before the restriction takes effect, as this is a potentially breaking change for existing data.
- What happens when an API request includes `patient` as the role value? The system must return a validation error, not silently coerce or ignore the value.
- What happens if no users currently have the `patient` role? The change is non-breaking and only affects validation going forward.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST restrict valid user role choices to `doctor` and `admin` only. Any other role value MUST be rejected as invalid.
- **FR-002**: The system MUST reject any attempt to create a new user with the role value `patient`, returning a descriptive validation error to the caller.
- **FR-003**: The system MUST reject any attempt to update an existing user's role to `patient`, returning a descriptive validation error.
- **FR-004**: When a new user is created without specifying a role, the system MUST assign `doctor` as the default role automatically.
- **FR-005**: The valid role enumeration MUST contain exactly two values: `doctor` and `admin`.

### Key Entities

- **User**: Represents a platform user (doctor or administrator). Has a `role` attribute that determines access level and permissions. Valid roles are now limited to `doctor` and `admin` only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of user creation and update operations that specify `patient` as the role are rejected with a validation error — zero such operations succeed.
- **SC-002**: 100% of user creation operations without an explicit role result in the user being assigned the `doctor` role.
- **SC-003**: The valid role options in any user management interface or API show exactly two choices: `doctor` and `admin`.
- **SC-004**: All existing functionality for `doctor` and `admin` role users continues to work without regression after the change is applied.

## Assumptions

- Existing users with `patient` role (if any exist in the system) are out of scope for this feature and are handled as a separate data migration task.
- No existing platform feature requires the `patient` role to function; all functionality has already been scoped to `doctor` and `admin` users.
- The change applies to all new user creation and role-update operations from the point of deployment onward.
