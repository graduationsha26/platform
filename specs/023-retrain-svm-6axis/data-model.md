# Data Model: Retrain SVM on 6 Active Sensor Axes (Feature 023)

**Branch**: `023-retrain-svm-6axis` | **Date**: 2026-02-18
**Phase**: 1 — Design & Contracts

**No new database entities.** This feature operates entirely in the training pipeline — it reads from `Dataset.csv`, trains in memory, and writes to `ml_models/` on disk. No Django models, no migrations, no Supabase schema changes.

---

## Training Pipeline Entities

### TrainingDataset

The input CSV used by `load_training_data()`.

| Attribute | Type | Value |
|-----------|------|-------|
| path | str | `../Dataset.csv` (relative to `backend/`) |
| total_samples | int | 27,995 |
| features | list[str] | `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` |
| label_column | str | class label (binary: 0 or 1) |
| test_split | float | 0.20 (stratified) |

**Train/test partitioning**:
- Training: ~22,396 samples (80%)
- Test: ~5,599 samples (20%)

---

### SVMConfiguration

Fixed hyperparameters passed to `SVC` during training. Not a search space — all values are fixed constants.

| Attribute | Type | Value | Description |
|-----------|------|-------|-------------|
| kernel | str | `'rbf'` | Radial basis function kernel |
| C | float | `1.0` | Regularization parameter |
| gamma | str | `'scale'` | Kernel coefficient; auto-scales with n_features and variance |
| random_state | int | `42` | Reproducibility seed |
| verbose | bool | `True` | Print training progress |

---

### TrainedSVMModel

The artifact produced by `train_svm()`.

| Attribute | Type | Constraint |
|-----------|------|-----------|
| n_features_in_ | int | MUST equal 6 |
| kernel | str | MUST be 'rbf' |
| classes_ | array | Binary class labels (0, 1) |
| artifact_filename | str | `svm_model.pkl` |
| output_directory | str | Configurable via `--output` arg (default: `ml_models`) |

**Validation**: `validate_sklearn_model(path, expected_features=6)` asserts `n_features_in_ == 6` before use.

---

### ModelMetricsRecord

The JSON sidecar written alongside the model artifact by `save_model()`.

| Field | Type | Constraint |
|-------|------|-----------|
| model_type | str | `"SVM"` |
| accuracy | float | 0.0–1.0 |
| f1_score | float | ≥ 0.85 (acceptance threshold) |
| n_features | int | MUST be 6 |
| feature_names | list[str] | `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` |
| kernel | str | `"rbf"` |
| trained_date | str | ISO 8601 UTC timestamp |

**Filename derivation**: `svm_model.pkl` → `svm_model_metrics.json` (automatic via `save_model()`).

---

### InferencePipeline (updated reference)

The `MLPredictor` in `predict.py`. Its `model_files` dict is updated to reference the new artifact.

| Attribute | Before | After |
|-----------|--------|-------|
| `model_files['svm']` | `'svm.pkl'` | `'svm_model.pkl'` |

No other inference logic changes.

---

## Training Pipeline Flow

```
Dataset.csv
    │
    ▼ load_training_data() [feature_utils.py]
    │   Selects FEATURE_COLUMNS = ['aX','aY','aZ','gX','gY','gZ']
    │   Returns X (n×6), y (n,)
    │
    ▼ train_test_split(test_size=0.20, stratify=y, random_state=42)
    │
    ├── X_train (22,396 × 6), y_train
    └── X_test  ( 5,599 × 6), y_test
                │
                ▼ train_svm(X_train, y_train, X_test, y_test)
                │   SVC(kernel='rbf', C=1.0, gamma='scale')
                │   svm.fit(X_train, y_train)
                │
                ▼ evaluate(X_test, y_test)
                │   accuracy, f1_score (weighted)
                │
                ▼ save_model(svm, 'svm_model.pkl', output_dir, metrics)
                    ├── ml_models/svm_model.pkl         [model artifact]
                    └── ml_models/svm_model_metrics.json [metrics sidecar]
```

---

## Artifact Coexistence Table

| Filename | Status | Notes |
|----------|--------|-------|
| `ml_models/random_forest.pkl` | Legacy (preserved) | Old RF from Feature 005 pipeline |
| `ml_models/rf_model.pkl` | Active RF | Created in Feature 022 |
| `ml_models/svm.pkl` | Legacy (preserved) | Old SVM from Feature 005 pipeline |
| `ml_models/svm_model.pkl` | **NEW** (Feature 023) | This feature's output |

Legacy artifacts are never deleted — they serve as backups and are explicitly not referenced by the active inference pipeline.
