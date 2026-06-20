# Data Model: Remove Flex Fields from MQTT Parser

**Branch**: `019-remove-flex-mqtt` | **Date**: 2026-02-18
**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

---

## Overview

This feature introduces no new database models and no migrations. The `BiometricReading` model was already updated in Feature E-2.1 (branch 017-remove-flex-fields) to remove flex columns. This document defines the **MQTT message schemas** (inbound sensor data contracts) and clarifies how they map to the existing model.

---

## MQTT Message Schemas

### Schema 1: Session Message (existing — no changes)

**Topic**: `devices/{serial_number}/data`
**Creates**: `BiometricSession` record

```json
{
  "serial_number":     "GLVXXXXXXXX",
  "timestamp":         "2026-02-18T10:30:00.000Z",
  "tremor_intensity":  [0.25, 0.30, 0.28, 0.32],
  "frequency":         4.5,
  "timestamps":        ["2026-02-18T10:30:00.000Z", "..."],
  "session_duration":  1000
}
```

**Validation**: Handled by existing `validate_mqtt_message()` in `realtime/validators.py`.
**Flex fields**: Not present, not expected. No changes required.

---

### Schema 2: Raw Reading Message (new)

**Topic**: `devices/{serial_number}/reading`
**Creates**: `BiometricReading` record

```json
{
  "serial_number": "GLVXXXXXXXX",
  "timestamp":     "2026-02-18T10:30:00.123Z",
  "aX":  1.23,
  "aY": -0.45,
  "aZ":  9.81,
  "gX":  0.12,
  "gY": -0.34,
  "gZ":  0.56
}
```

**Flex backward-compatibility**: If a legacy device includes `flex_1` through `flex_5` in this payload, those keys are silently discarded and never stored.

---

## Field Definitions: Raw Reading Message

| Field | JSON Type | Required | Constraint | Maps to BiometricReading |
|-------|-----------|----------|-----------|--------------------------|
| `serial_number` | string | Yes | 8-20 uppercase alphanumeric | Used to look up `Device` → `Patient` |
| `timestamp` | string | Yes | ISO 8601 UTC | `BiometricReading.timestamp` |
| `aX` | number | Yes | -20.0 to +20.0 (m/s²) | `BiometricReading.aX` |
| `aY` | number | Yes | -20.0 to +20.0 (m/s²) | `BiometricReading.aY` |
| `aZ` | number | Yes | -20.0 to +20.0 (m/s²) | `BiometricReading.aZ` |
| `gX` | number | Yes | -2000.0 to +2000.0 (°/s) | `BiometricReading.gX` |
| `gY` | number | Yes | -2000.0 to +2000.0 (°/s) | `BiometricReading.gY` |
| `gZ` | number | Yes | -2000.0 to +2000.0 (°/s) | `BiometricReading.gZ` |
| `flex_1` | any | **No** | Ignored if present | Not stored |
| `flex_2` | any | **No** | Ignored if present | Not stored |
| `flex_3` | any | **No** | Ignored if present | Not stored |
| `flex_4` | any | **No** | Ignored if present | Not stored |
| `flex_5` | any | **No** | Ignored if present | Not stored |

---

## Existing Model: BiometricReading (no changes)

```
BiometricReading
├── id          (BigAutoField, PK)
├── patient     (ForeignKey → Patient, CASCADE)
├── timestamp   (DateTimeField)
├── aX          (FloatField)   — Accelerometer X-axis
├── aY          (FloatField)   — Accelerometer Y-axis
├── aZ          (FloatField)   — Accelerometer Z-axis
├── gX          (FloatField)   — Gyroscope X-axis
├── gY          (FloatField)   — Gyroscope Y-axis
└── gZ          (FloatField)   — Gyroscope Z-axis

DB Table: biometric_readings
Indexes:  (patient, timestamp), (timestamp,)
```

Note: `device` is not a foreign key on `BiometricReading`. The device is used during MQTT message processing to resolve the associated patient, then only `patient` is stored on the record.

---

## Processing Flow

```
MQTT Broker
  │
  └── Topic: devices/{serial}/reading
        │
        ▼
validate_biometric_reading_message(payload)
  ├── Check: serial_number present + format valid
  ├── Check: timestamp present + ISO 8601 valid
  ├── Check: aX, aY, aZ, gX, gY, gZ present + numeric
  ├── Warn (don't reject): sensor values out of physical range
  └── Ignore: any extra fields (flex_1-flex_5, etc.)
        │
        ▼
validate_device_pairing(serial_number)   ← existing function
  └── Returns (Device, Patient) or rejects
        │
        ▼
BiometricReading.objects.create(
  patient=patient,
  timestamp=parsed_timestamp,
  aX=payload['aX'],
  aY=payload['aY'],
  aZ=payload['aZ'],
  gX=payload['gX'],
  gY=payload['gY'],
  gZ=payload['gZ'],
)
```

---

## Source Files Affected

| File | Change Type | Description |
|------|------------|-------------|
| `backend/realtime/validators.py` | **Modify** | Add `validate_biometric_reading_message()` function |
| `backend/realtime/mqtt_client.py` | **Modify** | Subscribe to `devices/+/reading`; add `_handle_reading_message()` handler |
| `backend/realtime/tests/test_mqtt_client.py` | **Modify** | Add test cases for raw reading message validation and handling |

No migrations. No new Django apps. No frontend changes.
