# Quickstart: Fix ML Pipeline Unit Mismatch

**Feature**: 041-fix-ml-pipeline | **Date**: 2026-04-16

## End-to-End Pipeline

Run these steps in order from the repository root:

### Step 1: Aggregate & Extract Features (US1)

```bash
py backend/ml_data/scripts/5_aggregate_and_extract.py
```

**Input**: `Data v2/Normal/*.xlsx` + `Data v2/Parkinson/*.xlsx`  
**Output**: `backend/ml_data/processed/X_features.npy`, `backend/ml_data/processed/y_labels.npy`

**Verify**:
- X_features.npy has shape `(N, 42)` where N > 0
- y_labels.npy has shape `(N,)` with values 0 and 1

### Step 2: Train Model (US2)

```bash
py backend/ml_models/scripts/train_random_forest.py
```

**Input**: `backend/ml_data/processed/X_features.npy`, `backend/ml_data/processed/y_labels.npy`  
**Output**: 
- `backend/ml_models/models/rf_model_v2.pkl`
- `backend/ml_models/models/rf_model_v2_scaler.pkl`  
- `backend/ml_models/models/rf_model_v2.json`

**Verify**:
- Accuracy > 80% on test set
- Metadata JSON has 42 feature names
- Scaler pkl loads successfully

### Step 3: Test Live Inference (US3)

```bash
py backend/live_glove_test.py --broker 192.168.137.1
```

**Requires**: MQTT broker running, ESP32 publishing sensor data  
**Verify**: After ~6.7s warm-up (200 samples @ 30Hz), predictions print for each incoming message

## Integration Scenarios

### Scenario A: Django API Inference

The `inference/services.py` `InferenceService.predict(model_name='rf', sensor_data=...)` will:
1. Load `rf_model_v2.pkl` + `rf_model_v2_scaler.pkl` (cached)
2. Receive a window of 200 sensor readings (200×6 array)
3. Extract 42 features using shared `extract_window_features()`
4. Scale features with loaded StandardScaler
5. Predict with RF model
6. Return prediction + severity

### Scenario B: Standalone MQTT Test

`live_glove_test.py` operates independently of Django:
1. Loads model + scaler directly from disk
2. Collects MQTT messages into 200-sample deque
3. On each new message (after warm-up): extract features → scale → predict → print

Both scenarios use the identical `extract_window_features()` function from `feature_extractors.py`.
