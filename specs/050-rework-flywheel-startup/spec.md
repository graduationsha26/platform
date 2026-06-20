# Feature Specification: Fix CMG Flywheel Startup Stall Using a Validated Brushless-Motor Sequence

**Feature Branch**: `050-rework-flywheel-startup`
**Created**: 2026-06-17
**Status**: Draft
**Input**: User description: "The problem that specs\049-fix-esc-flywheel-stall was trying to solve didn't work. The file C:\Data from HDD\Graduation Project\Platform\run_zizo.cpp doesn't face a problem in running the brushless motor but not complete for servo work. I want u to study the file in terms of running the brushless and implement the way to solve our problems in our firmware code"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Flywheel Startup Using a Sequence Already Proven on This Hardware (Priority: P1)

As the TremoAI smart glove is powered on for use, the Control Moment Gyroscope (CMG) flywheel must spin up to its operating speed reliably every time, so the device can deliver tremor counter-torque therapy immediately without manual troubleshooting or repeated power cycling. The previous firmware fix for this same symptom (reduced arm pulse, direct throttle jump, and a battery-voltage-sag retry heuristic) has since been bench-tested on the real assembled device and did **not** resolve the failure — the flywheel still fails to start reliably. A separate, standalone bench-test program written for this exact ESC, motor, and flywheel hardware has, however, demonstrated a startup command pattern that reliably spins the motor up without stalling. This story replaces the firmware's flywheel startup logic with that proven pattern.

**Why this priority**: The flywheel is the core actuator of the CMG tremor-suppression mechanism. If it cannot reliably reach and sustain operating speed, no therapy can be delivered at all — and the prior fix attempt already shipped without resolving this, so the underlying command sequence itself, not just its surrounding retry/detection logic, is now the blocking issue.

**Independent Test**: Power on the assembled device with the installed 35g aluminum flywheel across at least 20 consecutive power cycles and verify the flywheel reaches and sustains stable operating speed without an ESC fault cutoff in every cycle — matching the reliability already observed when running the proven sequence on the standalone bench-test program against the same hardware.

**Acceptance Scenarios**:

1. **Given** the device is powered off, **When** power is applied, **Then** the ESC arms without emitting a continuous pre-start fault-beep pattern, and the flywheel begins spinning within the expected startup window.
2. **Given** the flywheel has begun spinning, **When** it progresses through startup, **Then** it reaches and sustains its configured operating speed without the ESC abruptly cutting power, in every one of 20 consecutive power-on cycles.
3. **Given** the flywheel is at stable operating speed, **When** normal device operation continues, **Then** no fault-beep pattern occurs and the CMG gimbal can be actuated normally.

---

### User Story 2 - Flywheel Fix Must Not Disturb the Production Gimbal Servo Path (Priority: P1)

As the engineer applying this fix, I need the corrected flywheel startup sequence to come **only** from the brushless-motor-running portion of the reference bench-test program, not from its servo-stabilization logic, so that the device's actual therapeutic actuation path (sensor fusion, PID control, and task scheduling already driving the gimbal servo) is not regressed, simplified, or replaced by code that was never built for production use.

**Why this priority**: The reference program being studied includes its own minimal, single-axis, raw-gyro PID loop for the stabilizer servo — explicitly not a complete or production-equivalent implementation. If that servo logic were carried over alongside the brushless-motor fix, it would silently regress the device's real tremor-counter control. Keeping the two cleanly separated is just as critical as fixing the flywheel itself, so it shares top priority.

**Independent Test**: After applying the corrected flywheel startup sequence, induce a simulated tremor input on the bench rig and verify the gimbal servo's response is still produced exclusively by the existing production sensor-fusion + PID + task-scheduling pipeline, with no change in behavior, responsiveness, or accuracy compared to before this fix.

**Acceptance Scenarios**:

1. **Given** the corrected flywheel startup sequence is in place, **When** the device completes boot and enters normal operation, **Then** the gimbal servo continues to be driven exclusively by the existing production tremor-control pipeline, unchanged by this fix.
2. **Given** the reference program's simplified single-axis servo-stabilization logic, **When** this fix is implemented, **Then** none of that simplified logic is present in, or driving, the production gimbal control path.

---

### User Story 3 - Visible Fault Detection and Bounded Recovery Remain in Place (Priority: P2)

As the engineer or technician validating or servicing a device, when the flywheel still fails to start for any reason after the corrected sequence is applied, I need a clear, observable fault signal and a bounded automatic retry — rather than unexplained continuous beeping or an indefinite retry loop — so the failure can be diagnosed quickly and the device can attempt self-recovery without a full power cycle.

