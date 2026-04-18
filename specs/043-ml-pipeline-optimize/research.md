# Research: ML Pipeline Optimization & Confidence Scoring

**Feature**: 043-ml-pipeline-optimize  
**Date**: 2026-04-18  
**Branch**: `043-ml-pipeline-optimize`

---

## R-001: Feature Extraction Script & Current Window Parameters

**Decision**: Update `backend/ml_data/scripts/5_aggregate_and_extract.py` — change `WINDOW_SIZE = 200` → `100` and `STRIDE = 30` → `15`. All other pipeline parameters remain unchanged.

**Rationale**: This is the sole extraction script. It outputs fixed arrays `X_features.npy` and `y_labels.npy` to `backend/ml_data/processed/`. The feature extractor (`extract_window_features`) always produces a 42-feature vector regardless of window size (7 stats × 6 axes), so the downstream training script requires no structural changes. Only the parameter constants on lines 56–57 change.

**Alternatives considered**: Passing window/stride as CLI arguments — rejected because the script is used manually in a local dev workflow; hardcoded constants are the existing convention and match the training metadata.

---

## R-002: Model Training Script & Version Naming Convention

**Decision**: In `backend/ml_models/scripts/train_random_forest.py`, change `MODEL_VERSION = 2` → `3` on line 45. All output filenames auto-derive from this constant: `rf_model_v3.pkl`, `rf_model_v3_scaler.pkl`, `rf_model_v3.json`, `rf_model_metrics_v3.json`.

**Rationale**: The training script already uses a `MODEL_VERSION` constant that drives all output naming. A single-line change produces correctly-named v3 artifacts without touching any other logic. The metadata JSON written by the script includes `window_size` and `stride` fields from `pipeline_params`, so v3 metadata will self-document the new parameters after the extraction script is updated first.

**Alternatives considered**: Passing version as CLI arg — unnecessary complexity for a local dev workflow. Renaming post-hoc — error-prone.

---

## R-003: Window Size Alignment Across Scripts (Critical)

**Decision**: The live test script `backend/live_glove_test.py` has its own `WINDOW_SIZE = 200` constant (line 53). This MUST be changed to `100` when switching to the v3 model.

**Rationale**: The `extract_window_features()` function always produces 42 features regardless of window size, so there is no shape mismatch. However, the StandardScaler used by the v3 model was fitted on feature distributions derived from 100-sample windows. Feeding it features computed from 200-sample windows produces incorrectly normalized values, which will silently degrade classification accuracy. This is a non-obvious dependency: the feature count is the same but the feature value distributions differ.

**Alternatives considered**: Using a separate scaler for the live test — unnecessary; the correct fix is to use the same window size for live inference that was used during training.

---

## R-004: Inference Service Model Path Update

**Decision**: In `backend/inference/services.py`, update two dictionaries:
- `model_map` (line ~185): `'rf': settings.ML_MODELS_DIR / 'rf_model_v2.pkl'` → `'rf_model_v3.pkl'`
- `metadata_map` (line ~201): `'rf': settings.ML_MODELS_DIR / 'rf_model_v2.json'` → `'rf_model_v3.json'`

The scaler is not listed separately in the map — it is loaded dynamically from `metadata['scaler_file']`, which is written into the JSON by the training script. Updating the JSON path is sufficient; the scaler reference follows automatically.

**Rationale**: The `ModelCache` singleton loads the scaler path from the model's metadata JSON (`metadata['scaler_file']`). As long as the v3 JSON correctly references `rf_model_v3_scaler.pkl` (which the training script generates), no scaler path requires explicit change in `services.py`.

**Alternatives considered**: Storing model path in `.env` — over-engineering for a local dev context. No change needed.

---

## R-005: Confidence Scoring — predict_proba() vs predict()

**Decision**: Replace `model.predict(feature_scaled)[0]` with `model.predict_proba(feature_scaled)[0]` in `backend/live_glove_test.py`. The predicted class is `argmax(probs)`. Confidence is `max(probs) * 100`, formatted to one decimal place.

**Rationale**: `RandomForestClassifier` supports `predict_proba()` natively. The return shape is `(1, n_classes)` — for binary classification, `probs[1]` is P(TREMOR), `probs[0]` is P(NORMAL). `argmax` selects the dominant class, equivalent to `predict()` but exposing the margin.

**Alternatives considered**: Decision function / calibrated probabilities — unnecessary; Random Forest probabilities are well-calibrated for binary classification and require no post-processing. Logistic calibration — out of scope.

---

## R-006: Output Format Implementation

**Decision**: The live test terminal output format is exactly:

```
[HH:MM:SS.mmm] ✅ NORMAL (0) | Confidence: XX.X%
[HH:MM:SS.mmm] ⚠️ TREMOR (1) | Confidence: XX.X%
```

Implementation: Use `datetime.now().strftime('%H:%M:%S.') + f'{datetime.now().microsecond // 1000:03d}'` for millisecond timestamp, or `datetime.now().strftime('%H:%M:%S.%f')[:12]` (truncates microseconds to 3 digits).

**Rationale**: The existing script already computes a timestamp `ts` (line ~196). Only the format string changes. The emoji and label map directly to the argmax class index.

**Alternatives considered**: Using `time.strftime` — lacks millisecond precision. Logging module — heavier than needed for a standalone test script.

---

## R-007: Constitutional Conflict — Model Git Tracking

**Decision**: Accept user-justified deviation from the constitutional rule "Models are excluded from git via `.gitignore`". The `.gitignore` rules excluding `.pkl`, `.h5`, and `backend/ml_models/models/` have been commented out (see `.gitignore` diff).

**Rationale**: User explicitly requires model artifacts to be committed so they can be shared across team members and deployed without requiring a local retraining step. This is a valid graduation-project need. The deviation is documented, justified, and scoped to model artifact files only — all other `.gitignore` rules remain intact. This is not a tech-stack change.

**Alternatives considered**: Git LFS — would require additional tooling and registration; out of scope for local dev graduation project. Keeping models out of git — rejected by user requirement.

---

## R-008: Scope of Changes (Files Modified)

| File | Change |
|------|--------|
| `backend/ml_data/scripts/5_aggregate_and_extract.py` | `WINDOW_SIZE=200→100`, `STRIDE=30→15` |
| `backend/ml_models/scripts/train_random_forest.py` | `MODEL_VERSION=2→3` |
| `backend/inference/services.py` | `model_map['rf']` and `metadata_map['rf']` → v3 paths |
| `backend/live_glove_test.py` | `WINDOW_SIZE=200→100`, v3 model/scaler paths, `predict()→predict_proba()`, formatted output |
| `.gitignore` | Comment out `.pkl`, `.h5`, `ml_models/models/` ignore rules |

**Scripts to re-run** (not file edits, but execution steps):
1. `python backend/ml_data/scripts/5_aggregate_and_extract.py` — regenerates `X_features.npy`, `y_labels.npy`
2. `python backend/ml_models/scripts/train_random_forest.py` — produces `rf_model_v3.pkl`, `rf_model_v3_scaler.pkl`, `rf_model_v3.json`

**Zero changes to**: Django REST API, WebSocket consumers, MQTT handlers, frontend, firmware, database schema.
