# Feature Specification: Remove Flex Fields from MQTT Parser

**Feature Branch**: `019-remove-flex-mqtt`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-2.4 Remove Flex from MQTT Parser - Update MQTT message parsing to not expect flex_1-flex_5 in sensor JSON payload."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accept Sensor Payloads Without Flex Fields (Priority: P1)

The TremoAI glove device no longer includes flex sensor readings (flex_1 through flex_5) in its transmitted JSON payload. The MQTT message parser must be updated to accept and process payloads containing only the six accelerometer and gyroscope sensor fields (aX, aY, aZ, gX, gY, gZ). Any parser logic that requires flex fields as part of validation or data extraction must be removed, so that glove messages are accepted and stored without errors.

**Why this priority**: Without this change, every sensor reading transmitted by updated glove devices will fail validation and be discarded. No sensor data will reach the platform, making all downstream monitoring, analysis, and ML inference non-functional. This is a blocking correctness issue.

**Independent Test**: Can be fully tested by sending a 6-field MQTT sensor payload (no flex fields) and verifying the system accepts, validates, and stores the reading correctly.

**Acceptance Scenarios**:

1. **Given** a glove device sends an MQTT sensor payload with only aX, aY, aZ, gX, gY, gZ fields, **When** the MQTT parser receives the message, **Then** it accepts the message, extracts all six values, and stores the reading without raising any error.
2. **Given** the MQTT parser's required field list, **When** a developer inspects the validation logic, **Then** flex_1, flex_2, flex_3, flex_4, and flex_5 are not listed as required, expected, or validated fields.
3. **Given** a valid 6-field sensor payload arrives via MQTT, **When** the reading is stored, **Then** the stored record contains only the six accelerometer/gyroscope values and standard metadata (device identifier, timestamp).

---

### User Story 2 - Gracefully Ignore Legacy Flex Fields in Payloads (Priority: P2)

Some older glove devices may still transmit the legacy payload format, which includes flex_1 through flex_5 in addition to the six standard sensor fields. The parser must tolerate these extra fields without failing. It must silently discard the flex values and process only the six standard fields, so that mixed fleets of updated and legacy devices can coexist without message loss.

**Why this priority**: A mixed-fleet scenario is realistic during a device firmware rollout. If legacy payloads cause parse errors, the platform would silently drop data for patients with older devices — a patient safety concern.

**Independent Test**: Can be fully tested by sending a legacy-format payload (11 fields including flex_1-5) and verifying the reading is accepted, only the six standard fields are stored, and no error is raised.

**Acceptance Scenarios**:

1. **Given** a legacy glove sends an MQTT payload containing aX, aY, aZ, gX, gY, gZ, flex_1, flex_2, flex_3, flex_4, flex_5, **When** the parser receives the message, **Then** it accepts the message and stores only the six standard sensor values, discarding the flex fields without error.
2. **Given** a payload with flex fields is processed, **When** the stored reading is inspected, **Then** no flex field values are persisted to the data store.

---

### Edge Cases

- What happens when a sensor payload is missing one of the six required fields (aX, aY, aZ, gX, gY, gZ)? The parser must still reject payloads missing these required fields with a clear validation error — the removal of flex field requirements must not weaken other field validations.
- What happens when a payload contains only flex fields with no standard sensor fields? The parser must reject this as an invalid payload (required fields missing), not accept it.
- What happens when a flex field value is present but is null or non-numeric in a legacy payload? The parser must treat the entire flex group as ignorable regardless of content type — the value is never read or stored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MQTT message parser MUST NOT treat flex_1, flex_2, flex_3, flex_4, or flex_5 as required fields in any incoming sensor JSON payload.
- **FR-002**: The MQTT message parser MUST successfully validate and process a sensor payload containing exactly the six fields: aX, aY, aZ, gX, gY, gZ (plus device identifier and timestamp).
- **FR-003**: The MQTT message parser MUST silently ignore flex_1 through flex_5 if they are present in an incoming payload, without raising errors or storing their values.
- **FR-004**: All existing required field validations for non-flex sensor fields MUST remain in effect after this change (no regression on other field checks).
- **FR-005**: Any code that previously extracted, stored, or forwarded flex_1 through flex_5 values from parsed MQTT messages MUST be removed.
- **FR-006**: Any automated tests that used flex fields in sample MQTT payloads MUST be updated to reflect the 6-field-only format.

### Key Entities

- **MQTT Sensor Payload**: The JSON message published by a glove device over MQTT. After this change, the standard format is: device identifier, timestamp, and six sensor readings (aX, aY, aZ, gX, gY, gZ). Flex fields are not part of the expected schema.
- **Sensor Reading Record**: The stored representation of one MQTT sensor message. Contains only the six accelerometer/gyroscope values and metadata. No flex field columns or values are stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 out of 5 flex fields (flex_1 through flex_5) are referenced as required or expected in MQTT message parsing or validation logic after the change.
- **SC-002**: 100% of MQTT sensor payloads containing only the six standard fields (aX, aY, aZ, gX, gY, gZ) are accepted and stored without errors.
- **SC-003**: 100% of legacy MQTT payloads that include flex fields alongside the six standard fields are accepted and stored correctly, with no flex values persisted.
- **SC-004**: All existing MQTT parsing tests pass after the update, with 0 tests referencing flex fields in their sample payloads.
- **SC-005**: No regression: MQTT payloads missing any of the six required sensor fields continue to be rejected with a validation error.

## Assumptions

- The glove device hardware has removed the five flex sensors; updated firmware no longer includes flex_1 through flex_5 in transmitted payloads.
- Some legacy devices may still transmit flex fields in their payloads for an unspecified transition period; silent discarding is the correct behavior.
- The database schema change removing flex field columns was completed in Feature E-2.1 (branch 017-remove-flex-fields); no additional schema migration is required for this feature.
- Flex field values have no business or clinical meaning and may be discarded without consequence.

## Scope

**In scope**:
- Removing flex_1 through flex_5 from any required-field validation lists in MQTT message parsing code
- Removing any extraction, mapping, or forwarding of flex field values from parsed MQTT payloads
- Updating MQTT-related tests to use 6-field-only sample payloads
- Ensuring legacy payloads with extra flex fields are silently accepted

**Out of scope**:
- Changes to the BiometricReading database model or schema (completed in Feature E-2.1)
- Changes to any non-MQTT data ingestion paths (REST API, WebSocket consumers)
- Changes to the BiometricSession pipeline (which uses tremor_intensity/frequency/timestamps, not raw sensor fields)
- Adding any new sensor fields to replace flex sensors
