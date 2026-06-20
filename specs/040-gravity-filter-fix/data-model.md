# Data Model: Gravity Filter Fix for ML Pipeline

**Feature**: 040-gravity-filter-fix | **Date**: 2026-04-13

## Overview

This feature does not introduce new database entities. It extends the existing model metadata JSON schema to include gravity filter parameters, ensuring reproducible preprocessing between training and inference.

## Entity: Model Metadata (Extended)

### Current Schema (before this feature)

```json
{
  "model_type": "RandomForestClassifier | SVC | LSTM | CNN1D",
  "hyperparameters": { ... },
  "performance_metrics": {
    "accuracy": float,
    "precision": float,
    "recall": float,
    "f1_score": float,
    "confusion_matrix": [[int]],
    "meets_threshold": bool
  },
  "cross_validation": { ... },
  "training_info": {
    "timestamp": "ISO-8601",
    "training_time_seconds": float,
    "training_samples": int,
    "test_samples": int,
    "feature_count": int,
    "dataset_source": "string",
    "random_state": int
  }
}
```

### Extended Schema (after this feature)

New top-level key `filter_params` added:

```json
{
  "model_type": "...",
  "hyperparameters": { ... },
  "performance_metrics": { ... },
  "cross_validation": { ... },
  "training_info": { ... },
  "filter_params": {
    "type": "butterworth",
    "subtype": "highpass",
    "order": 2,
    "cutoff_hz": 0.5,
    "sampling_rate_hz": 37.0,
    "sos_coefficients": [[float, float, float, float, float, float]],
    "applied_to_axes": ["aX", "aY", "aZ"],
    "skipped_axes": ["gX", "gY", "gZ"],
    "initial_conditions": "sosfilt_zi_scaled"
  }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Filter family. Always `"butterworth"` for this feature. |
| `subtype` | string | Filter subtype. Always `"highpass"` for gravity removal. |
| `order` | int | Filter order. Value: `2`. |
| `cutoff_hz` | float | Cutoff frequency in Hz. Value: `0.5`. |
| `sampling_rate_hz` | float | Sampling rate used to design the filter. Computed from training data timestamps. |
| `sos_coefficients` | array of [6-float arrays] | Second-order section coefficients. For 2nd-order filter, this is a single section `[[b0, b1, b2, a0, a1, a2]]`. Stored to avoid re-computation and ensure exact reproducibility. |
| `applied_to_axes` | array of strings | Which sensor axes the filter was applied to. Always accelerometer axes. |
| `skipped_axes` | array of strings | Which sensor axes were NOT filtered. Always gyroscope axes. |
| `initial_conditions` | string | Method used for filter initialization. `"sosfilt_zi_scaled"` means steady-state initial conditions scaled by first sample value. |

### Validation Rules

- `sos_coefficients` must be a non-empty list of 6-element sublists
- `cutoff_hz` must be positive and less than `sampling_rate_hz / 2` (Nyquist constraint)
- `order` must be a positive integer
- `applied_to_axes` must be a subset of the model's expected input axes
- `sampling_rate_hz` must be positive

## Entity: Filter Parameters File

### Schema

Saved as `backend/ml_data/processed/filter_params.json` during pipeline execution:

```json
{
  "type": "butterworth",
  "subtype": "highpass",
  "order": 2,
  "cutoff_hz": 0.5,
  "sampling_rate_hz": 37.0,
  "sos_coefficients": [[float, float, float, float, float, float]],
  "applied_to_axes": ["aX", "aY", "aZ"],
  "skipped_axes": ["gX", "gY", "gZ"],
  "initial_conditions": "sosfilt_zi_scaled",
  "created": "ISO-8601 timestamp",
  "source_dataset": "string (e.g., 'PSMAD')"
}
```

### Relationships

- **Filter Parameters File** → consumed by training scripts → embedded into **Model Metadata**
- **Model Metadata** → consumed by inference service → reconstructs filter for live data
- One filter configuration produces one set of SOS coefficients, shared across all models trained in the same pipeline run

## Data Flow Diagram

```
[filter_params.json] ──────────────────────────────────────┐
   Created by: 4_psmad_pipeline.py                         │
   Contains: SOS coefficients, cutoff, sampling rate       │
                                                           ▼
[rf_model_metrics_v1.json] ←── train_random_forest.py ── Reads filter_params.json
[svm_model_metrics_v1.json] ←── train_svm.py ─────────── Reads filter_params.json
[lstm_model.json] ←── train_lstm.py ───────────────────── Reads filter_params.json
[cnn_1d_model.json] ←── train_cnn_1d.py ──────────────── Reads filter_params.json
                                                           │
                                                           ▼
[PreprocessingService] ── Reads filter_params from ── model metadata JSON
                          loaded model's metadata     at model load time
```
