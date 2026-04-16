# Data Model: Train ML Models on PSMAD Feature Dataset

**Branch**: `037-train-ml-models` | **Date**: 2026-04-07

This feature produces no database entities — it is a standalone batch training pipeline. The "data model" describes the file-based artifacts and their schemas.

---

## Input Entity: FeatureDataset

**File**: `backend/ml_data/processed/ready_for_training_features.csv`  
**Format**: CSV, 6,110 rows × 43 columns  
**Produced by**: Feature 036 (PSMAD preprocessing pipeline)

| Column Group | Count | Names | Description |
|---|---|---|---|
| Time-domain features | 30 | `RMS_aX`, `mean_aX`, `std_aX`, `skewness_aX`, `kurtosis_aX`, … (×6 axes) | Computed from raw IMU windows |
| FFT tremor-band features | 12 | `dominant_freq_aX`, `tremor_energy_aX`, … (×6 axes) | 3–12 Hz band features |
| Label | 1 | `label` | 0 = Control, 1 = Parkinson |

**Validation rules**:
- Exactly 43 columns (42 features + `label`)
- `label` column contains only 0 and 1
- No NaN or Inf values in any column

---

## Derived Entities: TrainSplit / TestSplit

Created in-memory during training; not persisted to disk.

| Field | Value |
|---|---|
| Train size | ~4,888 rows (80%, stratified) |
| Test size | ~1,222 rows (20%, stratified) |
| Split method | Stratified random split by `label` |
| Random state | 42 (for reproducibility) |

---

## Output Entity: TrainedModel (×2)

**Files**: `backend/ml_models/models/rf_model_v1.pkl` and `svm_model_v1.pkl`  
**Format**: joblib-serialized scikit-learn estimator  
**Loaded by**: Django inference endpoint `/api/predict/`

| Attribute | RF | SVM |
|---|---|---|
| Algorithm | RandomForestClassifier | SVC (RBF kernel) |
| Input features | 42 | 42 (scaled via StandardScaler) |
| Output | Binary class: 0 or 1 | Binary class: 0 or 1 |

---

## Output Entity: ModelMetrics (×2)

**Files**: `backend/ml_models/rf_model_metrics_v1.json` and `svm_model_metrics_v1.json`

```json
{
  "model_type": "RandomForestClassifier",
  "hyperparameters": {
    "n_estimators": 200,
    "max_depth": null
  },
  "performance_metrics": {
    "accuracy": 0.923,
    "precision": 0.921,
    "recall": 0.926,
    "f1_score": 0.923,
    "confusion_matrix": [[TN, FP], [FN, TP]],
    "meets_threshold": false
  },
  "cross_validation": {
    "cv_scores": [0.91, 0.94, 0.93, 0.92, 0.90],
    "cv_mean": 0.92,
    "cv_std": 0.015
  },
  "training_info": {
    "timestamp": "2026-04-07T...",
    "training_time_seconds": 45.2,
    "training_samples": 4888,
    "test_samples": 1222,
    "feature_count": 42,
    "dataset_source": "ready_for_training_features.csv",
    "random_state": 42,
    "sklearn_version": "1.x.x",
    "python_version": "3.14.x"
  }
}
```

---

## Artifact Lifecycle

```
ready_for_training_features.csv     (read-only input)
            |
            v
   [train_test_split 80/20]
            |
    ________|________
   |                 |
X_train / y_train   X_test / y_test
   |                 |
[GridSearchCV]    [evaluate_model()]
   |                 |
best_model        metrics dict
   |                 |
   v                 v
rf_model_v1.pkl    rf_model_metrics_v1.json
svm_model_v1.pkl   svm_model_metrics_v1.json
```

---

## Superseded Artifacts (deleted after successful training)

### From `backend/ml_models/models/`
- `random_forest.pkl`, `random_forest.json`
- `rf_model.pkl`, `rf_model.json`
- `svm_model.pkl`, `svm_model.json`
- `svm_rbf.pkl`, `svm_rbf.json`

### From `backend/ml_models/` (root)
- `random_forest.pkl`, `random_forest.json`
- `rf_model.pkl`, `rf_model.json`
- `svm_model.pkl`, `svm_model.json`
- `svm_rbf.pkl`, `svm_rbf.json`
- `rf_model_metrics.json`
- `svm_model_metrics.json`
