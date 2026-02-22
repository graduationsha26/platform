# Feature Specification: CMG Gimbal Servo Control

**Feature Branch**: `028-gimbal-servo-control`
**Created**: 2026-02-19
**Status**: Draft
**Input**: User description: "1.3.2 CMG Gimbal Servo Control: Dual servo control for pitch and roll gimbal axes. Rate limiting to prevent mechanical stress. Calibrate center positions and travel range."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gimbal Position Control (Priority: P1)

A doctor uses the platform dashboard to command the smart glove gimbal to a specific pitch and roll orientation. The system forwards the command to the glove device, which moves both servo axes to the requested angles. Movement is automatically bounded by the configured travel range and executed at a rate that prevents mechanical stress. The doctor receives confirmation once the gimbal reaches the target position, or is notified if the movement cannot be completed.

**Why this priority**: This is the primary operational capability of the gimbal — without the ability to command specific positions, the pitch/roll stabilization feature has no value. All other stories depend on this foundation being in place and working reliably.

**Independent Test**: Can be fully tested by sending a position command (e.g., pitch +10°, roll −5°) via the dashboard and verifying the gimbal reaches the target within the expected tolerance, with movement speed not exceeding the rate limit. Delivers the core value of programmatic gimbal control.

**Acceptance Scenarios**:

1. **Given** the glove is online and the gimbal is at center position, **When** the doctor commands pitch +20°, **Then** the gimbal moves to pitch +20° (±2°) and confirms arrival without exceeding the configured rate limit.
2. **Given** the gimbal travel range is set to ±45° for both axes, **When** the doctor commands pitch +60°, **Then** the system rejects the command with a clear out-of-range error and the gimbal does not move.
3. **Given** the doctor sends simultaneous pitch and roll commands, **When** both commands are received, **Then** both axes move independently to their targets within the travel range.
4. **Given** the glove is offline, **When** the doctor sends a position command, **Then** the platform displays a device-unavailable error immediately.

---

### User Story 2 - Servo Calibration (Priority: P2)

A doctor or clinical technician sets the center (neutral) position and the allowed travel range for each servo axis on a specific patient's glove device. Calibration accounts for the physical differences between individual glove units (e.g., mechanical zero offset, varying wrist anatomy). The calibrated values persist on the device and within the platform, so they are applied automatically the next time the patient uses the glove.

**Why this priority**: Calibration is necessary to ensure position commands are interpreted correctly relative to the actual mechanical zero of each individual glove. Without calibration, commanded angles may not correspond to real-world positions, degrading therapeutic effectiveness and potentially exceeding safe travel limits.

**Independent Test**: Can be tested by setting center positions and travel range limits for a device, power-cycling the glove, and verifying that the new calibration values are still in effect and that position commands respect the updated travel limits.

**Acceptance Scenarios**:

1. **Given** a doctor opens the calibration panel for a device, **When** they set pitch center to +3° and confirm, **Then** subsequent commands treat +3° as the new neutral reference and the platform stores this value.
2. **Given** a travel range of ±30° is configured for the roll axis, **When** the glove is power-cycled, **Then** the travel range remains ±30° and position commands are still bounded accordingly.
3. **Given** the doctor enters an invalid calibration value (e.g., min travel > max travel), **When** they attempt to save, **Then** the platform rejects the entry with a descriptive validation error.
4. **Given** calibration has never been performed for a device, **When** the doctor opens the calibration panel, **Then** default center positions of 0° and default travel ranges are shown as starting values.

---

### User Story 3 - Real-time Gimbal Monitoring (Priority: P3)

A doctor monitoring a patient session can see the live pitch and roll angles of the gimbal updating in real time on the dashboard. The display also shows whether each axis is moving, idle, or in a fault state. This gives the doctor situational awareness of how the gimbal is responding during treatment without needing to query the device manually.

**Why this priority**: Real-time monitoring provides the feedback loop required for a doctor to make informed decisions about gimbal adjustments. While position control (P1) enables commands and calibration (P2) ensures accuracy, monitoring closes the loop and makes the system observable. It is ranked P3 because US1 and US2 can deliver value even with only periodic (non-live) status updates.

**Independent Test**: Can be tested by manually tilting the glove and verifying that the pitch/roll readings on the dashboard update within 1 second of the physical movement, and that a fault state (e.g., servo stall) is shown when triggered.

**Acceptance Scenarios**:

