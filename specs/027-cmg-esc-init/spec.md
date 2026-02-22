# Feature Specification: CMG Brushless Motor & ESC Initialization

**Feature Branch**: `027-cmg-esc-init`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "1.3 CMG    Brushless Motor + ESC Init    Configure ESC PWM signal for brushless rotor motor. Implement soft-start ramp to 15,000+ RPM. Safety: max current limit, stall detection."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe CMG Rotor Startup (Priority: P1)

The tremor suppression glove contains a high-speed spinning rotor (Control Moment Gyroscope — CMG) that must accelerate from rest to its operating speed before it can provide effective tremor suppression. The system must execute this startup sequence safely, gradually increasing rotor speed rather than applying full power immediately, to avoid mechanical stress and excessive current draw.

**Why this priority**: Without a safely executing startup, the CMG rotor cannot reach operating speed. This is the foundational behavior — tremor suppression cannot function if the motor fails to start correctly.

**Independent Test**: Can be tested by commanding the CMG to start from rest and verifying the rotor reaches ≥15,000 RPM within the defined startup window without triggering any safety faults.

**Acceptance Scenarios**:

1. **Given** the glove is powered and the CMG rotor is at rest, **When** a start command is issued, **Then** the rotor speed increases gradually (not abruptly) from 0 to ≥15,000 RPM within the configured startup duration.
2. **Given** the rotor is accelerating during startup, **When** current draw approaches the configured maximum limit, **Then** the acceleration rate is throttled to prevent overcurrent rather than abruptly cutting power.
3. **Given** the rotor has reached operating speed, **When** monitored continuously, **Then** the system maintains the target speed within ±5% of the setpoint under nominal load.

---

### User Story 2 - Real-Time CMG Status Telemetry (Priority: P2)

The doctor monitoring platform needs visibility into the CMG motor state — current rotor speed, current draw, and operational status (idle, starting, running, fault) — received from the glove in real time. This allows the platform to display CMG health alongside patient tremor data, supporting clinician oversight.

**Why this priority**: Knowing whether the tremor suppression mechanism is active and healthy is critical context for interpreting patient monitoring data. Without motor telemetry, doctors cannot distinguish hardware faults from ineffective tremor suppression.

**Independent Test**: Can be tested by streaming simulated CMG telemetry to the platform and verifying the dashboard reflects accurate motor state within 1 second of each update.

**Acceptance Scenarios**:

1. **Given** the CMG rotor is running, **When** the platform receives motor telemetry, **Then** the displayed rotor speed and current draw are accurate within ±5% of actual values and are updated at least once per second.
2. **Given** the CMG enters a fault state, **When** the fault event is received by the platform, **Then** the fault type and timestamp are recorded and visible to the doctor within 2 seconds of the fault occurring.

---

### User Story 3 - Automatic Safety Fault Response (Priority: P3)

The CMG motor must autonomously protect itself and the patient when abnormal conditions occur. If the motor draws more current than its rated maximum (overcurrent), or if the motor becomes stalled (commanded to spin but not spinning), the system must immediately cut motor output and report the fault condition to the platform.

**Why this priority**: Safety is non-negotiable; however, this is P3 as a separately testable story because the core startup (P1) and monitoring (P2) must first be demonstrable. Safety fault injection tests are meaningful only on top of a working motor system.

**Independent Test**: Can be tested by injecting simulated overcurrent or stall conditions and verifying that motor output is cut off within 500ms and a fault record is created on the platform.

**Acceptance Scenarios**:

1. **Given** the motor is running, **When** current draw exceeds the configured maximum limit, **Then** motor output is disabled within 500ms and an overcurrent fault event is recorded with its timestamp.
2. **Given** the motor is commanded to run, **When** the rotor speed is near-zero for more than 1 second despite active motor output, **Then** motor output is disabled within 500ms of stall detection and a stall fault event is recorded.
3. **Given** a fault has occurred and motor output is disabled, **When** a restart is commanded, **Then** the restart is rejected unless the fault has been explicitly acknowledged — no automatic recovery from fault state.

