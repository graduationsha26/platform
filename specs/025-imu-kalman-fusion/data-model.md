# Data Model: IMU Initialization, Calibration & Kalman Filter Sensor Fusion

**Feature**: 025-imu-kalman-fusion | **Date**: 2026-02-18

This document defines the firmware-side data structures used by the IMU driver, calibration routine, and Kalman filter. These are in-memory C/C++ structures — no database schema is involved. The only external data contract is the MQTT JSON payload published to the broker (defined in `contracts/mqtt-reading.yaml`).

---

## Entities

### 1. `RawSample` — Unprocessed 6-axis IMU reading

Represents a single reading from the MPU9250 at one sample instant, in physical units, before calibration is applied.

| Field     | Type    | Unit   | Range       | Description                      |
|-----------|---------|--------|-------------|----------------------------------|
| `aX`      | float   | m/s²   | ±19.6       | Accelerometer X-axis (raw)       |
| `aY`      | float   | m/s²   | ±19.6       | Accelerometer Y-axis (raw)       |
| `aZ`      | float   | m/s²   | ±19.6       | Accelerometer Z-axis (raw)       |
| `gX`      | float   | °/s    | ±2000       | Gyroscope X-axis (raw)           |
| `gY`      | float   | °/s    | ±2000       | Gyroscope Y-axis (raw)           |
| `gZ`      | float   | °/s    | ±2000       | Gyroscope Z-axis (raw)           |
| `timestamp_ms` | uint32 | ms | monotonic | MCU millis() at sample capture  |

**Conversion from sensor registers**:
- Accel: `raw_int16 / 16384.0 * 9.80665` → m/s² (±2g, AFS_SEL=0)
- Gyro: `raw_int16 / 16.384` → °/s (±2000°/s, FS_SEL=3)

---

### 2. `CalibrationOffsets` — Startup bias correction values

Computed once during the startup calibration window (glove held stationary). Applied to every subsequent `RawSample` to produce a `CalibratedSample`.

| Field     | Type  | Unit  | Description                                      |
|-----------|-------|-------|--------------------------------------------------|
| `aX_bias` | float | m/s² | Mean accelerometer X over calibration window     |
| `aY_bias` | float | m/s² | Mean accelerometer Y over calibration window     |
| `aZ_bias` | float | m/s² | Mean accel Z minus gravity reference (e.g., 9.80665 if flat) |
| `gX_bias` | float | °/s  | Mean gyroscope X over calibration window         |
| `gY_bias` | float | °/s  | Mean gyroscope Y over calibration window         |
| `gZ_bias` | float | °/s  | Mean gyroscope Z over calibration window         |
| `n_samples` | uint16 | — | Number of samples used to compute offsets      |
| `valid`   | bool  | —    | True if calibration completed without fault      |

**Calibration window**: 500 samples at 100Hz = 5 seconds of stationary data.

**Gravity compensation**: When the glove is flat (Z-axis up), aZ should read +9.80665 m/s². The `aZ_bias` stores `mean_aZ - 9.80665` so that calibrated aZ ≈ 0 at rest. This approach assumes a defined resting orientation. If orientation is unknown, only gyro bias is compensated and accel offsets are zero.

---

### 3. `CalibratedSample` — Bias-corrected 6-axis reading

Result of subtracting `CalibrationOffsets` from a `RawSample`. This is the input to the Kalman filter.

| Field     | Type  | Unit  | Description                                  |
|-----------|-------|-------|----------------------------------------------|
| `aX`      | float | m/s² | Calibrated accelerometer X                   |
| `aY`      | float | m/s² | Calibrated accelerometer Y                   |
| `aZ`      | float | m/s² | Calibrated accelerometer Z                   |
| `gX`      | float | °/s  | Calibrated gyroscope X (rate around X-axis) |
| `gY`      | float | °/s  | Calibrated gyroscope Y (rate around Y-axis) |
| `gZ`      | float | °/s  | Calibrated gyroscope Z (rate around Z-axis) |
| `dt`      | float | s    | Time delta since previous sample (≈0.01s)    |

---

### 4. `KalmanState` — Filter internal state (one instance per angle axis)

A 4-state Kalman filter is used for roll and pitch separately. Each instance tracks one angle (e.g., roll = rotation around X-axis) and the corresponding gyroscope bias.

| Field         | Type  | Description                                      |
|---------------|-------|--------------------------------------------------|
| `angle`       | float | Current filtered angle estimate (degrees)        |
| `bias`        | float | Estimated gyroscope bias for this axis (°/s)     |
| `rate`        | float | Unbiased gyroscope rate = measured rate − bias   |
| `P[2][2]`     | float | Error covariance matrix (2×2)                    |