**Why this priority**: This continues the fault-visibility and auto-recovery behavior already expected of the device. It is secondary to actually fixing the startup sequence (User Stories 1 and 2), since a correct sequence should make detection/retry the rare exception rather than the common path, but it must not be silently dropped while the underlying sequence changes.

**Independent Test**: Deliberately induce a stall condition during bench testing (e.g., briefly interrupting a motor phase connection) and verify the system records or reports a distinguishable startup-fault indication; separately, induce a transient stall and confirm automatic retry recovers without a power cycle, while a persistent stall results in a latched fault state rather than retrying forever.

**Acceptance Scenarios**:

1. **Given** the ESC fails to reach stable operating speed within the expected startup window even after the corrected sequence is applied, **When** the failure is detected, **Then** the system records or reports a distinct startup-fault indication, distinguishable from other fault types (e.g., IMU calibration failure).
2. **Given** a startup fault has occurred, **When** the system automatically retries the arm/spin-up sequence, **Then** the flywheel successfully reaches operating speed without the power source being physically disconnected and reconnected.
3. **Given** the system has exhausted its bounded automatic retry attempts without success, **When** no further retries occur, **Then** the device enters a persistent startup-fault state rather than retrying indefinitely.

---

### Edge Cases

- What happens if the proven startup pattern — validated only on a standalone, single-purpose bench rig — behaves differently once running inside the full production firmware (concurrent sensor sampling, control loop, and wireless/MQTT activity sharing the same microcontroller)? Could shared timing resources reintroduce a stall even though the command pattern itself is correct?
- What happens if the previously implemented fault-detection/retry behavior (from the prior, unsuccessful fix attempt) now produces false readings or unnecessary retries once the underlying sequence has changed, and needs to be reconciled rather than left as-is?
- What happens if the flywheel ESC stalls on some power-ups but not others (intermittent failure) even with the corrected sequence, rather than failing consistently every time?
- How does the system behave if battery voltage is low or marginal during startup, since the flywheel's high-inertia spin-up draws the most current precisely during that window?
- What happens if a startup fault occurs after the device has already entered normal operation (e.g., a transient stall mid-session) rather than only during initial power-on?
- How does the system distinguish a genuine ESC or wiring hardware fault (e.g., damaged ESC, disconnected phase wire) from the flywheel-inertia startup mismatch this feature addresses, so technicians aren't misled into chasing the wrong cause?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CMG flywheel ESC MUST complete its power-on arming sequence without emitting a continuous pre-start fault-beep pattern under normal operating conditions (the reported Phase 1 failure).
- **FR-002**: The flywheel MUST reach and sustain its configured operating speed after arming, without the ESC cutting power due to a stall or desync event, while driving the installed 35g aluminum flywheel (the reported Phase 2 failure) — this time using a startup command pattern consistent with the one already confirmed, via standalone bench testing on the same ESC/motor/flywheel hardware, to reliably start this motor.
- **FR-003**: After reaching stable operating speed, the flywheel MUST continue running without entering a continuous fault-beep state during normal device operation (the reported Phase 3 failure).
- **FR-004**: The system MUST distinguish a flywheel startup fault from other device fault conditions (e.g., IMU calibration failure, WiFi/MQTT connection failure) so the two are not confused during diagnosis.
- **FR-005**: The flywheel startup sequence (arming through reaching stable operating speed) MUST complete within a bounded, predictable time so device readiness can be determined without indefinite waiting.
- **FR-006**: The fix MUST operate within the existing 35g solid aluminum flywheel and motor hardware as a fixed constraint — changing the flywheel mass/inertia, motor, or gearing is out of scope; the solution MUST be achieved entirely through firmware and configuration.
- **FR-007**: The fix MUST be achievable entirely through the existing ESP32-generated PWM control path — no one-time ESC reconfiguration via vendor tooling (e.g., BLHeliSuite) or a dedicated programming cable is required or permitted.
- **FR-008**: Upon detecting a startup fault, the system MUST automatically retry the arm/spin-up sequence without requiring operator intervention or a manual power cycle.
- **FR-009**: After a bounded number of consecutive failed automatic retry attempts, the system MUST stop retrying and enter a persistent startup-fault state (per FR-004) rather than retrying indefinitely, so a genuine hardware fault is not masked by endless retry attempts.
- **FR-010**: The corrected startup sequence's command pattern (arm-pulse level, arm hold duration, and the shape/step-size of the transition from the arm pulse to running speed) MUST be derived from, and consistent with, the sequence already empirically validated to reliably start this exact ESC/motor/flywheel combination — not an untested new pattern invented independently of that validated reference.
- **FR-011**: This fix MUST NOT alter, replace, simplify, or otherwise interfere with the existing gimbal servo's production tremor-counter control path (sensor fusion, PID computation, and task scheduling). Only the flywheel motor's own arm/startup command sequence is in scope for this feature.

