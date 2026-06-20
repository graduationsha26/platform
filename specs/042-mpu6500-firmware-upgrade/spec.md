# Feature Specification: ESP32 Firmware Upgrade & Pin Management

**Feature Branch**: `042-mpu6500-firmware-upgrade`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: Upgrade ESP32 firmware from GY-521 (MPU6050) sensor to MPU6500 with SPI communication, reconfigure actuator pins (Servo → GPIO 14, Brushless ESC → GPIO 13), and ensure no pin conflicts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — MPU6500 SPI Sensor Integration & Pin-Safe Actuation (Priority: P1)

As a hardware engineer deploying the TremoAI glove, I need the ESP32 firmware to communicate with the MPU6500 sensor over SPI instead of I2C, configure the sensor for ±2g accelerometer and ±250 dps gyroscope ranges, and have the servo motor and brushless motor (ESC) reliably assigned to GPIO 14 and GPIO 13 respectively — with no pin conflicts between the SPI bus and the actuator control lines.

**Why this priority**: The hardware has been physically upgraded to the MPU6500. Without a matching firmware update, the glove cannot acquire sensor data at all, making the entire tremor-suppression system non-functional. Pin conflicts between SPI and actuators would cause irreversible hardware damage or erratic motor behavior.

**Independent Test**: Can be fully tested by flashing the updated firmware to the ESP32, connecting the MPU6500 via SPI on the assigned pins, and verifying via Serial Monitor that: (1) the sensor is detected with the correct MPU6500 chip ID, (2) live 6-axis readings stream at the configured rate, and (3) the servo on GPIO 14 and ESC on GPIO 13 respond to PWM commands without interference.

**Acceptance Scenarios**:

1. **Given** the ESP32 is powered on with an MPU6500 connected via SPI, **When** the firmware initializes, **Then** the Serial Monitor reports successful sensor detection with the correct MPU6500 chip ID and no I2C references in the initialization log.

2. **Given** the sensor is initialized, **When** live data is read, **Then** accelerometer readings fall within the ±2g range and gyroscope readings fall within the ±250 dps range, confirming the correct sensitivity registers are applied.

3. **Given** the firmware is running, **When** the actuator control loop activates, **Then** the servo motor responds correctly on GPIO 14 and the brushless motor ESC responds correctly on GPIO 13, with no signal corruption caused by SPI bus activity.

4. **Given** any reference to "6050" or "MPU-6050" exists in the firmware source (comments, variable names, identifiers), **When** the updated firmware is reviewed, **Then** no such references remain — all are updated to "6500" or "MPU-6500".

5. **Given** the SPI bus requires dedicated clock, data, and chip-select pins, **When** the SPI pins are assigned, **Then** none of the SPI pins are GPIO 13 or GPIO 14, preventing any overlap with the actuator control lines.

---

### Edge Cases

- What happens if the MPU6500 SPI chip-select overlaps with a PWM-active pin at boot — does the ESC arming sequence corrupt the first SPI transaction?
- What happens when the firmware boots on hardware that still has an older MPU6050 or MPU9250 chip — does it fail gracefully with a descriptive error rather than silently producing wrong data?
- What happens if SPI clock noise on adjacent GPIO lines induces spurious PWM pulses on GPIO 13 or GPIO 14 during a burst read?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The firmware MUST communicate with the MPU6500 sensor exclusively over SPI for all initialization, configuration, and data reads — no I2C transactions to the sensor.

- **FR-002**: The firmware MUST configure the MPU6500 accelerometer sensitivity to ±2g (16384 LSB/g) during initialization.

- **FR-003**: The firmware MUST configure the MPU6500 gyroscope sensitivity to ±250 dps (131 LSB/dps) during initialization.

- **FR-004**: The firmware MUST verify the MPU6500 identity via its WHO_AM_I register at boot and halt with a descriptive Serial error message if the chip ID does not match the expected MPU6500 value.

- **FR-005**: The firmware MUST assign the servo motor PWM control exclusively to GPIO 14 with a LEDC channel configured for 50 Hz, 16-bit resolution.

- **FR-006**: The firmware MUST assign the brushless motor ESC PWM control exclusively to GPIO 13 with a LEDC channel configured for 50 Hz, 16-bit resolution.

- **FR-007**: The SPI pins selected for MPU6500 (clock, MISO, MOSI, chip-select) MUST NOT include GPIO 13 or GPIO 14.

- **FR-008**: All source code references to "6050" or "MPU-6050" in variable names, comments, and string literals MUST be replaced with "6500" or "MPU-6500".

- **FR-009**: The firmware MUST preserve all existing calibration, Kalman filter, PID, and MQTT publish behaviors — only the sensor interface layer and actuator pin assignments change.

### Key Entities

- **MPU6500 Sensor**: The 6-axis IMU chip providing accelerometer (±2g) and gyroscope (±250 dps) readings over SPI. Replaces the GY-521 (MPU6050) breakout board.
- **Servo Motor**: Gimbal actuator controlled via 50 Hz PWM on GPIO 14. Receives angle commands from the PID controller.
- **Brushless Motor (ESC)**: Flywheel actuator controlled via 50 Hz PWM on GPIO 13. Holds constant throttle after ESC arming.
- **SPI Bus**: High-speed serial bus connecting ESP32 to MPU6500. Must use pins that do not overlap with GPIO 13 or GPIO 14.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The glove firmware successfully detects the MPU6500 on 100% of cold-boot attempts across 10 sequential power cycles with no sensor detection failures.

- **SC-002**: Live IMU data streams at 100 Hz with no samples dropped and all values within the configured ±2g / ±250 dps ranges during a 60-second continuous read test.

- **SC-003**: The servo on GPIO 14 and ESC on GPIO 13 each respond within one PWM cycle (≤20 ms) to control commands, with zero signal corruption observed during simultaneous SPI sensor reads.

- **SC-004**: A code review confirms zero remaining "6050" or "MPU-6050" string references across all firmware source and header files.

- **SC-005**: A GPIO pin audit confirms no SPI bus pin (clock, MISO, MOSI, chip-select) overlaps with GPIO 13 or GPIO 14.

## Assumptions

- The MPU6500 uses the same register addresses as the MPU9250 for SMPLRT_DIV, GYRO_CONFIG, ACCEL_CONFIG, PWR_MGMT_1, PWR_MGMT_2, and the 14-byte burst-read block starting at 0x3B — only the WHO_AM_I value and communication protocol change.
- The existing LEDC PWM channel indices (channels 0 and 1 for gimbal and flywheel) remain valid; only the GPIO pin numbers change from GPIO 18/19 to GPIO 14/13.
- The gyro sensitivity changes from ±2000 dps (existing firmware) to ±250 dps as requested; the LSB/dps conversion constant must be updated from 16.384 to 131.0.
- No other firmware modules (MQTT publisher, Kalman filter, task scheduler, battery reader) require changes — they consume already-converted physical-unit float values.
- The ESP32 VSPI peripheral (default pins: SCK=18, MISO=19, MOSI=23, CS=5) will be used for the MPU6500 SPI connection, as these pins are free once the actuators move to GPIO 13/14.