**State vector**: `[angle, bias]`
**Inputs per update**:
- From gyro (predict step): `gyro_rate` (°/s), `dt` (s)
- From accel (update step): `accel_angle` (degrees, derived from atan2)

**Fixed noise parameters** (tunable constants):
- `Q_angle` = 0.001 (process noise: how much angle can change)
- `Q_bias`  = 0.003 (process noise: how much bias can drift)
- `R_measure` = 0.03 (measurement noise: accelerometer angle uncertainty)

*These are initial values from the Lauszus reference implementation. Increase `R_measure` if accelerometer is noisy; increase `Q_angle` if gyro drift is slow to correct.*

---

### 5. `FusedReading` — Kalman filter output, ready for MQTT transmission

The final output of one complete filter cycle. Contains the Kalman-filtered orientation angles alongside the calibrated raw sensor values and a timestamp string for the MQTT payload.

| Field          | Type   | Unit  | Description                                         |
|----------------|--------|-------|-----------------------------------------------------|
| `aX`           | float  | m/s² | Calibrated accelerometer X (passed through for platform) |
| `aY`           | float  | m/s² | Calibrated accelerometer Y                          |
| `aZ`           | float  | m/s² | Calibrated accelerometer Z                          |
| `gX`           | float  | °/s  | Calibrated gyroscope X                              |
| `gY`           | float  | °/s  | Calibrated gyroscope Y                              |
| `gZ`           | float  | °/s  | Calibrated gyroscope Z                              |
| `roll`         | float  | °    | Kalman-filtered roll angle (rotation around X)      |
| `pitch`        | float  | °    | Kalman-filtered pitch angle (rotation around Y)     |
| `timestamp_iso`| char[] | —    | ISO 8601 UTC timestamp string (from RTC or NTP)     |

**MQTT payload mapping**: The `devices/{serial}/reading` message uses `aX, aY, aZ, gX, gY, gZ, timestamp, serial_number`. The `roll` and `pitch` are firmware-internal estimates used to improve data quality but are not currently part of the MQTT payload (they may be added in a future extension). The calibrated 6-axis values are what the backend stores.

---

## State Transitions

### Firmware Boot Sequence

```
POWER_ON
    │
    ▼
IMU_INIT
    │ (success)
    ▼
CALIBRATING ──(motion detected or timeout)──► FAULT
    │ (500 samples collected)
    ▼
RUNNING ──────────────────────────────────────► FAULT
    │                                            │
    │ (every 10ms = 100Hz)                       │ (I2C error or MQTT fail > N retries)
    ▼                                            ▼
read_6axis()                               FAULT_STATE
    │                                      (stops publishing;
    ▼                                       blinks error LED;
apply_calibration()                         awaits reset)
    │
    ▼
kalman_predict() → kalman_update()
    │
    ▼
publish_to_mqtt()
    │
    └──► (loop back to read_6axis)
```

### Calibration Sub-States

```
CALIBRATING:
  - Accumulate N samples
  - Check for motion (if stddev(gX,gY,gZ) > threshold → FAULT or retry)
  - Compute mean → store as CalibrationOffsets
  - Set CalibrationOffsets.valid = true
  → Transition to RUNNING
```

---

## Key Relationships

- `RawSample` → (subtract `CalibrationOffsets`) → `CalibratedSample`
- `CalibratedSample` → (Kalman predict + update) → updates `KalmanState` → produces `FusedReading`
- `FusedReading` → (serialize to JSON) → MQTT publish → Django backend → `BiometricReading` DB record
- `BiometricReading` fields map 1:1 to `FusedReading.{aX, aY, aZ, gX, gY, gZ}` (calibrated values)

---

## Sensor Ranges Reference

| Axis | Physical Range  | Backend Accepted Range | Configured MPU9250 Range |
|------|-----------------|----------------------|--------------------------|
| aX   | ±19.6 m/s²      | ±20 m/s²             | ±2g (AFS_SEL=0)          |
| aY   | ±19.6 m/s²      | ±20 m/s²             | ±2g (AFS_SEL=0)          |
| aZ   | ±19.6 m/s²      | ±20 m/s²             | ±2g (AFS_SEL=0)          |
| gX   | ±2000 °/s       | ±2000 °/s            | ±2000°/s (FS_SEL=3)      |
| gY   | ±2000 °/s       | ±2000 °/s            | ±2000°/s (FS_SEL=3)      |
| gZ   | ±2000 °/s       | ±2000 °/s            | ±2000°/s (FS_SEL=3)      |

*Note: Backend validator warns (but does not reject) out-of-range values. Firmware should still operate within these bounds under normal Parkinson's tremor conditions.*
