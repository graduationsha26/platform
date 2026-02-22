# Feature Specification: Real-Time Task Scheduling for Glove Control

**Feature Branch**: `031-freertos-scheduler`
**Created**: 2026-02-19
**Status**: Draft
**Input**: User description: "1.5.1    1.5 Loop    FreeRTOS Task Scheduler    Configure FreeRTOS with 3 tasks: Sensor reading task (100Hz), PID control task (200Hz), MQTT publish task (30Hz). Set task priorities. Verify total loop time <70ms from sensor read to CMG actuation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Responsive Tremor Suppression (Priority: P1)

A patient wearing the TremoAI smart glove relies on the glove to detect tremor motion and actuate the suppression mechanism fast enough to counteract the tremor before it becomes perceptible. The glove's control response must complete within 70 milliseconds of the sensor detecting motion — from the moment a sensor reading is captured to the moment the suppression actuator responds.

The control algorithm must run at 200 cycles per second to track and counteract rapid tremor oscillations smoothly. Sensor data must be available at 100 samples per second to feed the control algorithm with fresh input.

**Why this priority**: This is the core therapeutic function of the device. Without a sub-70ms sensor-to-actuation loop, tremor suppression becomes ineffective. All other tasks are secondary to this timing guarantee.

**Independent Test**: With the glove powered on, instrument the firmware to timestamp the sensor read and the actuation command. Verify that the measured sensor-to-actuation elapsed time is below 70ms for every cycle over a 60-second observation window.

**Acceptance Scenarios**:

1. **Given** the glove is powered on and running normally, **When** the sensor captures an IMU reading, **Then** the control algorithm processes that reading and issues an actuation command within 70ms.
2. **Given** the glove is running all three concurrent activities (sensing, controlling, transmitting), **When** the control algorithm is due to execute, **Then** it runs immediately and is not delayed by the telemetry transmission activity.
3. **Given** the control task is executing, **When** the telemetry task also becomes ready to run, **Then** the control task completes its current cycle uninterrupted before telemetry resumes.

---

### User Story 2 — Concurrent, Non-Blocking Operation (Priority: P2)

The glove must simultaneously perform three distinct activities: reading sensor data at 100Hz, running the tremor suppression control algorithm at 200Hz, and transmitting telemetry data at 30Hz. These activities must not interfere with one another — if the telemetry transmission is delayed (e.g., due to a slow network), the sensor reading and control algorithm must continue running at their required rates without any interruption.

**Why this priority**: If any one activity blocks another, the entire system becomes unreliable. A telemetry stall must never cause the control loop to miss cycles. Concurrent, isolated scheduling is a prerequisite for the system to be both therapeutically effective and observable.

**Independent Test**: Simulate a slow or delayed telemetry transmission (e.g., introduce a deliberate 100ms delay in the publish step). Verify via serial log timestamps that the sensor task still achieves 100Hz and the control task still achieves 200Hz throughout the delay period.

**Acceptance Scenarios**:

1. **Given** all three tasks are running, **When** telemetry transmission takes longer than its allotted time window, **Then** sensor sampling and control algorithm execution continue at their scheduled rates without skipping any cycles.
2. **Given** all three tasks are running, **When** a sensor read cycle and a control cycle are due simultaneously, **Then** the control task executes first (higher priority), followed immediately by the sensor task.
3. **Given** the glove has been running for 60 seconds, **When** task execution counts are inspected, **Then** the sensor task has executed approximately 6,000 times, the control task approximately 12,000 times, and the telemetry task approximately 1,800 times.

---

### User Story 3 — Predictable Telemetry Rate (Priority: P3)

Doctors monitoring a patient's session via the TremoAI platform rely on a smooth, consistent data stream from the glove. The glove must transmit sensor readings to the backend at 30 messages per second. This transmission must occur without disrupting the higher-priority sensing and control activities.

**Why this priority**: Telemetry is essential for clinical monitoring but is a best-effort activity. While data delivery must be regular enough for the platform to render smooth charts (~30Hz), the glove must never sacrifice tremor control to meet transmission timing.

**Independent Test**: Subscribe to the MQTT topic (`tremo/sensors/+`) and observe message arrival rate over 60 seconds. Verify approximately 1,800 messages are received (30Hz average) and that no transmission burst causes a gap or delay in the sensor-to-actuation timing verified in User Story 1.

**Acceptance Scenarios**:

