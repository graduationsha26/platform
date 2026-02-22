# Research: Update ML Prediction Endpoint (Feature 024)

**Branch**: `024-update-predict-endpoint` | **Date**: 2026-02-18
**Phase**: 0 — Research findings that resolve all technical unknowns before design

---

## Research Questions & Answers

### Q1: Where is the Django inference endpoint defined?

**Decision**: The ML prediction endpoint lives in `backend/inference/` Django app, registered as `POST /api/inference/`.

**Details**:
- **Views**: `backend/inference/views.py` — `InferenceAPIView.post()`
- **Serializers**: `backend/inference/serializers.py` — `InferenceRequestSerializer`
- **Validators**: `backend/inference/validators.py` — `validate_ml_input_shape()`, `validate_sensor_values()`
- **Services**: `backend/inference/services.py` — `PreprocessingService._preprocess_ml()`
- **URL registration**: `backend/tremoai_backend/urls.py` line 22: `path('api/inference/', include('inference.urls'))`

This is separate from `backend/apps/ml/predict.py` (the standalone `MLPredictor` class used by training scripts). The Django API uses its own `InferenceService`.

---

### Q2: Does the endpoint currently enforce a feature count for ML models?

**Decision**: No — the API layer does **not** enforce any feature count for ML model input.

**Details**:
- `InferenceRequestSerializer.validate_sensor_data()` validates:
  - The payload is a non-empty list ✓
  - For 1D input (ML path): all elements are `int` or `float` ✓
  - **Does NOT check length/count** — a 1D array of any length passes ✗
- `validate_ml_input_shape(expected_features=18)` exists in `validators.py` but is **never called from views.py** — only `validate_sensor_values()` is called (which checks NaN/Inf only)
- `PreprocessingService._preprocess_ml()` contains a comment about "18 engineered features" but does not validate the count
- The 18-feature count is documented in comments and docstrings but not enforced at the API boundary

**Gap**: If a caller submits 5, 7, or 18 features for an ML model, the request passes serializer validation, reaches `InferenceService.predict()`, and the scikit-learn model raises a `ValueError` (caught as 500 Internal Server Error). The caller gets no actionable error.

---

### Q3: What is the exact current serializer validation for ML input?

**Relevant code** (`backend/inference/serializers.py`, lines 20–56):

```python
def validate_sensor_data(self, value):
    if not isinstance(value, list):
        raise serializers.ValidationError("sensor_data must be a list")
    if len(value) == 0:
        raise serializers.ValidationError("sensor_data cannot be empty")

    first_element = value[0]

    if isinstance(first_element, list):
        # DL format: 2D array (128, 6)
        ...
    elif isinstance(first_element, (int, float)):
        # ML format: 1D array — validates types only, NOT count
        if not all(isinstance(x, (int, float)) for x in value):
            raise serializers.ValidationError(
                "For ML models, sensor_data must be a 1D array of numbers"
            )
    else:
        raise serializers.ValidationError(...)
```

**Finding**: The `elif isinstance(first_element, (int, float)):` branch needs a `len(value) != 6` count check added.

---

### Q4: What is `validate_ml_input_shape()` and is it used?

**Decision**: `validate_ml_input_shape()` exists in `validators.py` with `expected_features=18` default, but is never called from `views.py`.

**Details** (`backend/inference/validators.py`, lines 9–38):
- Function signature: `def validate_ml_input_shape(data: np.ndarray, expected_features: int = 18)`
- Comment on line 22: "ML models expect 1D array with 18 features (or 2D with shape (1, 18))"
- Not imported or called from `views.py` — dead code for validation purposes
- For Feature 024: change default `expected_features=18` → `expected_features=6`; update comment

---

### Q5: What does `PreprocessingService._preprocess_ml()` do with the feature count?

**Decision**: `_preprocess_ml()` does not validate feature count — it applies StandardScaler from metadata if present, then passes data through.

