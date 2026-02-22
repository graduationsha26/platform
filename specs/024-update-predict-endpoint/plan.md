# Implementation Plan: Update ML Prediction Endpoint

**Branch**: `024-update-predict-endpoint` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-update-predict-endpoint/spec.md`

---

## Summary

Feature 024 updates the Django ML inference endpoint (`POST /api/inference/`) to enforce exactly 6 sensor features for ML model (RF, SVM) input, replacing the previously unenforced 18-feature assumption. The core change is adding a 6-element count check in `InferenceRequestSerializer.validate_sensor_data()`. Without this check, callers submitting wrong feature counts received a cryptic HTTP 500 from scikit-learn; after this change they receive a clear HTTP 400 with an actionable error message. Secondary changes update inline comments and the `validate_ml_input_shape()` default in validators.py to be consistent with the new 6-feature schema.

**Total code changes**: 3 files, ~8 line changes. No migrations, no new models, no new dependencies.

This is the API layer companion to Features 022 (RF retrained for 6 axes) and 023 (SVM retrained for 6 axes) — completing the E-4.x series.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data (paho-mqtt)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) — models served via Django
**Performance Goals**: ML inference latency <70ms (unchanged from Feature 008)
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: ~10 doctors, ~100 patients

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Changes in `backend/inference/` — within the monorepo `backend/` directory
- [x] **Tech Stack Immutability**: DRF serializers, validators, service comments — no new libraries
- [x] **Database Strategy**: No database changes; `InferenceLog` model untouched
- [x] **Authentication**: Feature does not affect auth; existing `IsAuthenticated` permission unchanged
- [x] **Security-First**: No secrets or credentials involved; no hardcoded values
- [x] **Real-time Requirements**: Feature does not affect real-time pipeline
- [x] **MQTT Integration**: Feature does not affect MQTT subscription
- [x] **AI Model Serving**: Models remain served via Django backend; prediction flow unchanged
- [x] **API Standards**: REST + JSON; HTTP 400 for validation errors; snake_case; error format `{"error": "..."}` preserved
- [x] **Development Scope**: Local development only; no Docker/CI/CD

**Result**: ✅ PASS — no constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/024-update-predict-endpoint/
├── plan.md                                     # This file
├── research.md                                 # Phase 0 output
├── data-model.md                               # Phase 1 output
├── quickstart.md                               # Phase 1 output
├── contracts/
│   └── inference-api-schema.yaml              # Phase 1 output
└── tasks.md                                    # Phase 2 output (not created by /speckit.plan)
```

### Source Code (files touched by this feature)

```text
backend/
├── inference/
│   ├── serializers.py          # [MODIFY] 4 changes:
│   │                           #   (1) class docstring: "18 features" → "6 features"
│   │                           #   (2) sensor_data help_text: "1D array (18)" → "1D array (6) [aX, aY, aZ, gX, gY, gZ]"
│   │                           #   (3) validate_sensor_data docstring: "length 18" → "length 6"
│   │                           #   (4) ML branch: add len(value) != 6 count check (key functional change)
│   ├── validators.py           # [MODIFY] 2 changes:
│   │                           #   (1) validate_ml_input_shape default: expected_features=18 → 6
│   │                           #   (2) inline comment: "18 features" → "6 features [aX, aY, aZ, gX, gY, gZ]"
│   └── services.py             # [MODIFY] 2 changes (comments only):
│                               #   (1) _preprocess_ml docstring: "18 features" → "6 features [aX, aY, aZ, gX, gY, gZ]"
│                               #   (2) inline comment: "18 engineered features" → "6 raw sensor features [aX, aY, aZ, gX, gY, gZ]"
```

**Files explicitly NOT touched**:
- `backend/inference/views.py` — no logic changes; existing serializer error handling already surfaces validation errors correctly
- `backend/inference/urls.py` — endpoint path unchanged
- `backend/inference/models.py` — `InferenceLog` unchanged
- `backend/inference/exceptions.py` — exception classes unchanged
- `backend/apps/ml/predict.py` — already validates 6 features (Feature 023)
- `backend/apps/ml/train.py` — unchanged
- All Django migrations — no schema changes
- All frontend code — no frontend changes

---

## Phase 0: Research Findings

See [research.md](research.md) for full details. Summary:

| Question | Answer |
|---|---|
| Where is the inference endpoint? | `backend/inference/` Django app, `POST /api/inference/` |
| Does the endpoint enforce 18 features? | No — serializer validates types but NOT count |
| Is `validate_ml_input_shape()` called from views? | No — it exists but is dead code (never called) |
| What is the minimal functional change? | Add `len(value) != 6` check in `serializers.py` ML branch |
| What error format does wrong count produce? | HTTP 400 with `error_code: INVALID_INPUT_SHAPE`, details in `sensor_data` key |
| Does changing the serializer need view changes? | No — views already surface serializer errors as HTTP 400 |
| How many "18" occurrences need updating? | 8 total across 3 files |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full details. No new database entities.

