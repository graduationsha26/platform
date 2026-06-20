# Quickstart: MQTT Parser and Normalization 6-Axis Cleanup (Feature 021)

**Branch**: `021-6axis-params-cleanup` | **Date**: 2026-02-18

This guide shows how to verify E-3.3 (MQTT parser) and E-3.4 (params.json) are correctly implemented.

---

## Prerequisites

- Backend running: `python manage.py runserver`
- Migrations applied: `python manage.py migrate`

---

## Scenario 1: Verify MQTT Parser Ignores mX/mY/mZ (E-3.3)

Send a simulated MQTT reading message that includes all 9 sensor fields (the 6 active + 3 disabled magnetometer fields).

**Simulate inbound MQTT message** (using Python or MQTT client tool):

```python
payload = {
    "serial_number": "DEVICEABC123",
    "timestamp": "2026-02-18T10:30:05Z",
    "aX": 0.12,
    "aY": -0.05,
    "aZ": 9.81,
    "gX": 1.23,
    "gY": -0.44,
    "gZ": 0.09,
    "mX": -1,       # Magnetometer X — should be silently ignored
    "mY": -1,       # Magnetometer Y — should be silently ignored
    "mZ": -1        # Magnetometer Z — should be silently ignored
}
```

**Expected behaviour**:
1. The validator accepts the message (mX/mY/mZ are unknown fields, not rejected)
2. A `BiometricReading` record is created with exactly `aX=0.12, aY=-0.05, aZ=9.81, gX=1.23, gY=-0.44, gZ=0.09`
3. No mX, mY, or mZ values appear anywhere in the stored record

**Verify via Django shell**:

```bash
python manage.py shell
```

```python
from realtime.validators import validate_biometric_reading_message

# Payload with magnetometer fields included
payload = {
    "serial_number": "DEVICEABC123",
    "timestamp": "2026-02-18T10:30:05Z",
    "aX": 0.12, "aY": -0.05, "aZ": 9.81,
    "gX": 1.23, "gY": -0.44, "gZ": 0.09,
    "mX": -1, "mY": -1, "mZ": -1,
}

# Should pass without raising ValidationError
validate_biometric_reading_message(payload)
print("✓ Validation passed — mX/mY/mZ silently ignored")
```

---

## Scenario 2: Verify params.json Has 6-Axis-Only Entries (E-3.4)

Inspect the normalization configuration file directly:

```bash
python manage.py shell
```

```python
import json

with open("ml_data/params.json") as f:
    params = json.load(f)

feature_names = [f["name"] for f in params["features"]]
print(f"Feature count: {len(feature_names)}")
print(f"Feature names: {feature_names}")

assert len(feature_names) == 6, "Expected exactly 6 features"
assert feature_names == ["aX", "aY", "aZ", "gX", "gY", "gZ"], "Wrong feature names"
assert "mX" not in feature_names, "mX should not be in params.json"
assert "mY" not in feature_names, "mY should not be in params.json"
assert "mZ" not in feature_names, "mZ should not be in params.json"
print("✓ params.json has exactly 6 axis entries, no magnetometer fields")
```

---

## Scenario 3: Verify Normalization Pipeline Accepts 6-Axis Input

```bash
python manage.py shell
```

```python
import numpy as np
from apps.ml.normalize import load_params, normalize_features

# Load params
params = load_params("ml_data/params.json")
print(f"✓ Loaded {len(params['features'])} normalization entries")

# Normalize a 6-axis reading
raw = np.array([0.12, -0.05, 9.81, 1.23, -0.44, 0.09])
normalized = normalize_features(raw, params)
print(f"✓ Normalized successfully: {normalized}")

# Confirm shape
assert normalized.shape == (6,), "Expected shape (6,)"
print("✓ Normalization pipeline uses exactly 6 features — no magnetometer data")
```

---

## Scenario 4: Verify params.json Generator Produces 6-Axis Output

```bash
cd backend
python apps/ml/generate_params.py --dataset Dataset.csv --output ml_data/params_test.json
python apps/ml/generate_params.py --verify --output ml_data/params_test.json
```

**Expected output**:
```
Generating normalization parameters...
  Dataset: Dataset.csv
  Output: ml_data/params_test.json
...
✓ Generated ml_data/params_test.json with 6 features
✓ Validation successful
```

Inspect the generated file — it should have exactly 6 entries (aX, aY, aZ, gX, gY, gZ) with no mX, mY, mZ, or flex entries.

---

## Scenario 5: Verify Legacy mX/mY/mZ Payload from Older Firmware

Some older firmware versions may still transmit mX, mY, mZ alongside the 6 active axes.
These messages must be accepted gracefully:

```python
from realtime.validators import validate_biometric_reading_message
from django.core.exceptions import ValidationError

legacy_payload = {
    "serial_number": "LEGACYDEVICE01",
    "timestamp": "2026-02-18T10:30:00Z",
    "aX": 100.5, "aY": 200.1, "aZ": 9810.0,
    "gX": 50.0, "gY": -25.3, "gZ": 12.1,
    "mX": -1, "mY": -1, "mZ": -1,    # Legacy firmware extras
}

try:
    validate_biometric_reading_message(legacy_payload)
    print("✓ Legacy 9-field payload accepted — mX/mY/mZ silently ignored")
except ValidationError as e:
    print(f"✗ Unexpected rejection: {e}")
```
