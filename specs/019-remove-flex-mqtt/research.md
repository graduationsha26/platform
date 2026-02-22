# Research: Remove Flex Fields from MQTT Parser

**Branch**: `019-remove-flex-mqtt` | **Date**: 2026-02-18
**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Research Question 1: Current State of Flex References in MQTT Code

**Question**: Does any existing MQTT parsing code in the `realtime/` module currently expect or reference flex_1 through flex_5?

**Findings**:

Audit of all Python files in `backend/realtime/`:

| File | Flex References | Notes |
|------|----------------|-------|
| `realtime/validators.py` | None | Required fields: serial_number, timestamp, tremor_intensity, frequency, timestamps, session_duration |
| `realtime/mqtt_client.py` | None | Stores BiometricSession records only |
| `realtime/tests/test_mqtt_client.py` | None | Test payloads use tremor_intensity/frequency/timestamps |
| `realtime/consumers.py` | None | WebSocket consumer; no sensor field references |
| `realtime/ml_service.py` | None | Feature extraction uses tremor_intensity/frequency only |

Flex references in the wider codebase are confined to:
- `biometrics/migrations/0002_add_biometricreading.py` — historical: migration that created BiometricReading with flex columns
- `biometrics/migrations/0003_remove_flex_fields.py` — historical: migration that dropped the flex columns
- `biometrics/views.py` line 221, `biometrics/serializers.py` line 200 — comments documenting intentional exclusion

**Decision**: The existing session-level MQTT handler (`mqtt_client.py` / `validators.py`) is already clean of flex references. No changes needed to the existing session message pipeline.

---

## Research Question 2: BiometricReading MQTT Handler Status

**Question**: Is there an existing MQTT message handler that creates BiometricReading records from raw sensor data?

**Findings**:

The current `MQTTClient` subscribes to exactly one topic pattern:
```
devices/+/data
```
It processes session-level messages (`tremor_intensity`, `frequency`, `timestamps`, `session_duration`) and creates `BiometricSession` records.

There is no MQTT handler that creates `BiometricReading` records (the model for individual raw sensor readings with fields aX, aY, aZ, gX, gY, gZ). The `BiometricReadingViewSet` is read-only, confirming records must arrive via an ingestion path other than the REST API.

**Decision**: A raw-sensor-reading MQTT message handler does not yet exist. This feature provides the correct opportunity to implement it — from the ground up, without flex field expectations.

---

## Research Question 3: MQTT Message Schema for Raw Sensor Readings

**Question**: What is the correct MQTT message schema for individual sensor readings from the glove device?

**Context**:
- The BiometricReading model stores: `patient` (FK), `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`
- The glove hardware exposes accelerometer (3-axis) and gyroscope (3-axis) readings
- Flex sensors (flex_1-flex_5) have been removed from the hardware (Feature E-2.1 context)
- The feature_utils.py already defines `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`

**Decision — Schema**:
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

**Rationale**: Matches the BiometricReading model fields exactly. No flex fields. Mirrors the pattern of the existing session message (serial_number + timestamp + payload fields).

**Backward compatibility**: Any message that includes extra fields (e.g., legacy flex_1-flex_5 from older firmware) is accepted — unknown fields are ignored. The validator requires only the seven listed fields.

---

## Research Question 4: MQTT Topic Structure for Raw Readings

**Question**: What MQTT topic should the glove device publish raw sensor readings to?

**Context**:
- Existing topic: `devices/{serial}/data` → session-level summaries → BiometricSession
- Consistent naming convention: `devices/{serial}/{message-type}`

**Decision — Topic**:
```
devices/{serial}/reading
```

**Rationale**: Consistent with existing convention. `data` carries processed session summaries; `reading` carries raw per-sample sensor readings. The `MQTTClient` subscribes to both patterns using paho-mqtt's wildcard support.

**Alternatives considered**:
- `devices/{serial}/raw` — considered but `reading` maps more cleanly to the `BiometricReading` model name
- Same topic with different payload structure — rejected because it complicates dispatch logic and makes validation ambiguous

---

## Research Question 5: Validation Rules for Raw Reading Messages

**Question**: What validation rules apply to raw sensor readings from the glove?

**Findings from feature_utils.py**:

```python
SENSOR_RANGES = {
    'aX': (-20.0, 20.0),   # m/s²
    'aY': (-20.0, 20.0),
    'aZ': (-20.0, 20.0),
    'gX': (-2000.0, 2000.0),  # °/s
    'gY': (-2000.0, 2000.0),
    'gZ': (-2000.0, 2000.0),
}
```

**Decision — Validation rules**:

| Field | Type | Constraint |
|-------|------|-----------|
| `serial_number` | string | 8-20 uppercase alphanumeric characters |
| `timestamp` | string | ISO 8601 UTC format |
| `aX` | number | Range: -20.0 to 20.0 (m/s²) |
| `aY` | number | Range: -20.0 to 20.0 (m/s²) |
| `aZ` | number | Range: -20.0 to 20.0 (m/s²) |
| `gX` | number | Range: -2000.0 to 2000.0 (°/s) |
| `gY` | number | Range: -2000.0 to 2000.0 (°/s) |
| `gZ` | number | Range: -2000.0 to 2000.0 (°/s) |

Flex fields (flex_1-flex_5): silently ignored if present; never validated, never stored.

Out-of-range values: emit a warning and accept the reading (same pattern as `validate_sensor_ranges(warn_only=True)` in `feature_utils.py`).

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Existing session pipeline | No changes needed | Already flex-free |
| BiometricReading MQTT handler | Implement new | No existing handler; correct moment to add flex-free from ground up |
| MQTT topic for readings | `devices/+/reading` | Consistent with existing `devices/+/data` convention |
| Schema for reading message | serial_number + timestamp + aX/aY/aZ/gX/gY/gZ | Matches model; no flex fields |
| Flex fields in incoming payload | Silently ignore | Backward compatibility with legacy firmware |
| Out-of-range sensor values | Warn and accept | Consistent with existing `feature_utils.py` approach |
| New files to create | `validate_biometric_reading_message()` in validators.py; handler in mqtt_client.py | Minimal footprint, consistent location |