**Key schema change**: ML `sensor_data` request now enforces exactly 6 elements (was unenforced, documented as 18). DL request format unchanged.

**Validation flow**: Request → `InferenceRequestSerializer.validate_sensor_data()` [NEW: 6-count check] → `validate_sensor_values()` [unchanged] → `InferenceService.predict()` [unchanged].

### Schemas / Contracts

See [contracts/inference-api-schema.yaml](contracts/inference-api-schema.yaml).

Documents:
- Updated request schema: ML models require `sensor_data` with exactly 6 elements
- Error response for wrong count: HTTP 400, `INVALID_INPUT_SHAPE`, with count in message
- All pre-existing error responses preserved (empty, non-numeric, NaN/Inf, invalid model)
- DL request format, response schema, and error codes unchanged

### Integration Scenarios

See [quickstart.md](quickstart.md) for 8 verification scenarios:
1. Valid 6-feature RF request → HTTP 200 with prediction
2. Valid 6-feature SVM request → HTTP 200 with prediction
3. 5 features → HTTP 400 (not 500)
4. 18 features (old format) → HTTP 400 (not 500)
5. Non-numeric values → HTTP 400
6. Empty array → HTTP 400
7. All-zeros input → HTTP 200 (degenerate but valid)
8. DL model request → unaffected by ML count change

---

## Implementation Tasks

Feature 024 has exactly **3 code edits** (one functional, two documentation-only).

### Task 1: Add 6-feature count check in `backend/inference/serializers.py`

**Change location**: `validate_sensor_data()` method, ML branch (after line 50):

```python
# Old (lines 45-50):
elif isinstance(first_element, (int, float)):
    # ML format: 1D array
    if not all(isinstance(x, (int, float)) for x in value):
        raise serializers.ValidationError(
            "For ML models, sensor_data must be a 1D array of numbers"
        )

# New:
elif isinstance(first_element, (int, float)):
    # ML format: 1D array with exactly 6 features [aX, aY, aZ, gX, gY, gZ]
    if not all(isinstance(x, (int, float)) for x in value):
        raise serializers.ValidationError(
            "For ML models, sensor_data must be a 1D array of numbers"
        )
    if len(value) != 6:
        raise serializers.ValidationError(
            f"ML models require exactly 6 features [aX, aY, aZ, gX, gY, gZ], "
            f"got {len(value)}"
        )
```

**Also update** in the same file:
- Line 11: Class docstring `"18 features"` → `"6 features"`
- Lines 16-17: `help_text` `"1D array (18) for ML"` → `"1D array (6) for ML — [aX, aY, aZ, gX, gY, gZ]"`
- Lines 24-26: Docstring `"1D array with length 18"` → `"1D array with length 6"`

### Task 2: Update `validate_ml_input_shape()` default in `backend/inference/validators.py`

```python
# Old (line 9):
def validate_ml_input_shape(data: np.ndarray, expected_features: int = 18):

# New:
def validate_ml_input_shape(data: np.ndarray, expected_features: int = 6):
```

**Also update** line 22 comment:
```python
# Old: # ML models expect 1D array with 18 features (or 2D with shape (1, 18))
# New: # ML models expect 1D array with 6 features [aX, aY, aZ, gX, gY, gZ] (or 2D with shape (1, 6))
```

### Task 3: Update comments in `backend/inference/services.py`

**Line 265 docstring**:
```python
# Old: Args: data: Input features (should be 18 features)
# New: Args: data: Input features (6 raw sensor features [aX, aY, aZ, gX, gY, gZ])
```

**Line 274 comment**:
```python
# Old: # For ML models, data should already be 18 engineered features
# New: # For ML models, data should be 6 raw sensor features [aX, aY, aZ, gX, gY, gZ]
```

### Task 4: Verify US1 — Valid 6-feature prediction returns HTTP 200

Run Scenarios 1 and 6 from quickstart.md. Confirm RF and SVM models accept valid 6-feature input.

### Task 5: Verify US2 — Invalid feature count returns HTTP 400

Run Scenarios 2, 3, 4, 5 from quickstart.md. Confirm 5-element, 18-element, non-numeric, and empty requests all return HTTP 400 (not 500).

---

## Complexity Tracking

No constitution violations. No new complexity added.

---

## Notes

- **Only 1 functional line added**: `if len(value) != 6: raise serializers.ValidationError(...)` — everything else is documentation
- **No scikit-learn version dependency**: The 6-feature check happens at the Django API layer before the model is even called
- **Backward compatibility note**: ML callers sending 18 features will now get HTTP 400 instead of HTTP 500 — this is a fix, not a breaking change
- **DL models unaffected**: 2D array detection remains unchanged; CNN/LSTM paths proceed as before
- **Companion to Features 022 + 023**: Together, 022 + 023 + 024 complete the 6-axis ML pipeline alignment
