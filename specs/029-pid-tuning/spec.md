# Feature Specification: CMG PID Controller Tuning

**Feature Branch**: `029-pid-tuning`
**Created**: 2026-02-19
**Status**: Draft
**Input**: User description: "1.3.3 1.3 CMG PID Controller Tuning Dual-axis PID control loop: read tremor from filtered IMU data → compute inverse torque → command gimbal servos. Tune Kp, Ki, Kd for each axis. Target: counter-torque cancels 60-75% of tremor amplitude."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PID Gain Configuration (Priority: P1)

A doctor opens the CMG panel for one of their patients and adjusts the proportional, integral, and derivative gain values for the pitch and roll axes independently. After saving, the new gains are delivered to the patient's device and the suppression behaviour changes accordingly. The doctor can also retrieve the currently active gains to understand the device's current tuning state.

**Why this priority**: Gain configuration is the foundational action of this feature. Without the ability to set and persist gains, neither suppression activation nor effectiveness monitoring delivers any value. It is the smallest independently useful increment.

**Independent Test**: A doctor logs in, navigates to the CMG panel for a paired device, views the current Kp/Ki/Kd values for each axis, changes them, saves, and confirms the device receives the updated values. No suppression activation or monitoring view is required.

**Acceptance Scenarios**:

1. **Given** a doctor is viewing the CMG panel for a paired device, **When** they enter new Kp, Ki, and Kd values for the pitch axis and save, **Then** the system persists the new values, records the change with the doctor's identity and timestamp, and pushes the updated gains to the device.
2. **Given** a doctor enters a Kp value outside the defined safe range, **When** they attempt to save, **Then** the system rejects the submission with a clear out-of-range error and the device gains are not changed.
3. **Given** a doctor opens the gain configuration panel, **When** the panel loads, **Then** the currently active gain values for both axes are pre-filled in the form.
4. **Given** no gain record exists yet for a device, **When** a doctor opens the gain configuration panel, **Then** system-default gain values are pre-filled and the doctor can save them as a first configuration.

---

### User Story 2 - Suppression Mode Activation (Priority: P2)

A doctor enables or disables the automatic tremor suppression mode on a patient's device. When active, the device continuously reads tremor from the sensor and applies counter-torque to the gimbal servos using the currently configured PID gains. When disabled, the device stops applying automatic counter-torque and the servos return to idle. The web platform shows whether the suppression mode is currently on or off for each device.

**Why this priority**: Gain configuration (US1) is only meaningful if the suppression loop can be turned on. Activation gives the gains a purpose. Monitoring (US3) depends on the loop being active, so this is the logical next dependency.

**Independent Test**: With valid gains already saved (from US1), a doctor enables suppression mode on a device, verifies the platform shows the mode as active, then disables it and verifies the status returns to inactive. No effectiveness charts are required.

**Acceptance Scenarios**:

1. **Given** a doctor is viewing the CMG panel and suppression is inactive, **When** they enable suppression mode, **Then** the device transitions to active suppression, the platform displays the mode as active, and the action is logged with timestamp and doctor identity.
2. **Given** suppression is active, **When** the doctor disables it, **Then** the device stops automatic counter-torque, servos return to idle state, the platform shows mode as inactive, and the action is logged.
3. **Given** the device becomes unreachable while suppression is active, **Then** the suppression mode is marked as interrupted on the platform, and the device transitions to a safe state (no servo motion).
4. **Given** a doctor tries to enable suppression mode before any gains have been configured, **When** they attempt activation, **Then** the system prevents activation and informs the doctor that gain configuration is required first.

---

### User Story 3 - Suppression Effectiveness Monitoring (Priority: P3)

A doctor reviews tremor amplitude data for a session during which suppression was active. The monitoring view shows raw (unsuppressed) tremor magnitude alongside the residual (post-suppression) tremor magnitude, allowing the doctor to assess whether the current gain settings are achieving the 60–75% cancellation target. The doctor can use this view to decide whether to adjust the gains.

**Why this priority**: This is the feedback loop that validates whether tuning decisions (US1) are working as intended. While valuable for clinical decision-making, the core suppression mechanism functions without a monitoring view, making this an enhancement rather than a foundation.

**Independent Test**: After a suppression session has completed, a doctor opens the effectiveness panel and sees a comparison of raw tremor amplitude vs. residual amplitude for that session. No gain editing or activation controls are needed in this view.

**Acceptance Scenarios**:

1. **Given** a suppression session has recorded at least one minute of data, **When** a doctor views the effectiveness panel for that session, **Then** they see the average raw tremor amplitude and the average residual tremor amplitude, and the percentage reduction is displayed.
2. **Given** the percentage reduction is at or above 60%, **When** displayed in the monitoring view, **Then** the result is visually distinguished as meeting the target (e.g., a positive indicator).
3. **Given** the percentage reduction is below 60%, **When** displayed, **Then** the result is visually distinguished as below target to prompt gain adjustment.
4. **Given** a doctor is viewing the effectiveness panel during an active suppression session, **When** new data arrives, **Then** the displayed metrics update in near-real-time to reflect the latest readings.

---

### Edge Cases

