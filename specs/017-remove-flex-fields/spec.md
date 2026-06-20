# Feature Specification: Remove Flex Fields from BiometricReading

**Feature Branch**: `017-remove-flex-fields`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-2.1 Remove Flex Fields from BiometricReading - Remove flex_1 through flex_5 FloatFields from BiometricReading model. Create and run migration."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Biometric Data Model (Priority: P1)

The biometric reading record should contain only sensor fields that are actively used by the platform. The five placeholder flex fields (flex_1 through flex_5) are not mapped to any sensor input, not used in any data processing pipeline, and serve no functional purpose. Their presence pollutes the data model, wastes storage, and creates confusion for any developer or analyst working with the data.

Removing these fields produces a leaner, clearer data model that accurately reflects the data the platform actually captures and uses.

**Why this priority**: A clean data model is a prerequisite for reliable analytics, ML feature ingestion, and long-term maintainability. Unused fields are a source of ambiguity and hidden technical debt.

**Independent Test**: Can be fully tested by inspecting the BiometricReading data structure. Success means: (1) no flex_1 through flex_5 fields exist on a BiometricReading record, and (2) the system can create, read, and store BiometricReading records without referencing those fields.

**Acceptance Scenarios**:

1. **Given** the BiometricReading data model, **When** a developer inspects the available fields, **Then** none of flex_1, flex_2, flex_3, flex_4, or flex_5 are present.
2. **Given** a new BiometricReading is created via any data ingestion path, **When** the record is saved, **Then** it contains only the defined sensor fields and no flex placeholder values.
3. **Given** existing BiometricReading records in the database, **When** the schema update is applied, **Then** records remain accessible and complete for all non-flex fields.

---

### User Story 2 - Safe Schema Migration (Priority: P2)

Applying the removal of flex_1 through flex_5 requires a database schema change. This migration must run cleanly against the live database schema, produce the correct updated structure, and leave all existing records intact for the remaining fields.

**Why this priority**: Without a successful schema migration, the data model change is incomplete and the system may behave inconsistently (model code out of sync with database schema).

**Independent Test**: Can be fully tested by running the migration against the current schema and verifying: (1) migration completes without errors, (2) the database table no longer contains the five flex columns, (3) existing records are unaffected in their non-flex columns.

**Acceptance Scenarios**:

1. **Given** the current database schema contains flex_1 through flex_5 columns on the biometric readings table, **When** the migration is applied, **Then** those five columns are removed and the migration reports success.
2. **Given** the migration has run successfully, **When** the system attempts to read or write BiometricReading records, **Then** no errors are raised related to missing or unexpected columns.
3. **Given** the migration has run successfully, **When** a developer inspects the database table, **Then** only the expected sensor columns (and metadata columns) remain.

---

### Edge Cases

- What happens if a BiometricReading record was saved with non-null values in flex_1 through flex_5 before the migration? Those values are discarded when the columns are dropped; this is acceptable since the fields have no defined meaning.
- What happens if code elsewhere in the system references a flex field by name? Any such reference would cause a runtime error after the migration; the scope of this feature includes identifying and removing all such references before the migration runs.
- What happens if the migration fails midway? The migration must be atomic; a partial failure should leave the schema unchanged and the system operational.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The BiometricReading data model MUST NOT define or expose flex_1, flex_2, flex_3, flex_4, or flex_5 fields.
- **FR-002**: The database schema MUST be updated via a formal schema migration to remove the five flex columns from the biometric readings table.
- **FR-003**: The migration MUST be atomic — it either applies completely or leaves the schema unchanged.
- **FR-004**: All existing code paths that read, write, or validate BiometricReading records MUST function correctly after the flex fields are removed (zero regression).
- **FR-005**: Any code reference to flex_1 through flex_5 in models, serializers, views, or API contracts MUST be removed before the migration is applied.

### Key Entities

- **BiometricReading**: A database record representing a single timestamped reading from a patient's wearable sensor. After this change, it contains only the defined raw sensor fields (e.g., accelerometer and gyroscope axes) and standard metadata (patient reference, timestamp). It no longer contains flex_1 through flex_5.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the change is applied, 0 out of 5 flex fields (flex_1 through flex_5) exist on the BiometricReading data model.
- **SC-002**: The database migration completes with 0 errors and removes all 5 flex columns from the biometric readings table.
- **SC-003**: 100% of existing BiometricReading records remain readable after the migration, with no data loss in non-flex columns.
- **SC-004**: All data ingestion, storage, and retrieval operations for BiometricReading records succeed without referencing flex fields after the change.

## Assumptions

- The flex_1 through flex_5 fields are unused placeholder fields with no active data mapped to them; any values stored in these columns have no business or operational meaning and may be safely discarded.
- No downstream system (analytics pipeline, ML inference, reporting) currently reads or depends on these fields.
- The database schema currently has a biometric_readings table with flex_1 through flex_5 columns (i.e., the BiometricReading model was previously created with these fields).
- Dropping the columns is non-reversible in the forward migration; a rollback migration is out of scope for this engineering task.

## Scope

**In scope**:
- Removing flex_1 through flex_5 field definitions from the BiometricReading model
- Creating and running the database schema migration to drop those columns
- Removing any references to flex fields in related serializers, views, or validation logic

**Out of scope**:
- Replacing the flex fields with new named fields (this would be a separate feature)
- Backfilling or archiving data from the flex columns before removal
- Changes to any model other than BiometricReading
