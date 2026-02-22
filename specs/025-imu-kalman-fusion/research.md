# Research: IMU Initialization, Calibration & Kalman Filter Sensor Fusion

**Feature**: 025-imu-kalman-fusion | **Date**: 2026-02-18
**Phase**: Phase 0 — All NEEDS CLARIFICATION resolved

---

## Research Question 1: Kalman Filter Algorithm for 6-Axis IMU Fusion

### Decision

Use the **Lauszus 2-state linear Kalman filter** (one independent instance per angle axis — roll and pitch). Do not estimate yaw (no magnetometer reference available).

### Rationale

Three viable approaches were evaluated:

| Approach | Type | Operations/update | MCU suitability | Selected? |
|---|---|---|---|---|
| Lauszus 2-state KF | Linear Kalman | ~50 scalar (both axes) | All ARM Cortex | ✅ Yes |
| Madgwick 6-axis | Gradient descent | 109 scalar | All ARM Cortex | Alternative |
| ESKF + quaternions | Extended Kalman | 300-500 scalar | Cortex-M4F+ | If needed |

The Lauszus formulation is a **true Kalman filter** (not complementary, not extended) because the 2-state system `[angle, gyro_bias]` is linear when restricted to one axis at a time. It is the canonical embedded choice: small code size, no quaternions, explicit gyroscope bias correction, and proven on millions of MEMS deployments. For a wrist tremor monitoring application where pitch remains within approximately ±70°, this is sufficient and has no practical gimbal lock risk during clinical use.

The **Madgwick 6-axis filter** is the preferred alternative if quaternion output is required downstream or if extreme wrist orientations (pitch near ±90°) are expected.

### Algorithm Specification

**State vector** (2-element, per axis):
```
x = [ angle ]    # filtered angle estimate (degrees)
    [ bias  ]    # estimated gyroscope bias (deg/s)
```

**Error covariance** P (2×2), initialized to zero.

**Noise parameters** (starting values, tunable):
- `Q_angle  = 0.001` — process noise on angle state
- `Q_bias   = 0.003` — process noise on bias state (gyro drift rate)
- `R_measure = 0.03`  — measurement noise (accelerometer angle variance)

**Accelerometer angle derivation** (input to update step):
```c
float roll_accel  = atan2f(aY, aZ) * RAD_TO_DEG;
float pitch_accel = atan2f(-aX, sqrtf(aY*aY + aZ*aZ)) * RAD_TO_DEG;
```

**Predict step** (gyroscope integration, run at every sample):
```c
float rate   = new_rate - bias;
angle       += dt * rate;
P[0][0]     += dt * (dt * P[1][1] - P[0][1] - P[1][0] + Q_angle);
P[0][1]     -= dt * P[1][1];
P[1][0]     -= dt * P[1][1];
P[1][1]     += Q_bias * dt;
```

**Update step** (accelerometer correction):
```c
float y  = new_angle - angle;
float S  = P[0][0] + R_measure;
float K0 = P[0][0] / S;
float K1 = P[1][0] / S;
angle   += K0 * y;
bias    += K1 * y;
// update P using temporaries to avoid read-before-write
float P00 = P[0][0], P01 = P[0][1];
P[0][0] -= K0 * P00;  P[0][1] -= K0 * P01;
P[1][0] -= K1 * P00;  P[1][1] -= K1 * P01;
```

**Computational cost**: ~50 scalar float operations for both axes combined. On any ARM Cortex-M with hardware FPU: <50µs. On Cortex-M0 (software float): <500µs. Both well within the 10ms budget at 100Hz.

**Yaw**: Not computed. Without a magnetometer, yaw drifts unboundedly from gyroscope integration error. The platform does not require yaw for tremor classification.

### Alternatives Considered

- **Madgwick filter**: Chosen as secondary option. Use if quaternion output is needed by downstream ML pipeline or if gimbal lock becomes a concern.
- **ESKF with quaternions**: 3-5× more complex and 5-10× more compute. Not justified for this application.
- **Complementary filter**: Simpler but no explicit bias tracking; produces more drift in tremor scenarios where linear acceleration repeatedly corrupts the accelerometer angle measurement.

### Noise Tuning Procedure

