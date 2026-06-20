# Feature Specification: Biometric 6-Axis Field Cleanup

**Feature Branch**: `020-biometric-6-axis`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-3.1 Update BiometricReading Fields: Remove mX, mY, mZ fields from BiometricReading. Keep aX, aY, aZ, gX, gY, gZ. Create and run migration. E-3.2 Update Serializers for 6 Axes: Update BiometricReadingSerializer to only include 6 axis fields. Update any API response that lists sensor fields."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Data Model for Supported Sensors (Priority: P1)

The system should only store the 6 sensor axes the wearable glove hardware actually produces — accelerometer (aX, aY, aZ) and gyroscope (gX, gY, gZ). The magnetometer fields (mX, mY, mZ) are not produced by the hardware and must be removed from the data model via a schema migration so the database reflects reality.

**Why this priority**: The data model is the foundation for all other features — API contracts, serializers, ML inference, and analytics all depend on it. Stale magnetometer fields waste storage, create confusion, and can cause silent bugs in any component that expects only 6 axes. Removing them is the highest-priority cleanup.

**Independent Test**: Can be fully tested by verifying the database schema has no mX, mY, mZ columns and that all data in the 6 retained axis fields is intact. Delivers a clean, accurate schema as its value.

**Acceptance Scenarios**:

1. **Given** the system has a BiometricReading data model with mX, mY, mZ columns, **When** the schema migration is applied, **Then** the columns mX, mY, and mZ no longer exist in the biometric readings table.
2. **Given** the migration has been applied, **When** existing biometric records are retrieved, **Then** all data in aX, aY, aZ, gX, gY, gZ is preserved without loss or corruption.
3. **Given** a new biometric reading is submitted, **When** the system processes it, **Then** only the 6 axis fields (aX, aY, aZ, gX, gY, gZ) are accepted.

---

### User Story 2 - Clean API Responses with 6-Axis Fields Only (Priority: P2)

Any client (frontend, ML pipeline, or third-party integration) consuming the biometric readings API must receive responses that expose exactly the 6 supported axes and nothing more. The biometric reading serializer must be updated to omit mX, mY, mZ from all response payloads.

**Why this priority**: Once the data model is corrected (US1), the API layer must match it. Serializers that still reference removed fields will produce errors or mislead clients. This completes the cleanup at the integration boundary.

**Independent Test**: Can be fully tested by calling the biometric readings API endpoint after US1 is applied and verifying the JSON response contains exactly aX, aY, aZ, gX, gY, gZ and no magnetometer fields.

**Acceptance Scenarios**:

1. **Given** a biometric reading exists in the system, **When** an authorized user requests it via the API, **Then** the response JSON includes exactly the 6 axis fields (aX, aY, aZ, gX, gY, gZ plus standard metadata like id and timestamp) and does not include mX, mY, or mZ.
2. **Given** a client submits a biometric reading payload containing mX, mY, or mZ fields, **When** the system processes the request, **Then** those fields are ignored without causing a server error.
3. **Given** any API endpoint that lists or describes sensor field names, **When** it is called, **Then** the field list references only the 6 supported axes with no magnetometer axes included.

---

### Edge Cases

- What happens when existing records have values in mX, mY, mZ before migration? The migration drops those columns; any stored magnetometer data is discarded as it is legacy/unused.
- What happens if the migration is applied to an empty database? It should succeed without errors.
- What if a component elsewhere in the system (ML pipeline, analytics report) reads mX, mY, or mZ? Such a dependency must be identified and resolved before migration runs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST remove the mX, mY, and mZ fields from the BiometricReading data model.
- **FR-002**: The system MUST retain the aX, aY, aZ, gX, gY, gZ fields without alteration or data loss.
- **FR-003**: A schema migration MUST be created to drop the magnetometer columns from the biometric readings table.
- **FR-004**: The migration MUST complete without corrupting or altering the 6 retained axis field values.
- **FR-005**: The biometric reading serializer MUST expose exactly the 6 axis fields (aX, aY, aZ, gX, gY, gZ) in all read responses — no magnetometer fields.
- **FR-006**: The serializer MUST silently ignore mX, mY, mZ if submitted in a write request, without returning a server error.
- **FR-007**: All API endpoints that enumerate sensor field names MUST reflect only the 6-axis set after this change is applied.

### Key Entities

- **BiometricReading**: Represents a single sensor measurement from the wearable glove. After this change, contains exactly 6 sensor axes: aX, aY, aZ (accelerometer) and gX, gY, gZ (gyroscope). Magnetometer axes (mX, mY, mZ) are removed entirely.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After migration, the biometric readings table contains exactly 6 sensor axis columns (aX, aY, aZ, gX, gY, gZ) and zero magnetometer columns.
- **SC-002**: All existing biometric reading records are fully retrievable after migration with no data corruption in the 6 retained axis fields.
- **SC-003**: 100% of biometric reading API responses contain exactly the 6 axis fields and no magnetometer fields.
- **SC-004**: Submitting a reading payload with magnetometer fields does not cause a server error; the system handles such input gracefully.

## Assumptions

- The wearable gloves never produce mX, mY, mZ data; any values stored in those columns are legacy or test data that can be safely discarded.
- No other component (ML models, analytics, reports, real-time pipeline) reads the magnetometer fields. If any such dependency is discovered during implementation, it must be resolved before the migration is applied.
- The migration will run as a single, non-destructive step (column drop) against the PostgreSQL database.
- "Update any API response that lists sensor fields" refers to the BiometricReadingSerializer and any endpoint that explicitly enumerates axis field names.
