# Feature Specification: IMU Initialization, Calibration & Kalman Filter Sensor Fusion

**Feature Branch**: `025-imu-kalman-fusion`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "1.1 IMU Init & Calibration: I2C init for MPU9250. Read accelerometer (aX, aY, aZ) + gyroscope (gX, gY, gZ) at 100Hz. Startup calibration. Magnetometer disabled (not used, causes latency). Sensor Fusion (Kalman Filter): Implement Kalman filter fusing accelerometer + gyroscope for clean orientation estimates. 6-axis input only. No magnetometer correction."

## Context

This feature is part of the **TremoAI Smart Glove firmware** — the embedded software running on the wearable device worn by Parkinson's patients. The glove contains an MPU9250 inertial measurement unit (IMU) that captures motion data, which is then transmitted to the TremoAI platform for tremor analysis and classification.

The firmware must reliably acquire clean, consistent 6-axis motion data (accelerometer + gyroscope) and apply sensor fusion to produce stable orientation estimates that serve as the foundation for all downstream tremor classification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Sensor Startup (Priority: P1)

When the smart glove is powered on, the firmware must detect the IMU sensor, configure it correctly (with the magnetometer disabled), and execute a startup calibration so the device is ready to deliver accurate motion data before any readings are transmitted.

**Why this priority**: Without successful initialization and calibration, all downstream motion data is unreliable. This is the foundational step for any glove operation — nothing else works without it. Magnetometer must be disabled explicitly because enabling it introduces measurable latency that degrades the 100Hz sampling requirement.

**Independent Test**: Power on a glove unit. Verify that initialization completes within the required time, no magnetometer activity is detected, and the sensor reports calibrated readings within acceptable accuracy bounds — without requiring any further feature to be implemented.

**Acceptance Scenarios**:

1. **Given** the glove is powered on, **When** the firmware starts, **Then** the IMU sensor is detected and configured within 500ms, and the magnetometer is confirmed inactive.
2. **Given** the glove is stationary during startup, **When** the calibration routine runs, **Then** sensor bias offsets are computed and applied so that static readings converge to expected resting values within the calibration window.
3. **Given** the glove is powered on with the IMU sensor disconnected or undetectable, **When** the firmware starts, **Then** the firmware enters a defined fault state and does not attempt to transmit data.

---

### User Story 2 - Continuous 100Hz Motion Sampling (Priority: P1)

Once initialized, the firmware must continuously read 6-axis IMU data — three accelerometer axes (aX, aY, aZ) and three gyroscope axes (gX, gY, gZ) — at a steady rate of 100 samples per second, making raw samples available for further processing and transmission.

**Why this priority**: The 100Hz sampling rate is a hard requirement for tremor characterization. Tremor frequency in Parkinson's disease typically ranges from 3–7 Hz; 100Hz provides sufficient temporal resolution with headroom for artifact analysis. Any lower rate compromises clinical validity.

**Independent Test**: Connect the glove and capture a time-stamped log of raw 6-axis readings over 10 seconds. Verify that approximately 1000 samples are recorded, timestamps are evenly spaced at ~10ms intervals, and all six axes contain plausible values.

**Acceptance Scenarios**:

1. **Given** the IMU is initialized and calibrated, **When** the firmware enters its main loop, **Then** new 6-axis samples are produced at a rate of 100Hz (±5% timing tolerance).
2. **Given** samples are being produced at 100Hz, **When** a reading is captured, **Then** all six values (aX, aY, aZ, gX, gY, gZ) are present and within the sensor's valid measurement range.
3. **Given** continuous sampling is running, **When** the system is observed over 60 seconds, **Then** no samples are dropped and the sampling rate remains consistent within tolerance.

---

### User Story 3 - Kalman Filter Sensor Fusion for Clean Orientation Estimates (Priority: P2)

The raw accelerometer and gyroscope readings contain noise and drift. The firmware must apply a Kalman filter that fuses these two 6-axis sources to produce stable, noise-reduced orientation estimates — using only the accelerometer and gyroscope (no magnetometer input).

**Why this priority**: Raw IMU data alone is insufficient for accurate tremor classification: accelerometers are noisy at high frequency; gyroscopes drift over time. The Kalman filter corrects each sensor's weakness with the other's strength. This is required for reliable feature extraction upstream. It is P2 (after P1 sampling) because raw samples must first be reliably acquired.

**Independent Test**: With the glove stationary, compare raw accelerometer orientation against Kalman-filtered orientation over 30 seconds. Filtered output must show substantially lower variance and no drift accumulation. Rotate the glove to a known angle and verify the filtered estimate converges to the correct orientation.

**Acceptance Scenarios**:

