# Feature Specification: MQTT Parser and Normalization 6-Axis Cleanup

**Feature Branch**: `021-6axis-params-cleanup`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "E-3.3 Update MQTT Parser for 6 Axes: Update MQTT JSON parsing to extract only aX, aY, aZ, gX, gY, gZ from incoming sensor data. E-3.4 Update params.json Normalization: Rebuild params.json with min/max or mean/std for only 6 axes. Remove mX, mY, mZ, flex entries."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - MQTT Messages Parsed for 6 Active Axes Only (Priority: P1)

When a wearable glove sends a sensor reading over the data connection, the system should extract and process only the 6 active sensor axes (accelerometer: aX, aY, aZ; gyroscope: gX, gY, gZ). Magnetometer values (mX, mY, mZ) — which the hardware sends as a constant disabled value — must never be read, stored, or forwarded to the prediction pipeline. This ensures that every stored reading, every tremor prediction, and every API response is based solely on real, active sensor data.

**Why this priority**: The MQTT parser is the entry point for all live sensor data. If it extracts wrong or non-existent channels, every downstream component — storage, inference, WebSocket broadcast — is affected. Fixing the parser at the boundary is the highest-leverage change.

**Independent Test**: Can be fully tested by sending a simulated glove message that includes all 9 sensor fields (aX–gZ plus mX, mY, mZ) and confirming the system stores a record with only the 6 accelerometer and gyroscope values, and that no magnetometer data is persisted or forwarded.

**Acceptance Scenarios**:

1. **Given** a glove device sends a sensor reading containing aX, aY, aZ, gX, gY, gZ, mX, mY, mZ, **When** the system processes the message, **Then** only aX, aY, aZ, gX, gY, gZ are extracted and stored; mX, mY, mZ are silently discarded.
2. **Given** a glove device sends a sensor reading containing only the 6 active axes (no magnetometer fields), **When** the system processes it, **Then** the message is accepted and the 6 values are stored correctly.
3. **Given** a glove device sends a reading with missing magnetometer fields (hardware has them disabled), **When** the system processes it, **Then** no error occurs and the 6 axis values are stored successfully.
4. **Given** the system receives a reading and runs it through the ML prediction pipeline, **When** the prediction completes, **Then** it was based exclusively on the 6 active axes, with no magnetometer values in the feature vector.

---

### User Story 2 - Normalization Parameters Defined for 6 Axes Only (Priority: P2)

The ML prediction pipeline normalizes raw sensor values before running them through the tremor detection model. The normalization configuration file must contain statistical parameters (mean and standard deviation) for exactly the 6 active sensor axes — no more, no less. Any entries for magnetometer axes (mX, mY, mZ) or flex sensors must be absent, so that normalization never accidentally applies to non-existent or disabled channels.

**Why this priority**: Normalization misconfiguration is a silent error — wrong or extra parameters do not cause crashes but produce incorrect feature vectors, degrading prediction accuracy without any obvious failure signal. Ensuring the configuration file matches the 6-axis pipeline is essential for model reliability.

**Independent Test**: Can be fully tested by inspecting the normalization configuration file and confirming it contains exactly 6 entries named aX, aY, aZ, gX, gY, gZ with valid statistical values; then running the inference pipeline and verifying the prediction completes without error.

**Acceptance Scenarios**:

1. **Given** the normalization configuration file, **When** its contents are inspected, **Then** it contains exactly 6 entries: aX, aY, aZ, gX, gY, gZ — no magnetometer (mX, mY, mZ) or flex sensor entries.
2. **Given** raw sensor data for the 6 active axes, **When** the normalization step runs, **Then** it succeeds using the 6-entry configuration and produces normalized values ready for inference.
3. **Given** the normalization configuration file needs to be regenerated from the training dataset, **When** the regeneration process runs, **Then** the output contains only the 6-axis entries derived from the active sensor channels in the dataset.
4. **Given** the normalization configuration has invalid statistics (zero standard deviation, wrong count), **When** the system attempts to load it, **Then** the system rejects it with a clear error and does not proceed with inference.

---

### Edge Cases

- What if a glove firmware sends mX/mY/mZ fields? They are silently discarded — the system does not error or store them.
- What if the normalization file is regenerated after adding new sensor types to the dataset? The regeneration process must still produce only the 6 active-channel entries.
- What happens when the normalization file has fewer than 6 entries or contains unexpected axis names? The system should reject it at startup with a descriptive error.
- What if an operator attempts to manually add mX/mY/mZ entries to the normalization file? The system should reject the file at load time due to the entry count mismatch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extract exactly the 6 active sensor axes (aX, aY, aZ, gX, gY, gZ) from incoming glove sensor messages and MUST NOT extract or store magnetometer values (mX, mY, mZ).
- **FR-002**: The system MUST silently discard any magnetometer or flex sensor fields present in incoming sensor messages without raising an error.
- **FR-003**: The normalization configuration MUST contain statistical parameters for exactly 6 sensor axes: aX, aY, aZ, gX, gY, gZ.
- **FR-004**: The normalization configuration MUST NOT contain any entries for mX, mY, mZ, or any flex sensor channels.
- **FR-005**: When the normalization configuration is loaded, the system MUST validate that it contains exactly 6 entries and reject any file that does not match.
- **FR-006**: The tool that generates the normalization configuration from training data MUST produce exactly 6-axis entries, using only the active sensor channels from the dataset.
- **FR-007**: The ML prediction pipeline MUST use the 6-axis normalization configuration exclusively — no magnetometer or flex values may enter the feature vector at any stage.

### Key Entities

- **Sensor Message**: A real-time data packet from the wearable glove. Contains at minimum the 6 active axes (aX–gZ). May also contain disabled magnetometer fields (mX, mY, mZ = constant value) depending on firmware version. Only the 6 active fields are ever processed.
- **Normalization Configuration**: A file containing mean and standard deviation values for each active sensor axis. Must have exactly 6 entries matching the 6 active axes. Used by the ML pipeline at inference time to normalize raw readings before model input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of sensor messages processed by the system result in stored records containing exactly 6 sensor axis values — no magnetometer values are ever persisted.
- **SC-002**: The normalization configuration contains exactly 6 entries (aX, aY, aZ, gX, gY, gZ) with 0 entries for mX, mY, mZ, or any flex sensor.
- **SC-003**: Every ML prediction issued by the system is derived from a 6-element feature vector — no prediction is ever based on more or fewer features.
- **SC-004**: The normalization configuration regeneration process produces a valid 6-axis file in under 30 seconds from any valid training dataset.
- **SC-005**: The system immediately rejects (at startup) any normalization configuration that does not contain exactly 6 matching axis entries, preventing silent prediction errors.

## Assumptions

- The glove hardware's magnetometer is permanently disabled; mX, mY, mZ will always be a constant sentinel value (e.g., −1) and carry no clinically useful data.
- The training dataset (`Dataset.csv`) contains mX, mY, mZ columns with all-constant values; the normalization configuration generator correctly excludes them and derives statistics only for the 6 active columns.
- "Rebuild params.json" (E-3.4) means regenerating the file from the training dataset using the standard generation tool, ensuring the output matches the 6-axis schema — not manually editing the file.
- Any existing normalization configuration that already meets the 6-axis requirements is considered compliant and does not need to be regenerated unless the training data changes.
