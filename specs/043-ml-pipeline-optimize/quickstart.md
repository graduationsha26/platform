# Quickstart: ML Pipeline Optimization & Confidence Scoring

**Feature**: 043-ml-pipeline-optimize  
**Date**: 2026-04-18

---

## Prerequisites

- Python virtual environment activated (`venv/` or `.venv/`)
- Working directory: `C:/Data from HDD/Graduation Project/Platform/`
- Raw training data available in `backend/ml_data/` (Excel files in `Data v2/Normal/` and `Data v2/Parkinson/`)
- No hardware required for US1 (pipeline offline); ESP32 glove required for full US2 live test

---

## Scenario 1: Verify Feature Extraction Produces Smaller Output (US1)

After updating `5_aggregate_and_extract.py` to Window=100, Stride=15:

```bash
# Run from repo root
python backend/ml_data/scripts/5_aggregate_and_extract.py

# Verify output size is smaller than v2 (Window=200 produced more rows)
python -c "
import numpy as np
X = np.load('backend/ml_data/processed/X_features.npy')
print(f'X_features shape: {X.shape}')
# Shape should be (N, 42) where N is roughly half of v2's N
# v2 example: (3420, 42) → v3 expect: ~(6840, 42) or similar
# (Stride=15 is smaller than Stride=30, so more windows; Window=100 < 200 so more fit)
"
```

**Expected**: Shape `(N, 42)` printed without error. N will differ from v2 due to changed stride.

---

## Scenario 2: Train v3 Model (US1)

After feature extraction completes:

```bash
python backend/ml_models/scripts/train_random_forest.py

# Verify artifacts were saved
ls backend/ml_models/models/rf_model_v3*
# Expected output:
#   rf_model_v3.pkl
#   rf_model_v3_scaler.pkl
#   rf_model_v3.json
#   rf_model_metrics_v3.json
```

Confirm metadata contains correct window parameters:
```bash
python -c "
import json
with open('backend/ml_models/models/rf_model_v3.json') as f:
    meta = json.load(f)
pp = meta['pipeline_params']
print('window_size:', pp['window_size'])   # expect: 100
print('stride:', pp['stride'])             # expect: 15
print('scaler_file:', meta['scaler_file']) # expect: rf_model_v3_scaler.pkl
print('accuracy:', meta.get('accuracy', meta.get('test_accuracy')))
"
```

---

## Scenario 3: Verify Inference Service Loads v3 (US1)

After updating `inference/services.py` model paths to v3:

```bash
cd backend
python manage.py shell -c "
from inference.services import ModelCache
cache = ModelCache()
model, meta, scaler = cache.get_model('rf')
print('Model loaded:', type(model).__name__)
print('Window size from meta:', meta['pipeline_params']['window_size'])  # expect: 100
print('Scaler loaded:', scaler is not None)
"
```

**Expected**: Prints `RandomForestClassifier`, `100`, `True` — no FileNotFoundError.

---

## Scenario 4: Live Test with Confidence Scoring (US2)

Run against the hardware glove or use a recorded MQTT replay:

```bash
python backend/live_glove_test.py
# Expected output (one line per prediction):
# [17:57:19.659] ✅ NORMAL (0) | Confidence: 95.5%
# [17:57:20.123] ⚠️ TREMOR (1) | Confidence: 88.2%
# [17:57:20.623] ✅ NORMAL (0) | Confidence: 72.1%
```

**Verify format compliance**:
- Timestamp is `[HH:MM:SS.mmm]` (brackets, milliseconds)
- State line matches exactly: emoji, space, STATE_LABEL, space, `(N)`, space, `|`, space, `Confidence:`, space, `XX.X%`
- No prediction line missing a confidence value
- NORMAL lines always use ✅; TREMOR lines always use ⚠️

---

## Scenario 5: Commit v3 Artifacts to Git (FR-009)

After successful training and verification:

```bash
git status backend/ml_models/models/
# Should show rf_model_v3.pkl, rf_model_v3_scaler.pkl, rf_model_v3.json as untracked

git add backend/ml_models/models/rf_model_v3.pkl \
        backend/ml_models/models/rf_model_v3_scaler.pkl \
        backend/ml_models/models/rf_model_v3.json \
        backend/ml_models/models/rf_model_metrics_v3.json

git status
# Should show 4 files staged — not ignored
```

**If files still show as ignored**: Verify `.gitignore` rules for `backend/ml_models/models/*.pkl` and `*.json` are commented out.

---

## Fault Indicators

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `FileNotFoundError: rf_model_v3.pkl` | Training not yet run | Run `train_random_forest.py` first |
| `ValueError: X has N features, expected M` | Live test WINDOW_SIZE still 200 | Update `WINDOW_SIZE = 100` in `live_glove_test.py` |
| Output line missing `Confidence:` | `predict()` not changed to `predict_proba()` | Update live test script |
| `AttributeError: predict_proba` | Model loaded without `predict_proba` support | Confirm model is Random Forest (not SVM with default settings) |
| Model files still gitignored | `.gitignore` rules still active | Confirm `.pkl`/`.json` lines are commented out |
