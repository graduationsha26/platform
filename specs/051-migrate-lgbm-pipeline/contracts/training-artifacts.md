# Contract: Training Artifacts

**Feature**: 051-migrate-lgbm-pipeline

Three artifacts are produced by `backend/ml_models/train.py`, in this order.

## 1. Combined Processed Dataset — `backend/ml_data/combined_processed_data.csv`

**Written BEFORE any model training begins** (spec FR-003 / SC-001).

- Columns: 66 feature columns (axis-major order, see data-model.md Entity 3) + `file_id` + `label`.
- One row per 1-second analysis window across all three groups.
- No `inf`/`NaN` rows (dropped).
- Deterministic given the same raw inputs.

## 2. Model — `backend/ml_models/lgbm_tremor_model.pkl`

- A fitted `imblearn.Pipeline([SMOTE(random_state=42), LGBMClassifier(**PINNED, random_state=42, verbose=-1)])`.
- Serialized with `joblib`.
- `predict()` → {0,1,2}; `predict_proba()` → 3 probabilities (column order = classes 0,1,2).
- No external scaler.

## 3. Metadata — `backend/ml_models/lgbm_tremor_model.json`

```json
{
  "model_type": "lightgbm",
  "classes": { "0": "Non-Tremor", "1": "Tremor", "2": "Voluntary" },
  "n_features": 66,
  "feature_names": ["AX_mean", "AX_std", "AX_median", "AX_q1", "AX_q3", "AX_min", "AX_max",
                    "AX_peak1_freq", "AX_peak1_amp", "AX_peak2_freq", "AX_peak2_amp",
                    "AY_mean", "...", "GZ_peak2_amp"],
  "pipeline": {
    "fs_hz": 66.67,
    "window_seconds": 1.0,
    "window_samples": 67,
    "bandpass_hz": [0.5, 20.0],
    "bandpass_order": 4,
    "scaler": null
  },
  "hyperparameters": {
    "n_estimators": 0, "learning_rate": 0.0, "num_leaves": 0, "max_depth": 0
  },
  "smote": { "random_state": 42 },
  "metrics": {
    "cv": "GroupKFold(4) on file_id",
    "window_macro_precision": 0.0,
    "window_macro_recall": 0.0,
    "window_macro_f1": 0.0,
    "window_accuracy": 0.0,
    "file_macro_precision": 0.0,
    "file_accuracy": 0.0
  },
  "trained_at": "<ISO 8601, stamped at run time>"
}
```

### Consumers of the metadata

- `backend/inference/services.py`: class map, feature order, pipeline constants (no scaler).
- `backend/test_AI_live.py`: class map + `metrics.window_macro_precision` for the constant
  **Precision** column in each output line.

### Field rules

- `hyperparameters`: the exact pinned values discovered by the one-time `RandomizedSearchCV`
  run (research.md §3); zeros above are placeholders filled at training time.
- `metrics`: filled after fitting; `window_macro_precision` is the value reported live.
- `feature_names`: MUST equal the order produced by `extract_features_66()` and match the
  CSV feature columns exactly.