1. **Given** calibrated 6-axis samples are produced at 100Hz, **When** the Kalman filter processes each sample, **Then** it outputs a filtered orientation estimate at the same 100Hz rate without added latency beyond one sample period.
2. **Given** the glove is held stationary, **When** filtered orientation is observed over 30 seconds, **Then** the estimate remains stable with no visible drift and noise is reduced compared to raw accelerometer readings.
3. **Given** the glove is rotated to a new orientation, **When** the Kalman filter converges, **Then** the filtered estimate reflects the new orientation accurately within a defined settling time.
4. **Given** magnetometer input is absent (disabled), **When** the Kalman filter runs, **Then** it operates correctly using only the 6 axes (accelerometer + gyroscope) without any magnetometer correction step.

---

### Edge Cases

- What happens if I2C communication fails mid-session (sensor becomes unresponsive after successful init)?
- What happens if the glove is moving during the calibration window (bias computation corrupted by motion)?
- How does the Kalman filter behave when a sensor axis saturates or reports an out-of-range value?
- What happens if the 100Hz timer drifts due to competing firmware tasks or interrupt contention?
- How is the Kalman filter state initialized at startup before the first valid reading pair is available?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The firmware MUST initialize communication with the MPU9250 IMU sensor at device startup.
- **FR-002**: The firmware MUST explicitly disable the MPU9250 magnetometer during initialization and MUST NOT read from it at any point during normal operation.
- **FR-003**: The firmware MUST perform a startup calibration routine that computes and stores bias offsets for all six axes (accelerometer and gyroscope) before entering normal sampling mode.
- **FR-004**: The firmware MUST sample accelerometer data (aX, aY, aZ) and gyroscope data (gX, gY, gZ) at a rate of 100 samples per second (100Hz) during normal operation.
- **FR-005**: The firmware MUST apply the calibration-derived bias offsets to every raw sample before the sample is used for sensor fusion or transmission.
- **FR-006**: The firmware MUST implement a Kalman filter that fuses each calibrated accelerometer + gyroscope sample pair to produce a filtered orientation estimate.
- **FR-007**: The Kalman filter MUST use only the 6 IMU axes (accelerometer + gyroscope) as input; magnetometer data MUST NOT be used as a correction input.
- **FR-008**: The Kalman-filtered orientation estimate MUST be produced at the same 100Hz rate as the raw sampling rate.
- **FR-009**: The firmware MUST enter a defined fault state if IMU initialization fails, preventing transmission of invalid data.
- **FR-010**: The firmware MUST complete IMU initialization and calibration within an acceptable startup time before entering normal sampling mode.

### Key Entities

- **IMU Sensor (MPU9250)**: The 9-axis inertial measurement unit used as the motion data source. Only 6 axes are active (3-axis accelerometer + 3-axis gyroscope). Magnetometer axis is disabled.
- **Raw Sample**: A single time-stamped measurement containing all six axis values (aX, aY, aZ, gX, gY, gZ), produced at 100Hz.
- **Calibration Offsets**: Bias correction values computed per-axis during the startup calibration routine. Applied to every subsequent raw sample.
- **Calibrated Sample**: A raw sample with calibration offsets subtracted, representing the corrected sensor reading.
- **Kalman Filter State**: The internal state vector maintained by the Kalman filter, encoding current orientation estimate and uncertainty. Updated with each incoming calibrated sample.
- **Fused Orientation Estimate**: The output of the Kalman filter for each sample — a stable, noise-reduced orientation representation used by downstream tremor classification logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: IMU initialization and magnetometer disable complete within 500ms of device power-on.
- **SC-002**: Startup calibration completes within 5 seconds and reduces per-axis static error to within acceptable bounds for the sensor's operating range.
- **SC-003**: The firmware consistently produces 6-axis samples at 100Hz with no more than ±5% timing jitter over any 60-second observation window.
- **SC-004**: No samples are dropped during continuous 60-second operation under normal firmware load.
- **SC-005**: The Kalman-filtered orientation estimate, when measured against a stationary glove over 30 seconds, shows at least 50% lower variance than the raw accelerometer output for the same period.
- **SC-006**: The Kalman filter converges to a stable orientation estimate within 2 seconds of the glove reaching a new static position.
- **SC-007**: The magnetometer produces zero sensor bus transactions during normal operation, confirming it does not contribute to system latency.

## Assumptions

- The MPU9250 is the sole IMU sensor on the glove hardware; no alternative sensor fallback is required.
- The startup calibration assumes the glove is stationary during the calibration window. Motion during calibration is an edge case handled by a fault/retry path, not normal operating conditions.
- The Kalman filter variant (standard linear, complementary, EKF, etc.) is an implementation decision deferred to the planning phase; this spec only requires fusing accelerometer and gyroscope using a Kalman-family algorithm.
- 100Hz is sufficient for characterizing tremor in the 3–7Hz clinical frequency range; no higher sampling rate is required at this stage.
- The firmware runs on a microcontroller with sufficient processing headroom to execute the Kalman filter update step within a single 10ms sample period.
- Downstream tremor classification on the platform consumes the Kalman-filtered orientation estimates (not raw samples) as its primary input.
