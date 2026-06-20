# Quickstart: IMU Kalman Fusion — Integration Guide

**Feature**: 025-imu-kalman-fusion | **Date**: 2026-02-18

This guide describes how the firmware integrates with the TremoAI platform, how to test the end-to-end pipeline, and what to verify at each integration point.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                TremoAI Smart Glove                  │
│                                                     │
│  MPU9250 ──I2C──► imu.cpp                          │
│                        │                            │
│                        ▼                            │
│                  Startup Calibration                │
│                  (500 samples @ rest)               │
│                        │                            │
│                        ▼                            │
│                 100Hz Sampling Loop                 │
│                        │                            │
│                        ▼                            │
│               Kalman Filter (roll, pitch)           │
│                        │                            │
│                        ▼                            │
│           mqtt_publisher.cpp (JSON publish)         │
└──────────────┬──────────────────────────────────────┘
               │ MQTT (devices/{serial}/reading)
               ▼
      ┌─────────────────┐
      │  MQTT Broker    │  (Mosquitto, localhost:1883)
      └────────┬────────┘
               │
               ▼
      ┌─────────────────────────────────────────────┐
      │           Django Backend                    │
      │   realtime/mqtt_client.py                   │
      │   _handle_reading_message()                 │
      │        │                                    │
      │        ▼                                    │
      │   validate_biometric_reading_message()      │
      │        │                                    │
      │        ▼                                    │
      │   BiometricReading.objects.create(...)      │
      │        │                                    │
      │        ▼                                    │
      │   Supabase PostgreSQL (biometric_readings)  │
      └─────────────────────────────────────────────┘
```

---

## Integration Scenario 1: First Boot & Calibration

**Preconditions**:
- Glove is powered off
- MQTT broker is running at `localhost:1883`
- Django backend MQTT subscriber is running (`python manage.py runserver` + management command)
- Glove device is registered in the platform with a valid serial number

**Steps**:
1. Place the glove flat on a surface (dorsal side up, minimal movement)
2. Power on the glove
3. Observe the status LED (if present) — should blink during calibration (~5 seconds)
4. After calibration, LED changes to solid → RUNNING state

**Expected outcome**:
- Firmware log: `[IMU] WHO_AM_I OK (0x71)`
- Firmware log: `[IMU] Magnetometer disabled`
- Firmware log: `[CALIB] Collecting 500 samples...`
- Firmware log: `[CALIB] Done. Offsets: aX=X.XX aY=X.XX aZ=X.XX gX=X.XX gY=X.XX gZ=X.XX`
- Firmware log: `[MQTT] Connected. Publishing to devices/GLOVE001A/reading`
- Backend log: `Received MQTT message on topic: devices/GLOVE001A/reading`
- Backend log: `Stored BiometricReading: id=1 for patient X`

**Verification**:
```bash
# Check backend received the reading
python manage.py shell -c "from biometrics.models import BiometricReading; print(BiometricReading.objects.count())"
```

---

## Integration Scenario 2: Continuous 100Hz Streaming

**Preconditions**: Glove is in RUNNING state (calibration complete).

**Verify 100Hz rate**:
1. Monitor MQTT broker for incoming messages:
   ```bash
   mosquitto_sub -t "devices/+/reading" -v
   ```
2. Count messages over 10 seconds → expect ~1000 messages

**Verify JSON payload format**:
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

**Verify database accumulation**:
```bash
# After 60 seconds, expect ~6000 BiometricReading records
python manage.py shell -c "
from biometrics.models import BiometricReading
import time
c1 = BiometricReading.objects.count()
time.sleep(10)
c2 = BiometricReading.objects.count()
print(f'Rate: {(c2-c1)/10:.1f} Hz (expected: ~100 Hz)')
"
```

---

## Integration Scenario 3: Kalman Filter Quality Validation

**Purpose**: Verify the Kalman filter is reducing noise vs. raw accelerometer readings.

**Setup**: Connect a serial monitor to the glove firmware (UART debug output).

**Test A — Static noise test**:
1. Hold the glove completely still for 30 seconds
2. Log both `raw_aZ` and `kalman_pitch` values
3. Compute variance of each over the 30-second window
4. Expected: `var(kalman_pitch) < 0.5 * var(raw_accel_pitch)`

**Test B — Motion convergence test**:
1. Hold the glove at 0° orientation
2. Rotate to ~45° pitch, hold still
3. Measure time for `kalman_pitch` to stabilize within ±2° of true angle
4. Expected: convergence within 2 seconds

**Test C — Magnetometer absence confirmation**:
```bash
# Monitor I2C bus transactions using logic analyzer or software I2C sniffer
# AK8963 I2C address: 0x0C
# Should see ZERO read/write transactions to address 0x0C during operation
# (Any transaction to 0x0C would indicate magnetometer is active — this is a fail)
```

---

## Integration Scenario 4: Fault State Handling

**Scenario A — IMU not detected**:
1. Disconnect the MPU9250 I2C lines
2. Power on the glove
3. Expected: firmware enters FAULT state within 500ms; no MQTT messages published
4. Backend receives no readings for this device

**Scenario B — Motion during calibration**:
1. Power on the glove while actively shaking it
2. Expected: firmware detects excessive motion (gyro stddev > threshold)
3. Expected: retries calibration or enters FAULT state (depending on implementation)
4. No readings published until calibration succeeds

---

## Device Configuration (config.h)

The firmware uses a configuration header (not runtime `.env`) for device-specific settings:

```c
// firmware/include/config.h
// DO NOT COMMIT real credentials — use a local override or template pattern