---

### Edge Cases

- What happens when the glove battery voltage drops below the motor's minimum operating voltage during a startup sequence?
- How does the system respond if the rotor reaches operating speed and then stalls due to a sudden mechanical obstruction?
- What happens if both overcurrent and stall conditions are detected simultaneously?
- What is the behavior if a start command is issued while a previous startup sequence is still in progress?
- How does the motor shut down if the glove loses communication with the platform mid-session?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST gradually ramp motor output from rest to the target operating speed (≥15,000 RPM) over a configurable startup duration when a start command is received.
- **FR-002**: The system MUST NOT apply full motor output instantaneously — soft-start protection is mandatory for every startup sequence.
- **FR-003**: The system MUST continuously monitor motor current draw throughout startup and operation, and enforce a configurable maximum current limit.
- **FR-004**: When current draw exceeds the configured maximum limit, the system MUST disable motor output within 500ms and record an overcurrent fault event.
- **FR-005**: The system MUST continuously monitor rotor speed and detect stall conditions (motor output active, rotor speed near-zero for ≥1 second).
- **FR-006**: When a stall is detected, the system MUST disable motor output within 500ms of detection and record a stall fault event.
- **FR-007**: Recovery from any fault state MUST require explicit acknowledgment — the motor cannot restart automatically after a safety fault.
- **FR-008**: The system MUST publish motor telemetry at a minimum rate of 1 Hz to the monitoring platform.
- **FR-009**: Motor telemetry MUST include at minimum: rotor speed (RPM), current draw (amperes), and operational status (idle / starting / running / fault with fault type).
- **FR-010**: The system MUST support a controlled shutdown sequence (gradual deceleration to rest) in addition to the emergency fault-stop (immediate output disable).

### Key Entities

- **CMG Motor State**: Represents the instantaneous operating condition of the CMG rotor — speed (RPM), current draw (amperes), operational status (idle / starting / running / fault), and fault type when applicable.
- **Motor Command**: An instruction issued to the CMG system — start (initiate soft-start ramp), stop (initiate controlled deceleration), or emergency stop (immediate output disable).
- **Fault Event**: A safety incident record capturing fault type (overcurrent / stall), timestamp, rotor speed and current draw at the time of fault, and acknowledgment status.
- **Motor Configuration**: The set of operating parameters — target operating RPM, maximum current limit (amperes), soft-start ramp duration (seconds), stall detection timeout (seconds).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The CMG rotor reaches ≥15,000 RPM from a cold start within the configured startup window under nominal load, with zero safety faults triggered during a normal startup sequence.
- **SC-002**: Motor current draw during the soft-start ramp does not exceed the configured maximum current limit at any point during a normal startup sequence.
- **SC-003**: Overcurrent fault detection and motor output disable occur within 500ms of current exceeding the configured maximum limit.
- **SC-004**: Stall fault detection and motor output disable occur within 1,500ms of a stall condition beginning (1,000ms detection window + 500ms response).
- **SC-005**: Motor telemetry (rotor speed and current draw) is delivered to the monitoring platform at ≥1 Hz with values accurate within ±5% of actual sensor readings.
- **SC-006**: Restart from a fault state is blocked 100% of the time until the fault has been explicitly acknowledged.

## Assumptions

- The CMG rotor's nominal operating speed is ≥15,000 RPM; the exact setpoint is configurable per glove model.
- The soft-start ramp duration is configurable; a default of 3–5 seconds is assumed adequate.
- Rotor speed feedback is available from the motor controller hardware; stall detection relies on this feedback.
- The configured maximum current limit is a hardware safety parameter defined per glove model.
- CMG telemetry is delivered to the monitoring platform over the existing MQTT data pipeline used for IMU sensor readings.
- Graceful shutdown (ramp-down) takes approximately the same duration as startup.
- Fault events are stored in the platform database as part of per-device event history alongside biometric sessions.