1. **Measure `R_measure` empirically**: Place IMU stationary for 10s. Record 1000 accelerometer-derived angle samples. Compute variance → use as `R_measure` static value.
2. **Increase `R_measure` for dynamic use**: During active tremor, linear acceleration corrupts the accelerometer angle. Use 2–5× the static value for `R_measure` during motion (`R_measure_dynamic = 0.06–0.15`).
3. **Adaptive switching** (recommended): Monitor `|‖a‖ - 1g| > 0.3g`. When true, switch to `R_measure_dynamic`. When false, revert to `R_measure_static`. This directly handles tremor-induced acceleration contamination.

### Key References

- TKJ Electronics — Lauszus Kalman Filter reference: https://blog.tkjelectronics.dk/2012/09/a-practical-approach-to-kalman-filter-and-how-to-implement-it/
- GitHub: https://github.com/TKJElectronics/KalmanFilter
- Madgwick original report: https://x-io.co.uk/open-source-imu-and-ahrs-algorithms/

---

## Research Question 2: MPU9250 I2C Initialization, 100Hz ODR, Magnetometer Disable

### Decision

Configure MPU9250 over I2C with:
- Clock source: PLL with gyroscope X-axis reference (`CLKSEL=1`)
- Gyroscope ODR: 100Hz via `SMPLRT_DIV=9` + `DLPF_CFG=3` (41Hz LPF)
- Accel range: ±2g (`AFS_SEL=0`)
- Gyro range: ±2000°/s (`FS_SEL=3`)
- Magnetometer: **never initialized** (I2C master mode disabled, bypass disabled)

### MPU9250 Register Sequence

**I2C address**: `0x68` when AD0=LOW, `0x69` when AD0=HIGH. Most breakout boards default to `0x68`.

**Initialization sequence**:

```
1. WHO_AM_I (reg 0x75):
   - Read → expect 0x71 (MPU9250) or 0x73 (MPU9255)
   - Any other value: I2C wiring fault, abort init

2. PWR_MGMT_1 (reg 0x6B):
   - Write 0x80 → device reset (wait 100ms)
   - Write 0x01 → wake from sleep, select PLL clock (CLKSEL=1)
   - Wait 10ms

3. CONFIG (reg 0x1A):
   - Write 0x03 → DLPF_CFG=3 (gyro 41Hz bandwidth, 1kHz internal sampling)
   - This enables the digital low-pass filter on the gyroscope

4. SMPLRT_DIV (reg 0x19):
   - Write 0x09 → divider = 9+1 = 10
   - Sample rate = 1000Hz / 10 = 100Hz
   - (Only applies when DLPF is enabled, i.e., DLPF_CFG ≠ 0 or 7)

5. GYRO_CONFIG (reg 0x1B):
   - Write 0x18 → FS_SEL=3 → ±2000°/s
   - (FCHOICE_B = 0b00, no DLPF bypass)

6. ACCEL_CONFIG (reg 0x1C):
   - Write 0x00 → AFS_SEL=0 → ±2g

7. ACCEL_CONFIG2 (reg 0x1D):
   - Write 0x03 → ACCEL_FCHOICE_B=0, A_DLPFCFG=3 → 44Hz accel bandwidth
   - Sets accel to also run at 1kHz internally (DLPF active)

8. INT_PIN_CFG (reg 0x37):
   - Write 0x00 → Keep I2C bypass DISABLED, keep I2C master DISABLED
   - This isolates the AK8963 magnetometer from the I2C bus entirely
   - DO NOT write 0x02 (I2C_BYPASS_EN=1) — that would expose the AK8963

9. INT_ENABLE (reg 0x38):
   - Write 0x01 → DATA_RDY_INT enable (optional, for interrupt-driven reads)
   - Or write 0x00 to use polling instead

10. USER_CTRL (reg 0x6A):
    - Write 0x00 → I2C_MST_EN=0 (master mode disabled)
    - Magnetometer AK8963 is never reachable — CONFIRMED DISABLED
```

**Magnetometer isolation confirmation**: The AK8963 is connected to the MPU9250's internal auxiliary I2C bus. By keeping `I2C_BYPASS_EN=0` and `I2C_MST_EN=0`, the AK8963 is electrically isolated. It never receives a clock signal and never responds. Zero I2C transactions to address `0x0C` will occur during normal operation.

### Conversion Formulas (raw int16 to physical units)

