# Data Model: Retrain Random Forest on 6 Active Sensor Axes (Feature 022)

**Branch**: `022-retrain-rf-6axis` | **Date**: 2026-02-18

---

## Overview

Feature 022 is a training pipeline update. It involves no database schema changes and no new Django models. The "entities" in this feature are pipeline artifacts and in-memory data structures.

---

## Entities

### TrainingDataset

Represents the labeled sensor data loaded from `Dataset.csv` for model training.

| Attribute | Type | Description |
|-----------|------|-------------|
| path | string | File path to `Dataset.csv` (default: `../Dataset.csv` relative to `backend/`) |
| feature_columns | string[6] | Fixed: `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` |
| excluded_columns | string[3] | `['mX', 'mY', 'mZ']` — present in CSV, silently dropped |
| label_column | string | One of: `'label'`, `'Result'`, `'tremor_severity'` (first found) |
| n_samples | int | Total rows (27,995 in current Dataset.csv) |
| n_features | int | Always 6 after column selection |
| n_classes | int | Number of distinct class labels (2 in current dataset) |

**Validation rules**:
- All 6 feature columns must be present; `ValueError` if any missing
- No NaN values in feature columns; `ValueError` if found
- Label column must exist; `ValueError` if not found

**Source of truth**: `backend/apps/ml/feature_utils.py` → `load_training_data()` + `extract_features_from_dataframe()`

---

### GridSearchConfig

Represents the hyperparameter search space passed to GridSearchCV.

| Attribute | Type | Description |
|-----------|------|-------------|
| param_grid | dict | Hyperparameter grid: `{'n_estimators': [100, 200, 300], 'max_depth': [10, 20, None]}` |
| cv_folds | int | 5 — StratifiedKFold with 5 splits |
| scoring | string | `'accuracy'` — cross-validation metric |
| n_jobs | int | `-1` — use all CPU cores |

**Constraints**:
- Cross-validation must use stratified folds to handle class imbalance
- `random_state=42` on both the base estimator and CV splitter for reproducibility

---

### TrainedRandomForest

The fitted RandomForestClassifier selected by GridSearchCV, plus its evaluation metrics.

| Attribute | Type | Description |
|-----------|------|-------------|
| model | RandomForestClassifier | Best estimator from GridSearchCV; `n_features_in_ = 6` |
| best_params | dict | Hyperparameters selected by GridSearchCV |
| best_cv_score | float | Best cross-validation accuracy score (0.0–1.0) |
| test_accuracy | float | Accuracy on held-out 20% test set |
| test_f1_weighted | float | Weighted F1 score on test set |
| classification_report | string | Per-class precision/recall/F1 from sklearn |
| feature_importance | dict | `{feature_name: importance_value}` for all 6 axes |
| trained_date | string | ISO 8601 timestamp |

**Validation rules**:
- `n_features_in_` must equal 6 (validated by `validate_models.py` at inference load time)
- `best_cv_score >= 0.75` is the minimum acceptable threshold (from SC-004 in spec)

---

### ModelArtifact

The serialized form of the TrainedRandomForest, written to disk for inference.

| Attribute | Type | Description |
|-----------|------|-------------|
| pkl_path | string | `backend/ml_models/rf_model.pkl` |
| metrics_path | string | `backend/ml_models/rf_model_metrics.json` |
| format | string | joblib-serialized sklearn model |

**Constraints**:
- Overwrites any existing file at `rf_model.pkl` without error
- The `_metrics.json` file includes `best_params` from GridSearchCV (in addition to existing metrics fields)
- The artifact must pass `validate_sklearn_model('ml_models/rf_model.pkl', expected_features=6)` without raising

---

## Training Pipeline Flow

```
Dataset.csv (raw, 9 sensor columns)
    ↓ load_training_data()  [feature_utils.py]
    ↓ selects: aX, aY, aZ, gX, gY, gZ  (drops mX, mY, mZ)
X: (27995, 6)  y: (27995,)
    ↓ train_test_split(test_size=0.2, stratify=y, random_state=42)
X_train: (~22396, 6)  X_test: (~5599, 6)
    ↓ GridSearchCV(RandomForestClassifier, param_grid, cv=StratifiedKFold(5))
    ↓ selects best_estimator_
TrainedRandomForest (best_params, best_cv_score, n_features_in_=6)
    ↓ save_model('rf_model.pkl', output_dir)
ml_models/rf_model.pkl  +  ml_models/rf_model_metrics.json
    ↓ validate_sklearn_model('ml_models/rf_model.pkl', expected_features=6)
✓ Artifact ready for inference pipeline
```

---

## Inference Pipeline (Unchanged)

After `rf_model.pkl` is exported, the existing inference pipeline (`predict.py`) uses it:

```
POST /api/ml/predict/  {sensor data: [aX, aY, aZ, gX, gY, gZ]}
    ↓ MLPredictor._load_models()
    ↓ loads ml_models/rf_model.pkl  (after predict.py model_files update)
    ↓ validate_sklearn_model(expected_features=6)  ← must pass
    ↓ model.predict([[aX, aY, aZ, gX, gY, gZ]])
    → {prediction: class_label, confidence: float, latency_ms: float}
```

**No changes to the inference API or database** — the model artifact swap is transparent to the REST layer.
