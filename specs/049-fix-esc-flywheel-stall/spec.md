# Feature Specification: Fix CMG Flywheel ESC Arming and Stall Failure

**Feature Branch**: `049-fix-esc-flywheel-stall`
**Created**: 2026-06-17
**Status**: Draft
**Input**: User description: "System Context: The hardware utilizes an EMAX 30A BLHeli Electronic Speed Controller (ESC) to drive a 2200KV brushless motor. The motor is equipped with a custom 35g solid aluminum flywheel instead of a standard lightweight drone propeller. The ESC is controlled via PWM signals from an ESP32 microcontroller. The Symptom Sequence: When the system is powered on, it exhibits a three-phase failure sequence: 1. Phase 1 (Continuous pre-start buzzing): Upon power-up, continuous beeps and refuses to spin the motor. 2. Phase 2 (The 1-second spin): The motor eventually attempts to spin, runs for approximately one second, and then abruptly cuts power or stops spinning. 3. Phase 3 (Continuous post-stop buzzing): After the motor stops, continuous beeping and refuses further commands."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Flywheel Startup for Therapy Delivery (Priority: P1)

As the TremoAI smart glove is powered on for use, the Control Moment Gyroscope (CMG) flywheel must spin up to its operating speed reliably every time, so the device can deliver tremor counter-torque therapy immediately without manual troubleshooting or repeated power cycling.

**Why this priority**: The flywheel is the core actuator of the CMG tremor-suppression mechanism. If it cannot reliably reach and sustain operating speed, no therapy can be delivered at all — this is the foundational capability the rest of the device depends on.

**Independent Test**: Power on the assembled device with the installed 35g aluminum flywheel across at least 20 consecutive power cycles and verify the flywheel reaches and sustains stable operating speed without an ESC fault cutoff in every cycle.

**Acceptance Scenarios**:

1. **Given** the device is powered off, **When** power is applied, **Then** the ESC arms without emitting a continuous pre-start fault-beep pattern, and the flywheel begins spinning within the expected startup window.
2. **Given** the flywheel has begun spinning, **When** it progresses through startup, **Then** it reaches and sustains its configured operating speed without the ESC abruptly cutting power.
3. **Given** the flywheel is at stable operating speed, **When** normal device operation continues, **Then** no fault-beep pattern occurs and the CMG gimbal can be actuated normally.

---

### User Story 2 - Visible Fault Detection When Startup Fails (Priority: P2)

As the engineer or technician validating or servicing a device, when the flywheel ESC fails to start for any reason, I need a clear, observable signal — rather than just unexplained continuous beeping — so the failure can be diagnosed quickly and not mistaken for an unrelated hardware fault.

**Why this priority**: Even after the primary startup failure is fixed, manufacturing variance, battery condition, or wiring faults could still occasionally prevent the ESC from starting. Fast, unambiguous diagnosis shortens repair time. This is secondary to fixing the stall itself but important for long-term maintainability.

**Independent Test**: Deliberately induce a stall condition during bench testing (e.g., briefly interrupting a motor phase connection) and verify the system records or reports a distinguishable startup-fault indication.

**Acceptance Scenarios**:

1. **Given** the ESC fails to reach stable operating speed within the expected startup window, **When** the failure is detected, **Then** the system records or reports a distinct startup-fault indication.
2. **Given** a startup fault has been reported, **When** the operator inspects device status, **Then** they can distinguish "flywheel startup fault" from other fault types the device already reports (e.g., IMU calibration failure).

---

### User Story 3 - Automatic Recovery Without a Full Power Cycle (Priority: P3)

As the device operator, when a startup fault occurs I want the device to automatically retry the arm/spin-up sequence rather than requiring me to fully disconnect and reconnect the battery, so device uptime and usability are not unnecessarily degraded.

**Why this priority**: Improves operational resilience and reduces support burden, but only becomes the priority once Phase 1 (reliable startup) is largely solved — it addresses the remaining edge cases rather than the everyday case.

**Independent Test**: Induce a transient stall condition during bench testing and verify the device automatically retries and restores normal operation without requiring the battery to be disconnected and reconnected; separately, induce a persistent stall and verify the device stops retrying and enters a fault state instead of retrying forever.

**Acceptance Scenarios**:

1. **Given** a startup fault has occurred, **When** the system automatically retries the arm/spin-up sequence, **Then** the flywheel successfully reaches operating speed without the power source being physically disconnected and reconnected.
2. **Given** the system has exhausted its bounded automatic retry attempts without success, **When** no further retries occur, **Then** the device enters a persistent startup-fault state (per User Story 2) rather than retrying indefinitely.

---

### Edge Cases