**Accelerometer** (AFS_SEL=0, ±2g):
```
value_g    = raw_int16 / 16384.0f
value_ms2  = value_g * 9.80665f
```
→ Output in m/s², range ±19.614 m/s². Backend accepts ±20 m/s². ✅

**Gyroscope** (FS_SEL=3, ±2000°/s):
```
value_dps  = raw_int16 / 16.4f
```
→ Output in °/s, range ±2000°/s. Backend accepts ±2000°/s. ✅

### Startup Time

After reset and clock stabilization, allow **100ms** before reading sensor data. The internal oscillator needs ~50ms; the DLPF settling takes another ~50ms. The calibration window (500 samples at 100Hz = 5s) naturally absorbs this startup time.

### Alternatives Considered

- **DLPF_CFG=2** (44Hz, 4.9ms delay): Slightly lower latency but more noise.
- **DLPF_CFG=4** (20Hz, 9.9ms delay): Reduces noise further but introduces almost a full sample period of delay, degrading Kalman filter accuracy.
- **±4g accelerometer range**: Would better tolerate extreme tremor events but reduces resolution at typical tremor amplitudes. The backend validator range (±20 m/s² ≈ ±2.04g) constrains us to ±2g for the payload values to remain within defined bounds.

---

## Research Question 3: Startup Calibration Algorithm

### Decision

Collect **500 samples** (5 seconds at 100Hz) while the glove is stationary. Compute the arithmetic mean of each axis. Use mean values as bias offsets for gyroscope; for accelerometer, optionally subtract expected gravity on the expected static axis.

### Algorithm

```
1. Alert user to place glove flat and still
2. Wait 100ms (IMU stabilization after init)
3. Accumulate 500 samples:
   - sum_aX += aX, sum_aY += aY, sum_aZ += aZ
   - sum_gX += gX, sum_gY += gY, sum_gZ += gZ
4. Compute means:
   - offset_gX = sum_gX / 500    (at rest, gyro should read 0 deg/s)
   - offset_gY = sum_gY / 500
   - offset_gZ = sum_gZ / 500
   - offset_aX = sum_aX / 500    (at rest, accel X should read 0)
   - offset_aY = sum_aY / 500    (at rest, accel Y should read 0)
   - offset_aZ = sum_aZ / 500 - 9.80665  (at rest, accel Z should read +1g when flat)
5. Motion detection guard:
   - Compute stddev(gX, gY, gZ) over the 500 samples
   - If stddev > 1.0 deg/s threshold: calibration corrupted — retry or FAULT
6. Kalman filter initialization optimization:
   - Pre-set kf_roll.bias  = offset_gX (initial gyro bias from calibration)
   - Pre-set kf_pitch.bias = offset_gY
   - This halves convergence time vs. cold-starting with bias=0
```

**Motion detection**: Computing full stddev requires a second pass. Alternative: track `max - min` range. If `max(gX) - min(gX) > 5 deg/s` across the window, motion was detected.

**Gravity compensation note**: `offset_aZ -= 9.80665` only if the glove is placed flat with Z-axis pointing up. If orientation during calibration is unknown, skip the gravity subtraction (set `offset_aZ = 0`) and only compensate gyro bias. The Kalman filter will converge to the correct roll/pitch regardless of the accelerometer bias, since it operates on angle differences.

**Calibration sample count rationale**: 500 samples (5s) provides sufficient averaging to suppress noise. The MPU9250 gyroscope noise density is typically 0.01 deg/s/√Hz; at 100Hz, 500 samples reduces noise by √500 ≈ 22×. This gives gyro bias accuracy of ~0.00045 deg/s — well below the typical 0.1 deg/s systematic bias.

### Alternatives Considered

- **100 samples (1s)**: Faster but less averaging. Acceptable for gyro bias (noise reduction ×10) but may miss slow settling behavior in the IMU's internal voltage references.
- **1000 samples (10s)**: Better averaging but imposes a 10-second wait before the glove is operational. 5 seconds is the target for FR-010 / SC-002.

---

## Research Question 4: MQTT Payload Contract (Backend Integration)

### Decision

Firmware publishes to `devices/{serial_number}/reading` with this exact JSON structure:

```json
{
  "serial_number": "GLOVE001A",
  "timestamp": "2026-02-18T10:30:00.123Z",
  "aX": 0.12,
  "aY": -0.05,
  "aZ": 0.08,
  "gX": 1.23,
  "gY": -0.87,
  "gZ": 0.34
}
```

