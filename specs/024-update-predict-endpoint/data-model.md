# Data Model: Update ML Prediction Endpoint (Feature 024)

**Branch**: `024-update-predict-endpoint` | **Date**: 2026-02-18
**Feature**: Update ML inference endpoint to accept exactly 6-feature input

---

## Overview

Feature 024 adds no new database entities, no new models, and no schema migrations. All changes are confined to the API input validation layer and inline documentation. The existing `InferenceLog` model is unchanged.

---

## Entities (Unchanged)

### InferenceLog (pre-existing, not modified)

Stores a record of each inference request. Schema unchanged by Feature 024.

| Field | Type | Description |
|-------|------|-------------|
| `user` | FK → CustomUser | Authenticated user who made the request |
| `model_used` | CharField | Model identifier: rf, svm, lstm, cnn_1d |
| `prediction` | BooleanField | Tremor detected (true/false) |
| `severity` | IntegerField | Severity level 0–3 |
| `confidence_score` | FloatField (nullable) | Model confidence 0.0–1.0 |
| `inference_time_ms` | IntegerField (nullable) | Milliseconds for inference |
| `input_shape` | CharField | Shape of input array as string |
| `timestamp` | DateTimeField | Auto-set at creation (auto_now_add) |

---

## Input Schema (Before → After)

This is the key change — no database schema, but the API request body schema is updated.

### Prediction Request Schema

**Before** (Feature 008, undocumented/unenforced):
```json
{
  "sensor_data": [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18]
}
```
- 1D array, 18 elements (documented in comments, not enforced)
- Invalid feature count → 500 Internal Server Error (cryptic sklearn error)

**After** (Feature 024, enforced):
```json
{
  "sensor_data": [aX, aY, aZ, gX, gY, gZ]
}
```
- 1D array, exactly 6 elements: `[aX, aY, aZ, gX, gY, gZ]`
- Invalid feature count → 400 Bad Request with clear error

### DL Input Schema (Unchanged)

```json
{
  "sensor_data": [[aX1,aY1,aZ1,gX1,gY1,gZ1], ..., [aX128,aY128,aZ128,gX128,gY128,gZ128]]
}
```
- 2D array (128, 6) — not affected by Feature 024

---

## Validation Rules (Updated)

### ML Input Validation Flow (after Feature 024)

```
Request arrives at InferenceAPIView.post()
    │
    ▼
InferenceRequestSerializer.validate_sensor_data()
    ├── Is value a non-empty list?          → else → 400 "sensor_data cannot be empty"
    ├── Is first_element a list?            → DL path (unchanged)
    ├── Is first_element a number?          → ML path
    │       ├── All elements numeric?       → else → 400 "must be a 1D array of numbers"
    │       └── len(value) == 6?            → else → 400 "requires exactly 6 features [aX, aY, aZ, gX, gY, gZ]"
    └── (Other)                             → 400 "must contain numbers or nested lists"
    │
    ▼ (pass)
validate_sensor_values()                    → checks NaN/Inf/extreme range (unchanged)
    │
    ▼ (pass)
InferenceService.predict()                  → model inference (unchanged)
```

### Feature Count Validation Rule

| Condition | Response |
|-----------|----------|
| `len(sensor_data) == 6` and all numeric | Pass — proceed to inference |
| `len(sensor_data) < 6` | HTTP 400 — "requires exactly 6 features, got N" |
| `len(sensor_data) > 6` | HTTP 400 — "requires exactly 6 features, got N" |
| Any element is non-numeric | HTTP 400 — "must be a 1D array of numbers" |
| Any element is NaN or Inf | HTTP 400 — "invalid sensor values: NaN/Inf detected" |
| First element is a list (DL format) | Proceeds as DL (128×6 shape validation unchanged) |

---

## Feature Axis Schema

The 6 required features, in order:

| Index | Name | Description | Typical Range |
|-------|------|-------------|---------------|
| 0 | `aX` | Accelerometer X-axis | –10 to +10 m/s² |
| 1 | `aY` | Accelerometer Y-axis | –10 to +10 m/s² |
| 2 | `aZ` | Accelerometer Z-axis | –10 to +10 m/s² |
| 3 | `gX` | Gyroscope X-axis | –10 to +10 rad/s |
| 4 | `gY` | Gyroscope Y-axis | –10 to +10 rad/s |
| 5 | `gZ` | Gyroscope Z-axis | –10 to +10 rad/s |

Note: Values outside –50 to +50 are rejected by `validate_sensor_values()` (pre-existing, unchanged).

---

## Prediction Response Schema (Unchanged)

The response schema is not modified by Feature 024.

```json
{
  "prediction": true,
  "severity": 2,
  "model_used": "rf",
  "timestamp": "2026-02-18T12:00:00.000Z",
  "confidence_score": 0.78,
  "inference_time_ms": 45,
  "model_version": "rf_v1_2026-02-18",
  "input_validation": {
    "data_quality": "good",
    "missing_values": false,
    "out_of_range_values": false
  }
}
```

---

## Code Change Entities

These are the code-level "entities" affected — not database models, but the validation contracts within each file.

### InferenceRequestSerializer (serializers.py)

- **Updated**: Class docstring ("18 features" → "6 features")
- **Updated**: `sensor_data` field `help_text` ("1D array (18) for ML" → "1D array (6) for ML — [aX, aY, aZ, gX, gY, gZ]")
- **Updated**: `validate_sensor_data` docstring ("length 18" → "length 6")
- **Added**: Count check in ML branch: `if len(value) != 6: raise ValidationError(...)`

### validate_ml_input_shape (validators.py)

- **Updated**: Default parameter `expected_features: int = 18` → `expected_features: int = 6`
- **Updated**: Inline comment ("18 features" → "6 features [aX, aY, aZ, gX, gY, gZ]")

### PreprocessingService._preprocess_ml (services.py)

- **Updated**: Docstring ("should be 18 features" → "6 features [aX, aY, aZ, gX, gY, gZ]")
- **Updated**: Inline comment ("18 engineered features" → "6 raw sensor features [aX, aY, aZ, gX, gY, gZ]")