#define DEVICE_SERIAL      "GLOVE001A"        // Must match backend Device.serial_number
#define MQTT_BROKER_HOST   "192.168.1.100"    // Local broker IP
#define MQTT_BROKER_PORT   1883
#define MQTT_USERNAME      ""                 // Set if broker requires auth
#define MQTT_PASSWORD      ""                 // Set if broker requires auth
#define WIFI_SSID          "YourNetwork"      // WiFi credentials
#define WIFI_PASSWORD      "YourPassword"     // Keep out of git

// IMU Configuration
#define IMU_SAMPLE_RATE_HZ    100
#define CALIB_N_SAMPLES       500
#define GYRO_MOTION_THRESHOLD 1.0f   // °/s stddev — above this = motion detected during calib

// Kalman Filter Tuning
#define KF_Q_ANGLE    0.001f
#define KF_Q_BIAS     0.003f
#define KF_R_MEASURE  0.03f
```

**Security note**: `config.h` with real credentials must be added to `.gitignore`. Commit only `config.h.example` with placeholder values.

---

## MQTT Broker Setup (Development)

```bash
# Install Mosquitto
sudo apt-get install mosquitto mosquitto-clients   # Linux
brew install mosquitto                              # macOS

# Start broker (no auth for local dev)
mosquitto -v

# Test subscription (in separate terminal)
mosquitto_sub -t "devices/+/reading" -v
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `WHO_AM_I` read returns 0xFF | I2C wiring issue or wrong I2C address | Check SDA/SCL connections; try AD0=HIGH (address 0x69) |
| Calibration never completes | IMU never responds after init | Check power supply (3.3V), I2C pullups (4.7kΩ) |
| `gX/gY/gZ` all read 0 after calib | Calibration subtracted too much | Verify glove was stationary; check CALIB_N_SAMPLES |
| Backend shows validation warnings | Sensor values slightly out of range | Normal — backend accepts with warning. Check sensor range config. |
| No readings in database | Device serial not registered | Register the device serial in Django admin: `Devices > Add device` |
| Kalman pitch drifts over time | `Q_bias` too small or `R_measure` too high | Increase `KF_Q_BIAS` or decrease `KF_R_MEASURE` |