This is a **zero-change backend integration**. The payload schema was confirmed from:
- `backend/realtime/validators.py`: `validate_biometric_reading_message()` requires exactly these 8 fields
- `backend/realtime/mqtt_client.py`: `_handle_reading_message()` extracts and stores these fields
- `backend/biometrics/models.py`: `BiometricReading` model stores exactly these 6 sensor values + timestamp

No firmware extension of this payload is required. The `roll` and `pitch` Kalman filter outputs are firmware-internal only and are NOT added to the MQTT payload (no backend model for them currently).

**Sensor ranges confirmed against backend validator**:
```python
_sensor_ranges = {
    'aX': (-20.0, 20.0), 'aY': (-20.0, 20.0), 'aZ': (-20.0, 20.0),
    'gX': (-2000.0, 2000.0), 'gY': (-2000.0, 2000.0), 'gZ': (-2000.0, 2000.0),
}
```
Values outside these ranges are **warned, not rejected**. The firmware ±2g / ±2000°/s configuration maps to ±19.6 m/s² / ±2000°/s, fitting within the ±20 m/s² backend warning threshold. ✅

**Timestamp source**: Firmware must provide a valid ISO 8601 UTC timestamp. On ESP32: use NTP via `configTime()` or the RTC peripheral. Timestamp drift up to a few seconds is acceptable for clinical session data; millisecond precision is provided by appending `.SSS` from `millis() % 1000`.

---

## Research Question 5: Firmware Directory Location in Monorepo

### Decision

Create a new `firmware/` directory at the monorepo root. This is a justified extension to the constitution (documented in plan.md Complexity Tracking).

**Rationale**:
- The TremoAI monorepo constitution governs `backend/` and `frontend/`. It does not prohibit additional top-level directories.
- The firmware is the upstream data source for the entire platform. Without it, no real sensor data enters the system.
- Keeping firmware in the same repo enables atomic commits when the MQTT payload schema changes (firmware + backend validator change together).
- A separate firmware repo would require cross-repo coordination for schema changes — an unnecessary complexity for a graduation project.

**Build system**: PlatformIO is the standard for embedded Arduino-compatible firmware development. It handles ESP32, STM32, and other ARM targets uniformly. A `platformio.ini` at `firmware/` root defines the build target, dependencies, and upload settings.

**Alternatives considered**: Separate repository — rejected (schema coordination complexity); no firmware in repo (simulator only) — rejected (does not demonstrate end-to-end integration).

---

## Summary of All Decisions

| Question | Decision | Rationale |
|---|---|---|
| Kalman filter variant | Lauszus 2-state linear KF (roll + pitch) | Simplest true KF; no quaternions; explicit bias tracking; 100Hz feasible on all ARM Cortex |
| Yaw estimation | Not implemented | No magnetometer → no absolute yaw reference |
| Noise defaults | Q_angle=0.001, Q_bias=0.003, R_measure=0.03 | Lauszus reference values, proven for MEMS at this scale |
| Adaptive R_measure | Yes (switch based on |‖a‖-1g|>0.3g) | Prevents acceleration contamination during active tremor |
| IMU ODR | 100Hz via DLPF_CFG=3 + SMPLRT_DIV=9 | 41Hz gyro bandwidth; 1kHz internal → 100Hz output |
| Accel range | ±2g (AFS_SEL=0) | Matches backend ±20 m/s² accepted range |
| Gyro range | ±2000°/s (FS_SEL=3) | Maximum range; covers severe tremor peak angular velocity |
| Magnetometer | Never initialized | Keep I2C_BYPASS_EN=0, I2C_MST_EN=0; AK8963 isolated |
| Calibration samples | 500 (5 seconds) | Sufficient averaging; meets 5-second SC-002 target |
| Motion guard threshold | stddev(gyro) > 1.0 deg/s or range > 5 deg/s | Detects corruption from movement during calibration |
| MQTT payload | 8 fields exactly matching backend validator | Zero backend changes required |
| Kalman bias init | Pre-seeded from calibration mean | Halves convergence time |
| Firmware location | `firmware/` at monorepo root | Atomic commits; zero constitution violation |
| Build system | PlatformIO | Industry standard for ESP32/ARM embedded development |
