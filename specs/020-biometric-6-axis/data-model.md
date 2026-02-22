# Data Model: Biometric 6-Axis Field Cleanup (Feature 020)

**Branch**: `020-biometric-6-axis` | **Date**: 2026-02-18

---

## BiometricReading

Represents a single timestamped raw sensor measurement received from a patient's wearable glove device over MQTT.

### Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | BigInt (PK) | auto, primary key | Unique record identifier |
| `patient` | FK → Patient | CASCADE delete | Patient who wore the device |
| `timestamp` | DateTime | not null | Timestamp of the sensor reading (from device payload) |
| `aX` | Float | not null | Accelerometer X-axis (m/s²) |
| `aY` | Float | not null | Accelerometer Y-axis (m/s²) |
| `aZ` | Float | not null | Accelerometer Z-axis (m/s²) |
| `gX` | Float | not null | Gyroscope X-axis (°/s) |
| `gY` | Float | not null | Gyroscope Y-axis (°/s) |
| `gZ` | Float | not null | Gyroscope Z-axis (°/s) |

### Explicitly Absent Fields

| Field | Why Absent |
|---|---|
| `mX`, `mY`, `mZ` | Hardware magnetometer is disabled (all values would be −1); never added to this model |
| `flex_1` – `flex_5` | Flex sensors removed from glove hardware; added to initial migration then dropped in 0003 |

### Database Table

- **Table name**: `biometric_readings`
- **Ordering**: `-timestamp` (newest first)
- **Indexes**:
  - `(patient_id, timestamp)` — for filtering readings by patient in time order
  - `(timestamp)` — for time-range queries across all patients

### Migration History

| Migration | What It Does |
|---|---|
| `0002_add_biometricreading` | Creates table with aX, aY, aZ, gX, gY, gZ + flex_1–5 |
| `0003_remove_flex_fields` | Drops flex_1, flex_2, flex_3, flex_4, flex_5 |
| **Final schema** | aX, aY, aZ, gX, gY, gZ only |

### Validation Rules

- `timestamp` is extracted from the MQTT payload (ISO 8601 string, converted to aware datetime).
- Sensor values (`aX`–`gZ`) must be numeric. Out-of-range values (e.g., `|aX| > 20`) are accepted with a logged WARNING — not rejected.
- Device-patient pairing is validated before any reading is stored.

---

## BiometricReading API Response Shape

```json
{
  "id": 42,
  "patient_id": 7,
  "timestamp": "2026-02-18T10:30:00Z",
  "aX": 0.12,
  "aY": -0.05,
  "aZ": 9.81,
  "gX": 1.23,
  "gY": -0.44,
  "gZ": 0.09
}
```

No magnetometer or flex fields appear in any API response.

---

## Relationship to Other Entities

- **Patient** (one-to-many): A patient can have many `BiometricReading` records.
- **BiometricSession** (independent): `BiometricReading` is a separate, independent model from `BiometricSession`. Sessions carry aggregated tremor data (JSONField); readings carry individual raw IMU samples.
- **ML Training Data** (separate domain): The raw `Dataset.csv` used for training contains mX/mY/mZ columns — these are handled by `ml_data/utils/data_loader.py` and are intentionally dropped before feature extraction. This is a separate data pipeline and is not related to `BiometricReading`.
