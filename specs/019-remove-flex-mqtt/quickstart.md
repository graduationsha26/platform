# Quickstart: MQTT Raw Sensor Reading Integration

**Feature**: Remove Flex Fields from MQTT Parser (`019-remove-flex-mqtt`)
**Date**: 2026-02-18

This guide shows how the raw sensor reading MQTT pipeline works after this feature is implemented.

---

## Overview

The TremoAI platform handles two distinct MQTT message types from the glove device:

| Topic | Message Type | Creates | Handler |
|-------|-------------|---------|---------|
| `devices/{serial}/data` | Session summary | `BiometricSession` | Existing (unchanged) |
| `devices/{serial}/reading` | Raw sensor reading | `BiometricReading` | **New (this feature)** |

---

## Scenario 1: Updated Glove Firmware (6-field payload)

**Given**: A glove with updated firmware publishes a raw sensor reading.

**MQTT Message** (published by glove):
```json
{
  "serial_number": "GLV20241001",
  "timestamp":     "2026-02-18T10:30:00.123Z",
  "aX":  1.23,
  "aY": -0.45,
  "aZ":  9.81,
  "gX":  0.12,
  "gY": -0.34,
  "gZ":  0.56
}
```
**Topic**: `devices/GLV20241001/reading`

**Processing flow**:
1. `MQTTClient.on_message()` receives message on `devices/GLV20241001/reading`
2. Dispatches to `_handle_reading_message(payload, topic)`
3. Calls `validate_biometric_reading_message(payload)` → **passes** (all 6 fields present and valid)
4. Calls `validate_device_pairing("GLV20241001")` → returns `(Device, Patient)`
5. Creates `BiometricReading`:
   ```
   BiometricReading(
     patient=<Patient>,
     timestamp=2026-02-18 10:30:00.123+00:00,
     aX=1.23, aY=-0.45, aZ=9.81,
     gX=0.12, gY=-0.34, gZ=0.56
   )
   ```

**Result**: ✅ BiometricReading record stored. No flex fields involved at any step.

---

## Scenario 2: Legacy Glove Firmware (11-field payload with flex)

**Given**: An older glove still including flex sensor values in its payload.

**MQTT Message** (published by legacy glove):
```json
{
  "serial_number": "GLV20230501",
  "timestamp":     "2026-02-18T10:30:00.456Z",
  "aX":  0.98,
  "aY":  0.12,
  "aZ":  9.78,
  "gX": -0.05,
  "gY":  0.22,
  "gZ":  0.01,
  "flex_1": 0.50,
  "flex_2": 0.33,
  "flex_3": 0.71,
  "flex_4": 0.20,
  "flex_5": 0.44
}
```
**Topic**: `devices/GLV20230501/reading`

**Processing flow**:
1. `validate_biometric_reading_message(payload)` — validates only the 6 required fields
2. `flex_1` through `flex_5` are present but not in the required fields list → **silently ignored**
3. `validate_device_pairing("GLV20230501")` → returns `(Device, Patient)`
4. Creates `BiometricReading` with **only** the 6 standard sensor values

**Result**: ✅ BiometricReading record stored without any flex values. Legacy payload does not cause errors.

---

## Scenario 3: Payload Missing a Required Sensor Field

**Given**: A malformed payload is missing `gZ`.

**MQTT Message**:
```json
{
  "serial_number": "GLV20241001",
  "timestamp":     "2026-02-18T10:30:00.789Z",
  "aX": 1.10,
  "aY": 0.20,
  "aZ": 9.80,
  "gX": 0.05,
  "gY": 0.10
}
```

**Processing flow**:
1. `validate_biometric_reading_message(payload)` → raises `ValidationError: Missing required fields: gZ`
2. Error is logged at WARNING level
3. No BiometricReading record is created

**Result**: ❌ Message rejected with clear validation error. Other messages are unaffected.

---

## Scenario 4: Session Message (devices/{serial}/data) — Unchanged

The existing session-level MQTT pipeline continues to operate without modification. A session message published to `devices/{serial}/data` is handled by the existing `on_message()` / `_store_to_database()` path and creates a `BiometricSession` record.

```
devices/{serial}/data   → on_message() → validate_mqtt_message() → BiometricSession
devices/{serial}/reading → on_message() → validate_biometric_reading_message() → BiometricReading
```

The two pipelines are independent. A failure in one does not affect the other.

---

## Validation Reference

`validate_biometric_reading_message(payload)` — new function in `realtime/validators.py`:

| Check | Failure action |
|-------|---------------|
| `serial_number` missing | Reject |
| `serial_number` not string, not 8-20 uppercase alphanumeric | Reject |
| `timestamp` missing | Reject |
| `timestamp` not valid ISO 8601 | Reject |
| Any of `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` missing | Reject |
| Any of the six sensor values not numeric | Reject |
| Sensor value out of physical range | Warn + accept |
| `flex_1` through `flex_5` present | Ignore silently |
| Any other unexpected field present | Ignore silently |
