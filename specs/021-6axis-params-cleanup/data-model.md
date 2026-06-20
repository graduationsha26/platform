# Data Model: MQTT Parser and Normalization 6-Axis Cleanup (Feature 021)

**Branch**: `021-6axis-params-cleanup` | **Date**: 2026-02-18

---

## Feature Context

Feature 021 is a cleanup and documentation feature — no new data entities are introduced. The relevant entities already exist and are already in the correct state.

---

## Normalization Configuration (params.json)

Represents the statistical parameters used to normalize raw 6-axis sensor readings before ML inference.

### Schema

```json
{
  "features": [
    {"name": "<axis>", "mean": <float>, "std": <float>},
    ...
  ],
  "metadata": {
    "generated_from": "<csv_filename>",
    "n_samples": <integer>,
    "generated_date": "<ISO 8601 datetime>"
  }
}
```

### Required Feature Entries

| Entry | Axis | Sensor | Units (hardware) |
|---|---|---|---|
| `aX` | X | Accelerometer | Raw ADC counts |
| `aY` | Y | Accelerometer | Raw ADC counts |
| `aZ` | Z | Accelerometer | Raw ADC counts |
| `gX` | X | Gyroscope | Raw ADC counts |
| `gY` | Y | Gyroscope | Raw ADC counts |
| `gZ` | Z | Gyroscope | Raw ADC counts |

**Explicitly absent**:

| Entry | Why Absent |
|---|---|
| `mX`, `mY`, `mZ` | Hardware magnetometer disabled; all values = −1 constant; dropped from training data before statistics are computed |
| `flex_1` – `flex_5` | Flex sensors removed from hardware; dropped in Feature E-2.1 |

### Validation Rules

- Must contain exactly **6** feature entries.
- Each entry must have `name`, `mean`, and `std` keys.
- `std` must be > 0 for every feature (prevents division-by-zero in normalization).
- Feature names must match `FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` in order.

### Current File Location

`backend/ml_data/params.json`

---

## MQTT Sensor Reading Message (inbound, not stored)

Represents an incoming real-time sensor payload received from the wearable glove over MQTT.

### Required Fields (validated)

| Field | Type | Description |
|---|---|---|
| `serial_number` | string (8–20 chars, uppercase alphanumeric) | Device identifier |
| `timestamp` | string (ISO 8601) | Reading timestamp from device |
| `aX` | numeric | Accelerometer X-axis |
| `aY` | numeric | Accelerometer Y-axis |
| `aZ` | numeric | Accelerometer Z-axis |
| `gX` | numeric | Gyroscope X-axis |
| `gY` | numeric | Gyroscope Y-axis |
| `gZ` | numeric | Gyroscope Z-axis |

### Silently Ignored Fields

| Field | Reason |
|---|---|
| `mX`, `mY`, `mZ` | Magnetometer disabled; constant −1 values; not extracted or stored |
| `flex_1` – `flex_5` | Flex sensors removed from hardware; legacy firmware may still include them |
| Any other unknown field | Silently discarded per validator design |

### What Gets Stored

After the MQTT message is processed, a `BiometricReading` record is created with exactly:
`patient`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`

No magnetometer or flex data enters the database.

---

## Relationship Between Entities

```text
MQTT Message (inbound)
  → validate_biometric_reading_message()   [6 required fields; rest silently ignored]
  → BiometricReading.objects.create()      [6 axes stored]
  → BiometricReading (database record)     [6 axes only]

BiometricReading (or direct sensor dict)
  → apps/ml/feature_utils.FEATURE_COLUMNS [6-axis definition]
  → apps/ml/normalize.normalize_features() [z-score using params.json]
  → ML/DL model inference                 [6-feature vector]
  → Prediction result (severity, confidence)

params.json                               [6-axis mean/std config]
  → apps/ml/normalize.load_params()       [validated: exactly 6 entries]
  → normalize_features()                  [applied to live sensor data]
```
