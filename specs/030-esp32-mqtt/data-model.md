# Data Model: ESP32 WiFi + MQTT Client (Feature 030)

**Branch**: `030-esp32-mqtt`
**Date**: 2026-02-19

---

## Overview

Feature 030 is a firmware + backend message-format feature. There are no new database models. The data entities here describe the in-flight MQTT message structure and the firmware-internal data structures that produce it.

---

## Entity 1: SensorMessage (MQTT Payload)

The canonical JSON message published by the glove at 30–50 Hz.

| Field | Type | Unit | Constraints |
|-------|------|------|-------------|
| `device_id` | string | — | 8–20 uppercase alphanumeric characters; matches `Device.serial_number` in Django |
| `timestamp` | string | — | ISO 8601 UTC, e.g. `"2026-02-18T10:30:00.123Z"` |
| `aX` | float | m/s² | Range: −20.0 to +20.0 (±2 g; values outside range are accepted with a warning) |
| `aY` | float | m/s² | Range: −20.0 to +20.0 |
| `aZ` | float | m/s² | Range: −20.0 to +20.0 |
| `gX` | float | °/s | Range: −2000.0 to +2000.0 (±2000 °/s; values outside range accepted with warning) |
| `gY` | float | °/s | Range: −2000.0 to +2000.0 |
| `gZ` | float | °/s | Range: −2000.0 to +2000.0 |
| `battery_level` | float | % | Range: 0.0 to 100.0 (clamped at firmware; backend accepts 0–100) |

**MQTT transport properties**:
- Topic: `tremo/sensors/{device_id}` (e.g. `tremo/sensors/GLOVE001A`)
- QoS: 1 (at-least-once delivery)
- Retain: false
- Max serialized size: ~200 bytes

**Relationship to backend**:
- `device_id` maps to `Device.serial_number` (used in `validate_device_pairing()`)
- All 9 fields are stored in `BiometricReading` model (existing) after extraction in `mqtt_client.py`
- `battery_level` is a new field — the `BiometricReading` model may need a new column (deferred to a separate migration feature if needed; initial implementation stores battery_level in the MQTT handler but does not persist it)

---

## Entity 2: BatteryReading (Firmware-Internal)

Represents one ADC sample from the battery monitoring circuit.

| Field | Type | Notes |
|-------|------|-------|
| `adc_mv` | uint32_t | ADC reading in millivolts via `analogReadMilliVolts()` (factory-calibrated, corrects ESP32 non-linearity) |
| `voltage_v` | float | Computed: `(adc_mv / 1000.0) / divider_ratio` |
| `percentage` | float | Linear map of voltage to 0–100 % over LiPo range (3.0–4.2 V), clamped |

Produced by `battery_reader.cpp`, consumed once per MQTT publish cycle. **ADC pin must be GPIO32–39 (ADC1); ADC2 pins are unreliable when WiFi is active.** GPIO34 is the default (input-only, no conflicts).

---

## Entity 3: FusedReading (Firmware-Internal, Modified)

Extends the existing `FusedReading` struct in `mqtt_publisher.h` to carry `battery_level`.

| Field | Type | Notes |
|-------|------|-------|
| `aX`, `aY`, `aZ` | float | m/s², calibrated (existing) |
| `gX`, `gY`, `gZ` | float | °/s, calibrated (existing) |
| `roll` | float | degrees, Kalman-filtered, firmware-internal (existing, not in payload) |
| `pitch` | float | degrees, Kalman-filtered, firmware-internal (existing, not in payload) |
| `timestamp_iso` | char[32] | ISO 8601 UTC string (existing) |
| `battery_level` | float | % (new) — populated in main.cpp before publish call |

---

## MQTT Topic Structure

```
tremo/
└── sensors/
    └── {device_id}/     ← one topic per device, device_id = Device.serial_number
```

**Subscription wildcard** (backend `mqtt_client.py`):
```
tremo/sensors/+          ← matches all device topics
```

The `+` wildcard extracts `device_id` from the topic path (position 1, 0-indexed: `parts[1]` after splitting on `/`).

---

## Backend Validator Changes (No New DB Model)

The existing `validate_biometric_reading_message()` in `backend/realtime/validators.py` is updated:

| Change | From | To |
|--------|------|----|
| Required field name | `serial_number` | `device_id` |
| Added optional field | — | `battery_level` (float, 0–100) |
| Device lookup | `validate_device_pairing(serial_number)` | `validate_device_pairing(device_id)` (same function, renamed param) |

The `BiometricReading` model is NOT modified in this feature. `battery_level` is validated and extracted in the handler but not stored (requires a separate migration).
