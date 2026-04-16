# Data Model: Fix ML Pipeline Unit Mismatch

**Feature**: 041-fix-ml-pipeline | **Date**: 2026-04-16

> This feature has no Django database models. All data is file-based (numpy arrays, pickle files, JSON metadata). This document defines the schemas of those file-based artifacts.

## Artifact Schemas

### A1: Feature Matrix (`X_features.npy`)

**Location**: `backend/ml_data/processed/X_features.npy`  
**Format**: NumPy `.npy` (float64)  
**Shape**: `(N_windows, 42)` where N_windows depends on total data across all Excel files

**Column order** (42 features, axis-major):

| Index | Feature Name        | Index | Feature Name        |
|-------|---------------------|-------|---------------------|
| 0     | mean_aX             | 21    | mean_gX             |
| 1     | std_aX              | 22    | std_gX              |
| 2     | max_aX              | 23    | max_gX              |
| 3     | min_aX              | 24    | min_gX              |
| 4     | rms_aX              | 25    | rms_gX              |
| 5     | median_aX           | 26    | median_gX           |
| 6     | dominant_freq_aX    | 27    | dominant_freq_gX    |
| 7     | mean_aY             | 28    | mean_gY             |
| 8     | std_aY              | 29    | std_gY              |
| 9     | max_aY              | 30    | max_gY              |
| 10    | min_aY              | 31    | min_gY              |
| 11    | rms_aY              | 32    | rms_gY              |
| 12    | median_aY           | 33    | median_gY           |
| 13    | dominant_freq_aY    | 34    | dominant_freq_gY    |
| 14    | mean_aZ             | 35    | mean_gZ             |
| 15    | std_aZ              | 36    | std_gZ              |
| 16    | max_aZ              | 37    | max_gZ              |
| 17    | min_aZ              | 38    | min_gZ              |
| 18    | rms_aZ              | 39    | rms_gZ              |
| 19    | median_aZ           | 40    | median_gZ           |
| 20    | dominant_freq_aZ    | 41    | dominant_freq_gZ    |

### A2: Label Vector (`y_labels.npy`)

**Location**: `backend/ml_data/processed/y_labels.npy`  
**Format**: NumPy `.npy` (int64)  
**Shape**: `(N_windows,)`  
**Values**: `0` = Normal, `1` = Parkinson

### A3: Trained Model (`rf_model_v2.pkl`)

**Location**: `backend/ml_models/models/rf_model_v2.pkl`  
**Format**: joblib-serialized `sklearn.ensemble.RandomForestClassifier`  
**Expects**: 42-feature input vector (scaled via StandardScaler)

### A4: Fitted Scaler (`rf_model_v2_scaler.pkl`)

**Location**: `backend/ml_models/models/rf_model_v2_scaler.pkl`  
**Format**: joblib-serialized `sklearn.preprocessing.StandardScaler`  
**Fitted on**: Training split of X_features.npy  
**Usage**: `scaler.transform(features_2d)` before model prediction

### A5: Model Metadata (`rf_model_v2.json`)

**Location**: `backend/ml_models/models/rf_model_v2.json`  
**Format**: JSON

```json
{
  "model_type": "RandomForestClassifier",
  "version": 2,
  "feature_names": [
    "mean_aX", "std_aX", "max_aX", "min_aX", "rms_aX", "median_aX", "dominant_freq_aX",
    "mean_aY", "..."
  ],
  "pipeline_params": {
    "window_size": 200,
    "stride": 30,
    "mpu6050_accel_sensitivity": 16384.0,
    "mpu6050_gyro_sensitivity": 131.0,
    "accel_to_ms2": true,
    "training_sampling_rate_hz": 250.0,
    "fft_tremor_band_low_hz": 3.0,
    "fft_tremor_band_high_hz": 12.0
  },
  "scaler_file": "rf_model_v2_scaler.pkl",
  "hyperparameters": { "n_estimators": "...", "max_depth": "..." },
  "performance_metrics": {
    "accuracy": "...",
    "precision": "...",
    "recall": "...",
    "f1_score": "...",
    "confusion_matrix": "..."
  },
  "training_info": {
    "timestamp": "...",
    "training_samples": "...",
    "test_samples": "...",
    "feature_count": 42,
    "data_source": "Data v2 (Normal + Parkinson)",
    "random_state": 42
  }
}
```

**Key difference from v1 metadata**: 
- No `filter_params` (gravity filter removed)
- Added `pipeline_params` with scaling factors and window parameters
- Added `scaler_file` pointing to the scaler `.pkl`
- Added `feature_names` with exact 42-feature order
- Added `version: 2`