**Details** (`backend/inference/services.py`, lines 260–286):
- Docstring says: "Input features (should be 18 features)"
- Comment line 274: "For ML models, data should already be 18 engineered features"
- Functionally: converts to numpy, applies `(x - mean) / std` if `metadata['preprocessing']['scaler_params']` exists
- The retrained models (Features 022, 023) were trained on **raw** 6-axis data with **no normalization** — so the scaler block will be skipped (no scaler in metadata)
- Change needed: update docstring and comment from "18" → "6"

---

### Q6: What are all the places "18" appears in the inference code?

| File | Location | Content | Change Needed? |
|------|----------|---------|----------------|
| `serializers.py` | Line 11 (class docstring) | "18 features" | Yes — update to 6 |
| `serializers.py` | Line 16-17 (help_text) | "1D array (18) for ML" | Yes — update to 6 |
| `serializers.py` | Lines 24-26 (validate_sensor_data docstring) | "1D array with length 18" | Yes — update to 6 |
| `serializers.py` | Lines 45-50 (validate_sensor_data ML branch) | No count check | Yes — **add count check** (key functional change) |
| `validators.py` | Line 9 (function signature) | `expected_features: int = 18` | Yes — change to 6 |
| `validators.py` | Line 22 (comment) | "with 18 features" | Yes — update to 6 |
| `services.py` | Line 265 (docstring) | "should be 18 features" | Yes — update to 6 |
| `services.py` | Line 274 (comment) | "18 engineered features" | Yes — update to 6 |

**Key functional change**: `serializers.py` lines 45-50 (add `len(value) != 6` check).
**Documentation updates**: All other "18" occurrences in comments/docstrings.

---

### Q7: What error message should be returned when feature count is wrong?

**Decision**: Use the existing `serializers.ValidationError` pattern already in the file. Return HTTP 400 with error details.

**Error format** (from `views.py` lines 78-85):
```json
{
  "error": "Invalid input data",
  "error_code": "INVALID_INPUT_SHAPE",
  "details": {
    "sensor_data": ["ML models require exactly 6 features [aX, aY, aZ, gX, gY, gZ], got N"]
  }
}
```

This fits the existing error handling pattern and satisfies FR-006 (clear error format).

---

### Q8: Does the serializer need to know the model type (ML vs DL) to validate the feature count?

**Decision**: No — the 1D vs 2D detection in `validate_sensor_data()` already distinguishes ML from DL input without needing the `?model=` query param.

**Rationale**:
- DL input is always 2D (first element is a list) → `(128, 6)` validation applies
- ML input is always 1D (first element is a number) → `6` count check applies
- A request to use an SVM model with a 2D array will fail the DL-shape check, which is the correct behavior
- The `?model=` query parameter is only needed for routing (which model file to load), not for input shape detection

---

### Q9: What files change and what is the total scope?

**Total scope: 3 files, ~8 targeted line changes**

| File | Change Type | Lines Affected |
|------|------------|----------------|
| `backend/inference/serializers.py` | Functional + docs | Lines 11, 16-17, 24-26, 48-51 (add count check) |
| `backend/inference/validators.py` | Default param + comment | Lines 9, 22 |
| `backend/inference/services.py` | Comments only | Lines 265, 274 |

**Not changed**:
- `backend/inference/views.py` — no changes needed; existing error handling handles serializer failures
- `backend/inference/urls.py` — URL path unchanged
- `backend/apps/ml/predict.py` — already validates 6 features (modified in Feature 023)
- `backend/apps/ml/train.py` — unchanged
- Any models or migrations

---

## Summary

Feature 024 is a **3-file, documentation-plus-validation change**:

1. **`serializers.py`**: Add `len(value) != 6` count check in the ML branch of `validate_sensor_data()` — this is the **only functional change**. Update 3 docstrings.
2. **`validators.py`**: Change `expected_features=18` default to `expected_features=6`; update 1 comment.
3. **`services.py`**: Update 2 comments from "18 features" to "6 features".

The feature count check in `serializers.py` is the critical change: it turns a 500 Internal Server Error (from sklearn shape mismatch) into a clean 400 Bad Request with an actionable error message.