1. **Given** the glove is connected to the MQTT broker, **When** the telemetry task is scheduled, **Then** it publishes approximately 30 messages per second to the backend.
2. **Given** the control task preempts the telemetry task mid-transmission, **When** the control task completes, **Then** telemetry resumes and catches up without producing duplicate or malformed messages.
3. **Given** the glove is running all three tasks, **When** the telemetry rate is measured over a 30-second window, **Then** the observed rate is within ±10% of 30Hz (27–33 messages/second).

---

### Edge Cases

- What happens when the network is unavailable and telemetry cannot be transmitted — do the sensor and control tasks continue running at full rate?
- What if the sensor read takes longer than expected (e.g., I2C bus contention) — does the control task receive the last valid reading or wait?
- What happens if the control task consistently takes longer than its 5ms slot — does the scheduler detect overrun and how is it reported?
- What if all three tasks become ready simultaneously at a scheduling boundary — which runs first, and in what order do the others follow?
- What happens to telemetry if the MQTT broker disconnects mid-session — does reconnection logic run in a way that does not block the control loop?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST deliver an actuation command within 70 milliseconds of the sensor reading that triggered it, measured end-to-end under all normal operating conditions.
- **FR-002**: The sensor reading activity MUST execute at 100 cycles per second (one reading every 10ms) continuously while the device is powered on.
- **FR-003**: The tremor suppression control activity MUST execute at 200 cycles per second (one execution every 5ms) continuously while the device is powered on.
- **FR-004**: The telemetry transmission activity MUST execute at approximately 30 cycles per second (one transmission every ~33ms).
- **FR-005**: The control activity MUST have the highest scheduling priority; the sensor activity MUST have intermediate priority; the telemetry activity MUST have the lowest priority.
- **FR-006**: A delay or failure in the telemetry activity MUST NOT cause any missed cycles in the sensor or control activities.
- **FR-007**: A delay or failure in the sensor activity MUST NOT cause any missed cycles in the control activity (control uses the most recent valid sensor value).
- **FR-008**: The scheduling arrangement MUST be deterministic — given the same elapsed time, the same tasks execute in the same order.
- **FR-009**: The system MUST provide observable diagnostic output (e.g., serial log) that allows a developer to verify each task's execution rate and confirm end-to-end latency during testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The end-to-end latency from sensor capture to actuation command is below 70ms in every observed cycle over a 60-second test run (zero violations).
- **SC-002**: The control activity runs at 200Hz with no more than ±1ms jitter per cycle, measured over a 60-second window.
- **SC-003**: The sensor activity runs at 100Hz with no missed samples during any 10-second window, even when telemetry is actively transmitting.
- **SC-004**: The telemetry activity transmits at 30Hz ±10% (27–33 messages/second) measured over any 30-second window.
- **SC-005**: Introducing a deliberate 100ms artificial delay in telemetry does not cause any sensor or control cycles to be skipped (verified by cycle count comparison before and after the delay).
- **SC-006**: All three activities run concurrently for a minimum of 5 minutes without a watchdog reset, crash, or stack overflow.

## Assumptions

- The CMG (Control Moment Gyroscope) actuator accepts commands issued by the control algorithm and provides the physical tremor suppression response.
- The existing IMU sensor reading implementation (Feature 025) provides raw samples at up to 100Hz; this feature controls the scheduling cadence, not the sensor hardware rate.
- The existing MQTT publish implementation (Feature 030) handles the actual network transmission; this feature controls when the publish is triggered (30Hz), not the MQTT library internals.
- The 70ms end-to-end budget is allocated approximately as: ≤10ms sensor read + ≤5ms control execution + ≤55ms margin for scheduling overhead and actuation propagation.
- Stack memory for each task is sufficient for the workload; exact stack sizes are a planning-phase concern.
- The three task rates (100Hz, 200Hz, 30Hz) are fixed requirements, not configurable at runtime by the user.
- "Total loop time" refers to the elapsed time from when a sensor reading is captured to when the resulting actuation command is issued by the control algorithm — it does not include physical actuator response time.

## Dependencies

- **Feature 025** (IMU Kalman Fusion): Provides the sensor reading and Kalman filter update logic that the sensor task will invoke.
- **Feature 030** (ESP32 MQTT): Provides the MQTT publish logic that the telemetry task will invoke.
- CMG actuation interface must be defined (hardware signal or PWM output to the CMG driver).