- What happens when a doctor saves gains while the device is offline? → Gains are persisted on the platform; the device receives them upon next connection.
- What happens if computed counter-torque would exceed the gimbal's calibrated motion limits? → The device clamps output to the configured limits (from the calibration feature, Feature 028); the platform is not involved in this clamping.
- What happens if the gain values are set such that the control loop becomes unstable (oscillation)? → The device is responsible for detecting a fault state and transitioning to safe idle; the platform displays the resulting fault status received from the device.
- What happens if a doctor sets only some gain fields (e.g., only Kp) and leaves others unchanged? → Each axis's gains are updated atomically per save; partial per-field updates within a save are not supported (all three gains for an axis are saved together).
- What happens if two doctors try to update gains for the same device simultaneously? → Last write wins; the system records each save individually so the audit trail remains complete.
- What happens when there is no tremor data to compare (patient not wearing glove)? → The effectiveness panel shows a "no data" state without error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Doctors MUST be able to view the currently active PID gain values (Kp, Ki, Kd) for both the pitch axis and the roll axis of any device assigned to their patients.
- **FR-002**: Doctors MUST be able to update Kp, Ki, and Kd for each axis independently, with each axis's three gains saved together as one operation.
- **FR-003**: The system MUST validate that all submitted gain values fall within defined safe operating bounds before persisting them.
- **FR-004**: When a doctor saves new gains, the system MUST deliver the updated values to the target device automatically.
- **FR-005**: If a device is offline when gains are saved, the system MUST deliver the gains to the device upon its next connection.
- **FR-006**: The system MUST record every gain change with the submitting doctor's identity and a timestamp, forming an immutable audit log.
- **FR-007**: Doctors MUST be able to enable automatic tremor suppression mode on a patient's device through the web platform.
- **FR-008**: Doctors MUST be able to disable automatic tremor suppression mode on a patient's device, causing the gimbal servos to return to idle.
- **FR-009**: The web platform MUST display the current suppression mode status (active / inactive / interrupted) for each device.
- **FR-010**: The system MUST prevent activation of suppression mode if no gain configuration exists for the device.
- **FR-011**: If a device becomes unreachable while suppression is active, the platform MUST mark the session as interrupted and the device MUST transition to a safe (no-motion) state autonomously.
- **FR-012**: All suppression mode activations and deactivations MUST be logged with the responsible doctor's identity and timestamp.
- **FR-013**: Doctors MUST be able to view a summary of tremor suppression effectiveness for completed or active suppression sessions, showing raw tremor amplitude, residual tremor amplitude, and the percentage reduction achieved.
- **FR-014**: The effectiveness summary MUST visually indicate whether the percentage reduction meets the 60% minimum target.
- **FR-015**: During an active suppression session, the effectiveness panel MUST update in near-real-time as new data arrives.

### Key Entities

- **PIDConfig**: Represents the set of PID gain values (Kp, Ki, Kd for pitch and roll) associated with a device. Tracks the current values, who last updated them, when, and a config version for synchronisation with the device.
- **SuppressionSession**: Represents a discrete period during which automatic tremor suppression was active on a device. Records start time, end time (or interrupted status), the gains active at the time, and the responsible doctor.
- **SuppressionMetric**: Represents a time-stamped measurement of raw tremor amplitude and residual tremor amplitude captured during a suppression session. Used to compute the aggregate effectiveness summary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When PID gains are optimally tuned, the active suppression system cancels at least 60% of measured tremor amplitude compared to the unsuppressed baseline for the same patient.
- **SC-002**: Updated PID gains reach the target device and take effect within 5 seconds of a doctor saving them, when the device is connected.
- **SC-003**: A doctor can complete a full gain configuration for both axes in under 2 minutes.
- **SC-004**: The suppression system operates continuously for at least 30 minutes without triggering servo faults or visible oscillation after a tuning session.
- **SC-005**: Doctors can determine from the monitoring view alone whether the current tuning meets the 60–75% cancellation target, without requiring external analysis tools.

## Assumptions

- The PID control computation (reading IMU data, calculating counter-torque, issuing servo commands) is performed on the glove device's embedded firmware, not on the web platform server. The platform's role is gain management, mode control, and effectiveness monitoring.
- Tremor frequencies for Parkinson's disease fall in the 4–8 Hz range. The device firmware is assumed to sample and process IMU data at a sufficient rate for effective cancellation; this rate is outside the web platform's scope.
- Gimbal motion limits defined in Feature 028 (calibration) remain the authoritative bounds for servo output; the PID feature does not change or override them.
- Safe operating bounds for PID gains (min/max per gain type) will be defined during planning based on hardware constraints; the spec assumes they exist and are finite.
- The platform does not implement gain auto-tuning or machine learning–based optimisation; all gain values are manually entered by the doctor.

## Dependencies

- **Feature 028 (CMG Gimbal Servo Control)**: Provides the `GimbalCalibration` model (motion limits) and the servo command delivery mechanism. PID gain activation mode ultimately produces servo commands that must respect Feature 028's calibration.
- **Biometrics / IMU pipeline**: Raw filtered IMU tremor data must be available to the device firmware; the platform receives aggregated amplitude metrics from the device, not raw IMU samples.