1. **Given** the doctor has the patient's dashboard open, **When** the gimbal pitch changes by 5°, **Then** the displayed pitch value updates within 1 second.
2. **Given** a servo enters a stall condition, **When** the fault is detected, **Then** the monitoring panel shows a fault indicator for the affected axis within 1 second.
3. **Given** the glove is offline, **When** the doctor views the monitoring panel, **Then** the panel shows a "device disconnected" indicator rather than stale position values.

---

### Edge Cases

- What happens when a position command arrives while the gimbal is already in motion toward a different target? The new command supersedes the in-progress movement and the servo redirects to the new target, subject to rate limiting.
- What happens when the servo reaches a physical hard stop before reaching the commanded angle? The system detects the stall condition, stops the servo to avoid motor burn-out, and reports a fault for that axis.
- What happens when calibration is changed while a position command is in flight? The in-flight command completes based on the old calibration; the new calibration applies to subsequent commands.
- What happens when both axes receive commands simultaneously but only one is within range? The in-range axis executes; the out-of-range axis is rejected with an error; neither axis is silently ignored.
- What happens when the device reports a position that is outside the configured travel range? The platform displays the raw reported value with an out-of-range warning, rather than clipping silently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept target angle commands for the pitch axis and roll axis independently, as well as combined pitch+roll commands in a single request.
- **FR-002**: System MUST validate that commanded angles fall within the configured travel range for each axis and reject out-of-range commands with an explanatory error.
- **FR-003**: System MUST apply a configurable rate limit to servo movement so that angular velocity does not exceed the maximum degrees-per-second setting for each axis.
- **FR-004**: System MUST allow a doctor to set and update the center (neutral) position for the pitch axis and the roll axis independently.
- **FR-005**: System MUST allow a doctor to set and update the minimum and maximum travel angles for the pitch axis and the roll axis independently.
- **FR-006**: System MUST persist calibration data (center positions and travel range) for each device so that calibration survives device power cycles and platform restarts.
- **FR-007**: System MUST provide a "move to center" command that returns the gimbal to the calibrated neutral position for both axes.
- **FR-008**: System MUST detect when a servo axis cannot reach its commanded position (stall condition) and report this as a fault for that axis.
- **FR-009**: System MUST publish real-time gimbal position (current pitch and roll angles) to the doctor's dashboard at a frequency sufficient for live monitoring.
- **FR-010**: System MUST display the operational state of each servo axis (idle, moving, fault) on the doctor's dashboard.
- **FR-011**: System MUST record all position commands and calibration changes with timestamps, linked to the device and the doctor who issued them.
- **FR-012**: Only users with the doctor role MUST be permitted to issue position commands and modify calibration settings.

### Key Entities

- **ServoCommand**: A directive to move one or both gimbal axes to target angles, including the commanded pitch and roll values, the issuing user, the target device, and the timestamp.
- **GimbalCalibration**: The center position offset and travel range (minimum and maximum angles) for the pitch and roll axes of a specific device. Persists across sessions.
- **GimbalState**: The current reported pitch angle, roll angle, and per-axis operational status (idle / moving / fault) for a device at a point in time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The gimbal reaches any commanded angle within the travel range with a steady-state error of no more than 2 degrees.
- **SC-002**: Angular velocity during commanded movements never exceeds the configured rate limit, measurable by sampling position at 50 Hz and verifying no sample-to-sample change exceeds the per-interval equivalent of the rate cap.
- **SC-003**: Calibration changes (center position or travel range) take effect for all subsequent commands within 1 second of confirmation and persist correctly after device power cycle.
- **SC-004**: Live gimbal position and axis status update on the doctor's dashboard within 1 second of an actual change on the device.
- **SC-005**: A doctor can complete a full calibration workflow (set center positions and travel range for both axes) in under 5 minutes.
- **SC-006**: Stall conditions and out-of-range rejections are surfaced to the doctor as visible alerts within 2 seconds of detection.
- **SC-007**: 100% of position commands and calibration changes are recorded with correct timestamps and authorship.

## Assumptions

- The glove device firmware accepts position commands as target angles in degrees relative to the calibrated center position and enforces the rate limit on its side; the platform communicates the calibrated limits so the firmware can apply them.
- Default calibration values (0° center, ±45° travel range) are appropriate for a patient who has not yet been calibrated.
- Rate limiting is a system-wide safety setting with a default maximum velocity (e.g., 60°/s) that can be adjusted per device by a doctor; it is never disabled.
- The CMG gimbal uses two independent servo channels (pitch and roll); yaw is handled by the brushless motor (Feature 027) and is outside this feature's scope.
- Calibration data is scoped per physical device (not per patient), because glove hardware varies between units.
- Doctors are the only platform role that issues commands or modifies calibration; patients have read-only visibility at most.
