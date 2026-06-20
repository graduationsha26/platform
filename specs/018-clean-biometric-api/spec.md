# Feature Specification: Remove Flex Fields from BiometricReading API Layer

**Feature Branch**: `018-clean-biometric-api`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-2.2 Remove Flex from Serializers & Views — Remove flex_1-flex_5 from BiometricReadingSerializer fields. Update any view that references flex data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Data Contract (Priority: P1)

Any system component that reads or writes biometric reading data through the platform's data contract (serializer) should only see and provide the six meaningful sensor fields. There should be no placeholder flex fields (flex_1 through flex_5) in the data contract — not as accepted inputs, not as returned outputs, not as validation targets.

A clean data contract protects downstream consumers (analytics pipelines, real-time dashboards, ML inference) from relying on meaningless fields and ensures the API surface matches what the underlying data model actually stores.

**Why this priority**: The data contract is the authoritative interface for biometric reading data. If flex fields appear in it, consumers may begin relying on them, creating hidden dependencies on fields that carry no information. Removing them from the contract eliminates this risk.

**Independent Test**: Can be fully tested by inspecting the BiometricReading data contract definition. Success means: (1) flex_1 through flex_5 are absent from the list of accepted and returned fields, and (2) the contract includes only the six sensor fields plus metadata.

**Acceptance Scenarios**:

1. **Given** the BiometricReading data contract, **When** a consumer lists the available fields, **Then** none of flex_1, flex_2, flex_3, flex_4, or flex_5 appear.
2. **Given** a request to store a biometric reading that includes a flex field value, **When** the system processes the request, **Then** the flex field is ignored or rejected — it is not stored or returned.
3. **Given** a stored BiometricReading record, **When** the system returns it through the data contract, **Then** the response contains only sensor fields (aX, aY, aZ, gX, gY, gZ) and metadata — no flex fields.

---

### User Story 2 - Clean Request Handling (Priority: P2)

Any request-handling layer that accepts or returns biometric reading data must be consistent with the cleaned data contract. No handler should reference flex_1 through flex_5 when filtering, sorting, validating, or responding to requests.

**Why this priority**: Even if the data contract is correct, a handler that internally references flex fields will produce errors or incorrect behavior at runtime. Consistency between the data contract and all handlers is required for the system to function correctly.

**Independent Test**: Can be fully tested by submitting requests for biometric reading data and verifying the response contains no flex fields and no errors related to missing or unexpected flex columns.

**Acceptance Scenarios**:

1. **Given** the biometric reading request handler, **When** a request to list or retrieve BiometricReading records is made, **Then** the response contains no flex fields and no server errors.
2. **Given** no flex fields exist in the data store, **When** a handler attempts to filter or sort by flex fields, **Then** the system returns a clear error rather than silently failing.
3. **Given** a request handler that previously referenced flex_1..flex_5, **When** the cleanup is applied, **Then** all handler logic operates correctly using only the six sensor fields.

---

### Edge Cases

- What happens if an existing data contract definition lists flex_1..flex_5 in its field configuration? Those entries must be removed so they are no longer part of input validation or output serialization.
- What happens if a request handler is not yet created (no current handler for BiometricReading)? In that case, ensure the handler is created without flex field references from the start.
- What happens if a consumer sends a request body that includes flex field values? The system must ignore or reject those values rather than storing them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The BiometricReading data contract MUST NOT include flex_1, flex_2, flex_3, flex_4, or flex_5 in its list of accepted input fields.
- **FR-002**: The BiometricReading data contract MUST NOT include flex_1 through flex_5 in its list of returned output fields.
- **FR-003**: Any request handler that processes BiometricReading data MUST NOT reference flex_1 through flex_5 in its filtering, sorting, validation, or response logic.
- **FR-004**: The system MUST continue to accept and return the six sensor fields (aX, aY, aZ, gX, gY, gZ) correctly after the cleanup.
- **FR-005**: A complete audit of all data contract definitions and request handlers related to BiometricReading MUST confirm zero flex field references after this change.

### Key Entities

- **BiometricReading Data Contract**: The definition that governs what fields are accepted as input and returned as output when consumers interact with BiometricReading records. After this change, it exposes only: patient reference, timestamp, aX, aY, aZ, gX, gY, gZ.
- **BiometricReading Request Handler**: The component that receives, validates, and responds to requests for BiometricReading data. After this change, it operates exclusively on the six sensor fields and metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 out of 5 flex fields (flex_1 through flex_5) appear in the BiometricReading data contract definition.
- **SC-002**: 0 code references to flex_1 through flex_5 remain in any serializer or view file related to BiometricReading.
- **SC-003**: 100% of BiometricReading read and write operations succeed without errors after the cleanup.
- **SC-004**: The BiometricReading data contract and request handlers are consistent with the data model — both expose exactly the same set of fields.

## Assumptions

- The BiometricReading data model has already had flex_1 through flex_5 removed (Feature E-2.1). This feature aligns the API layer with that cleaned model.
- The BiometricReadingSerializer may not yet exist in the codebase — if it does not exist, it must be created without flex fields from the start (no migration needed for this layer).
- Any existing BiometricReading views that reference flex fields must be updated; if no such views exist yet, new views must be created without flex field references.
- No data consumers currently depend on flex fields in the BiometricReading API contract.

## Scope

**In scope**:
- BiometricReadingSerializer field list (remove or never include flex_1..flex_5)
- Any BiometricReading views/handlers that reference flex fields (update or create clean)
- Post-cleanup audit confirming zero flex references in the API layer

**Out of scope**:
- BiometricSession serializers and views (separate model, separate contract)
- Database schema changes (covered by Feature E-2.1)
- Frontend changes (the frontend does not yet consume BiometricReading data directly)