- What happens if the flywheel ESC stalls on some power-ups but not others (intermittent failure) rather than failing consistently every time?
- How does the system behave if battery voltage is low or marginal during startup, since the flywheel's high-inertia spin-up draws the most current precisely during that window?
- What happens if a startup fault occurs after the device has already entered normal operation (e.g., a transient stall mid-session) rather than only during initial power-on?
- How does the system distinguish a genuine ESC or wiring hardware fault (e.g., damaged ESC, disconnected phase wire) from the flywheel-inertia startup mismatch this feature addresses, so technicians aren't misled into chasing the wrong cause?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CMG flywheel ESC MUST complete its power-on arming sequence without emitting a continuous pre-start fault-beep pattern under normal operating conditions (the reported Phase 1 failure).
- **FR-002**: The flywheel MUST reach and sustain its configured operating speed after arming, without the ESC cutting power due to a stall or desync event, while driving the installed 35g aluminum flywheel (the reported Phase 2 failure).
- **FR-003**: After reaching stable operating speed, the flywheel MUST continue running without entering a continuous fault-beep state during normal device operation (the reported Phase 3 failure).
- **FR-004**: The system MUST distinguish a flywheel startup fault from other device fault conditions (e.g., IMU calibration failure, WiFi/MQTT connection failure) so the two are not confused during diagnosis.
- **FR-005**: The flywheel startup sequence (arming through reaching stable operating speed) MUST complete within a bounded, predictable time so device readiness can be determined without indefinite waiting.
- **FR-006**: The fix MUST operate within the existing 35g solid aluminum flywheel and motor hardware as a fixed constraint — changing the flywheel mass/inertia, motor, or gearing is out of scope; the solution MUST be achieved entirely through firmware and configuration.
- **FR-007**: The fix MUST be achievable entirely through the existing ESP32-generated PWM control path — no one-time ESC reconfiguration via vendor tooling (e.g., BLHeliSuite) or a dedicated programming cable is required or permitted.
- **FR-008**: Upon detecting a startup fault, the system MUST automatically retry the arm/spin-up sequence without requiring operator intervention or a manual power cycle.
- **FR-009**: After a bounded number of consecutive failed automatic retry attempts, the system MUST stop retrying and enter a persistent startup-fault state (per FR-004) rather than retrying indefinitely, so a genuine hardware fault is not masked by endless retry attempts.

### Key Entities

- **Flywheel Startup Sequence**: The arm → spin-up → stable-operation timeline the ESC and motor progress through on every power-up; defines the phases referenced by the acceptance criteria and the reported three-phase failure.
- **Startup Fault State**: A distinguishable device condition entered when the flywheel fails to complete the startup sequence, as opposed to normal operation or other unrelated fault types (e.g., sensor or connectivity faults).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The flywheel reaches and sustains stable operating speed without an ESC fault cutoff in at least 20 consecutive power-on cycles during validation testing with the installed 35g aluminum flywheel (100% success rate).
- **SC-002**: From power-on, the flywheel reaches stable operating speed within 10 seconds consistently, with no indefinite hang or unbounded fault-beeping.
- **SC-003**: Zero occurrences of continuous fault-beeping — before startup or after a stop — are observed across the validation test cycles under normal operating conditions.
- **SC-004**: When a startup fault is deliberately induced during validation testing, it is correctly identified as a distinct fault type (not confused with another device fault) in 100% of induced-fault trials.
- **SC-005**: When a transient startup fault is induced during validation testing, the system automatically recovers to stable operating speed without a physical power-cycle in at least 90% of induced-fault trials; persistent faults reliably result in the device entering a fault state rather than retrying indefinitely.

## Assumptions

- The 35g solid aluminum flywheel's significantly higher rotational inertia (compared to a standard lightweight drone propeller) is the underlying cause of the reported stall: the motor cannot accelerate fast enough during the ESC's startup phase for it to reliably hand off from forced commutation to normal sensorless operation, leading to the desync/cutoff described as Phase 2.
- A partial mitigation already exists in firmware — an ESC arming hold of several seconds followed by a gradual (rather than instantaneous) throttle ramp to operating speed — but the reported failure sequence indicates this is not yet sufficient to fully resolve the stall.
- "Stable operating speed" refers to the constant flywheel throttle level already used for normal CMG operation, not a variable/PID-driven speed.
- Validation is performed on the bench/assembled device with the actual installed ESC, motor, and flywheel hardware described in the system context (no substitute hardware).
- 10 seconds (SC-002) is a reasonable upper bound for startup time given the existing multi-second arm-and-ramp behavior already present in firmware; this is a default assumption, not a value confirmed with stakeholders.
- The flywheel/motor hardware (35g solid aluminum flywheel, EMAX 30A BLHeli ESC, 2200KV motor) is fixed for this feature; the resolution is firmware/configuration-only (confirmed during clarification).
- The fix must be deliverable entirely through the ESP32's PWM control path, with no separate ESC reconfiguration step via vendor tooling (confirmed during clarification).
- Automatic retry (FR-008) is confirmed as the desired recovery behavior; the exact retry count/backoff bound (FR-009) is left as a planning-phase detail, not specified here.