### Key Entities

- **Flywheel Startup Sequence**: The arm → spin-up → stable-operation timeline the ESC and motor progress through on every power-up; defines the phases referenced by the acceptance criteria and the reported three-phase failure.
- **Startup Fault State**: A distinguishable device condition entered when the flywheel fails to complete the startup sequence, as opposed to normal operation or other unrelated fault types (e.g., sensor or connectivity faults).
- **Validated Reference Sequence**: The empirically confirmed arm/hold/run command pattern demonstrated by a standalone bench-test program against the same ESC, motor, and flywheel hardware; serves as the baseline the corrected production firmware sequence must reproduce for the flywheel actuation path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The flywheel reaches and sustains stable operating speed without an ESC fault cutoff in at least 20 consecutive power-on cycles during validation testing with the installed 35g aluminum flywheel (100% success rate).
- **SC-002**: From power-on, the flywheel reaches stable operating speed within 10 seconds consistently, with no indefinite hang or unbounded fault-beeping.
- **SC-003**: Zero occurrences of continuous fault-beeping — before startup or after a stop — are observed across the validation test cycles under normal operating conditions.
- **SC-004**: When a startup fault is deliberately induced during validation testing, it is correctly identified as a distinct fault type (not confused with another device fault) in 100% of induced-fault trials.
- **SC-005**: When a transient startup fault is induced during validation testing, the system automatically recovers to stable operating speed without a physical power-cycle in at least 90% of induced-fault trials; persistent faults reliably result in the device entering a fault state rather than retrying indefinitely.
- **SC-006**: After the fix, the gimbal servo's tremor-counter response (measured on a bench tremor-simulation rig) shows no observable regression in responsiveness or accuracy compared to its behavior before this fix, confirming the change stayed scoped to the flywheel motor only.

## Assumptions

- The underlying root cause is unchanged from the prior feature attempt: the 35g solid aluminum flywheel's significantly higher rotational inertia (compared to a standard lightweight drone propeller) makes it harder for the motor to accelerate fast enough during the ESC's startup phase to hand off cleanly from forced commutation to normal sensorless operation.
- The fix delivered by the prior feature (`049-fix-esc-flywheel-stall`) — arm-pulse reduction, a direct (no-ramp) jump to target throttle, and a battery-voltage-sag-based retry/fault-detection heuristic — has since been bench-tested on the real assembled device and did **not** resolve the reported three-phase failure. This indicates the low-level command pattern itself (not only the surrounding detection/retry logic) needs to change.
- A standalone bench-test program written for this exact hardware (same ESC, same 2200KV motor, same flywheel, and the same GPIO/SPI pin assignments as production) has empirically demonstrated a startup sequence that reliably spins up the brushless motor without the three-phase failure. This is treated as the validated reference behavior this fix must reproduce for the flywheel actuation path specifically.
- That same standalone program's servo-stabilization logic (a minimal single-axis, raw-gyroscope-rate PID loop without sensor fusion or task scheduling) is explicitly out of scope and not production-ready. The production gimbal servo continues to be driven exclusively by the existing sensor-fusion + PID + task-scheduling pipeline, unmodified by this fix.
- The exact constant operating throttle/speed the corrected sequence settles at for normal CMG operation is a bench-tuning detail to be confirmed during implementation/validation, not fixed by this specification. It may end up differing from both the prior firmware's target and the reference program's target, provided it reliably delivers the flywheel's required gyroscopic counter-torque without reintroducing the stall.
- Whether the previously implemented fault-detection/retry mechanism is kept as-is, retuned, or replaced is left to the planning phase; this specification only requires that fault detection and bounded automatic retry continue to exist and remain distinguishable from other fault types, carried over from the prior feature's accepted requirements (FR-004, FR-008, FR-009 above).
- Validation is performed on the bench/assembled device with the actual installed ESC, motor, and flywheel hardware (no substitute hardware).
- 10 seconds (SC-002) remains a reasonable upper bound for startup time, consistent with both the existing multi-second arm-and-handoff behavior already present in firmware and the validated reference sequence's own timing.
- The flywheel/motor hardware (35g solid aluminum flywheel, ESC, 2200KV motor) is fixed for this feature; the resolution is firmware/configuration-only.
- The fix must be deliverable entirely through the ESP32's PWM control path, with no separate ESC reconfiguration step via vendor tooling.
