# Quickstart: Update ML Prediction Endpoint (Feature 024)

**Branch**: `024-update-predict-endpoint` | **Date**: 2026-02-18
**Purpose**: Verification scenarios for manual testing after implementation

---

## Prerequisites

Before running these scenarios:
1. Django dev server is running: `python manage.py runserver` (from `backend/`)
2. An authenticated user token is available (JWT from `/api/auth/login/`)
3. `rf_model.pkl` and `svm_model.pkl` are present (from Features 022 and 023)

Set TOKEN in shell: `TOKEN="your-jwt-access-token"`

---

## Scenario 1 — Valid 6-Feature ML Request Returns Prediction (US1)

**Goal**: Confirm a 6-element ML request succeeds with both RF and SVM models.

```bash
# RF model (default)
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}' \
  -s | python -m json.tool
```

**Expected**: HTTP 200, response contains `prediction` (true/false), `severity` (0-3), `model_used` ("rf"), `inference_time_ms` < 70.

```bash
# SVM model
curl -X POST "http://localhost:8000/api/inference/?model=svm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}'
```

**Expected**: HTTP 200, `model_used` is "svm", valid prediction returned.

---

## Scenario 2 — Too Few Features Rejected with Clear Error (US2)

**Goal**: Confirm a 5-element array returns HTTP 400 with a clear "requires exactly 6" message.

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02]}' \
  -s | python -m json.tool
```

**Expected**:
```json
{
  "error": "Invalid input data",
  "error_code": "INVALID_INPUT_SHAPE",
  "details": {
    "sensor_data": ["ML models require exactly 6 features [aX, aY, aZ, gX, gY, gZ], got 5"]
  }
}
```
Status: HTTP 400 (not 500).

---

## Scenario 3 — Too Many Features Rejected with Clear Error (US2)

**Goal**: Confirm an 18-element array (old ML format) returns HTTP 400 — not 500.

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8]}' \
  -s | python -m json.tool
```

**Expected**: HTTP 400 with `"error_code": "INVALID_INPUT_SHAPE"` and message mentioning "got 18". NOT HTTP 500.

---

## Scenario 4 — Non-Numeric Values Rejected (US2)

**Goal**: Confirm string values return a clear error.

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, "bad", 0.05, -0.02, 0.01]}'
```

**Expected**: HTTP 400 with message about non-numeric values.

---

## Scenario 5 — Empty Array Rejected (US2)

**Goal**: Confirm empty `sensor_data` returns a clear error.

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": []}'
```

**Expected**: HTTP 400, `"sensor_data cannot be empty"` in details.

---

## Scenario 6 — Edge Case: All Zeros Accepted (US1)

**Goal**: Confirm degenerate valid input (all zeros) still returns a prediction.

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
```

**Expected**: HTTP 200 with a valid prediction. All-zero input is valid per FR-001.

---

## Scenario 7 — DL Model Input Unchanged (Backward Compatibility)

**Goal**: Confirm DL model (LSTM/CNN) requests still accept 2D arrays (not affected by feature count change).

```bash
# Simplified test — first 3 rows of a 128-row sequence
# In practice, use a real 128×6 array
python3 -c "
import json, random
data = [[random.uniform(-1,1) for _ in range(6)] for _ in range(128)]
print(json.dumps({'sensor_data': data}))
" > /tmp/dl_payload.json

curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/dl_payload.json
```

**Expected**: Either HTTP 200 (if LSTM model is available) or HTTP 400 ModelNotFoundError (if not loaded) — either way, NOT a shape validation error.

---

## Scenario 8 — Invalid Model Name Rejected (Pre-existing, Verification)

**Goal**: Confirm invalid model names still return a clear error.

```bash
curl -X POST "http://localhost:8000/api/inference/?model=xgboost" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}'
```

**Expected**: HTTP 400, `"error_code": "MODEL_NOT_FOUND"`, `available_models` list shown.

---

## Python Verification Script

```python
"""
Feature 024 verification — run from backend/ directory:
    python verify_feature024.py
"""

import requests
import sys

BASE_URL = "http://localhost:8000"
TOKEN = "YOUR_JWT_TOKEN_HERE"  # Replace with actual token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def test(name, expected_status, payload, params=None):
    """Run a single test."""
    resp = requests.post(
        f"{BASE_URL}/api/inference/",
        json=payload,
        headers=headers,
        params=params
    )
    ok = resp.status_code == expected_status
    print(f"{'[OK]' if ok else '[FAIL]'} {name} — got {resp.status_code}, expected {expected_status}")
    if not ok:
        print(f"       Response: {resp.json()}")
    return ok


results = []

# US1: Valid 6-feature requests
results.append(test("Valid 6-feature RF request", 200,
    {"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}))
results.append(test("Valid 6-feature SVM request", 200,
    {"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}, params={"model": "svm"}))
results.append(test("All-zeros (degenerate valid) request", 200,
    {"sensor_data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}))

# US2: Invalid input rejected
results.append(test("5 features → 400", 400,
    {"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02]}))
results.append(test("7 features → 400", 400,
    {"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01, 0.99]}))
results.append(test("18 features → 400 (not 500)", 400,
    {"sensor_data": list(range(18))}))
results.append(test("Empty array → 400", 400,
    {"sensor_data": []}))

# Summary
passed = sum(results)
total = len(results)
print(f"\n{'='*50}")
print(f"Result: {passed}/{total} tests passed")
sys.exit(0 if passed == total else 1)
```
