# Quickstart: Train ML Models on PSMAD Feature Dataset

**Branch**: `037-train-ml-models` | **Date**: 2026-04-07

## Prerequisites

- `backend/ml_data/processed/ready_for_training_features.csv` must exist (run feature 036 pipeline first)
- Python dependencies installed: `scikit-learn>=1.3.0`, `pandas>=2.0.0`, `numpy>=2.0.0`, `joblib`

## Running the Training Scripts

Both scripts are run from the **repository root** (not from inside `backend/`):

```bash
# Train Random Forest (US1 — run first, faster)
py backend/ml_models/scripts/train_random_forest.py

# Train SVM (US2 — run after RF, slower due to hyperparameter search)
py backend/ml_models/scripts/train_svm.py
```

### With custom input path (if CSV is elsewhere):
```bash
py backend/ml_models/scripts/train_random_forest.py --input backend/ml_data/processed/ready_for_training_features.csv
py backend/ml_models/scripts/train_svm.py --input backend/ml_data/processed/ready_for_training_features.csv
```

## Expected Console Output (RF)

```
======================================================================
Random Forest Classifier Training
======================================================================
[INFO] Loading data from backend/ml_data/processed/ready_for_training_features.csv
[INFO] Dataset: 6110 total samples, 42 features
[INFO] Train: 4888 samples | Test: 1222 samples
[INFO] Label distribution — Train: Control=2326, Parkinson=2562 | Test: 582, 640
[INFO] Validating input data...
[INFO] [OK] Data validation passed (42 features confirmed)
[INFO] Starting GridSearchCV (16 combinations × 5 folds)...
...
[INFO] Best parameters: {'n_estimators': ..., 'max_depth': ...}
[INFO] Best CV score: 0.9xxx
[INFO] Evaluating on test set...
[INFO] Accuracy: 0.xxx (xx.x%)  F1: 0.xxx
[INFO] Saving model to backend/ml_models/models/rf_model_v1.pkl
[INFO] Saving metrics to backend/ml_models/rf_model_metrics_v1.json
[INFO] Cleaning up old model files...
[INFO] [OK] Old files removed
======================================================================
RF Training completed in xx.xx seconds
======================================================================
```

## Expected Output Files

After running both scripts:

```
backend/ml_models/
├── rf_model_metrics_v1.json    ← NEW (RF metrics)
├── svm_model_metrics_v1.json   ← NEW (SVM metrics)
└── models/
    ├── rf_model_v1.pkl         ← NEW (RF model)
    └── svm_model_v1.pkl        ← NEW (SVM model)
```

The following files should be **absent** after training:
- `backend/ml_models/models/`: `random_forest.pkl`, `random_forest.json`, `rf_model.pkl`, `rf_model.json`, `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`
- `backend/ml_models/`: `random_forest.pkl`, `random_forest.json`, `rf_model.pkl`, `rf_model.json`, `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`, `rf_model_metrics.json`, `svm_model_metrics.json`

## Verification

```python
# Quick sanity check — run from repo root
import joblib, json, numpy as np

rf = joblib.load("backend/ml_models/models/rf_model_v1.pkl")
svm = joblib.load("backend/ml_models/models/svm_model_v1.pkl")

# Dummy 42-feature input (one window)
x = np.zeros((1, 42))
print("RF prediction:", rf.predict(x))    # Should be 0 or 1
print("SVM prediction:", svm.predict(x))  # Should be 0 or 1

with open("backend/ml_models/rf_model_metrics_v1.json") as f:
    m = json.load(f)
print("RF accuracy:", m["performance_metrics"]["accuracy"])
print("RF feature_count:", m["training_info"]["feature_count"])  # Should be 42
```

## Expected Performance (approximate)

| Model | Expected Test Accuracy | Notes |
|---|---|---|
| Random Forest | 88–95% | PSMAD is a clean, well-separated dataset |
| SVM (RBF) | 78–90% | Requires StandardScaler; slower to train |

If accuracy is below these ranges, check that the input CSV is the correct 42-feature PSMAD output (not the legacy 30-feature files).
