# Quickstart: Retrain Random Forest on 6 Axes (Feature 022)

**Branch**: `022-retrain-rf-6axis` | **Date**: 2026-02-18

This guide shows how to retrain, verify, and test the updated Random Forest model.

---

## Prerequisites

- `Dataset.csv` present at repo root: `C:/Data from HDD/Graduation Project/Platform/Dataset.csv`
- Python environment active with scikit-learn and joblib installed
- Working directory: `backend/` unless stated otherwise

---

## Scenario 1: Run Training with GridSearchCV (US1)

After the `train_random_forest()` function is updated to use GridSearchCV:

```bash
cd backend
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models rf
```

**Expected console output** (approximate):

```
Loading training data from ../Dataset.csv...
Loaded 27995 samples with 6 features from ../Dataset.csv
Labels found: 2 unique classes

Dataset split:
  Training: 22396 samples
  Test: 5599 samples
  Features: 6

=== Training Random Forest ===
Training samples: 22396
Test samples: 5599
Features: 6 (aX, aY, aZ, gX, gY, gZ)

Starting GridSearchCV...
  Testing N parameter combinations with 5-fold CV...
  [GridSearchCV progress output...]

Best parameters: {'max_depth': ..., 'n_estimators': ...}
Best CV accuracy: X.XXXX

--- Random Forest Results ---
Accuracy: X.XXXX
F1 Score: X.XXXX

Classification Report:
              precision    recall  f1-score   support
           0       X.XX      X.XX      X.XX      XXXX
           1       X.XX      X.XX      X.XX      XXXX

Feature Importance:
  aX: X.XXXX
  aY: X.XXXX
  ...

✓ Saved model to ml_models/rf_model.pkl
✓ Saved metrics to ml_models/rf_model_metrics.json

✓ All models meet F1 score requirement (≥ 0.85)
✓ Training complete!
```

**Verify model artifact exists**:

```bash
python -c "import os; print('rf_model.pkl exists:', os.path.exists('ml_models/rf_model.pkl'))"
```

Expected: `rf_model.pkl exists: True`

---

## Scenario 2: Verify Model Accepts 6-Axis Input (US1 acceptance)

```bash
cd backend
python -c "
import joblib, numpy as np
model = joblib.load('ml_models/rf_model.pkl')
print(f'n_features_in_: {model.n_features_in_}')
assert model.n_features_in_ == 6, 'Expected 6 features!'

# Test prediction with 6-axis input
X = np.array([[0.5, -0.3, 10.2, 0.05, -0.02, 0.01]])
pred = model.predict(X)
proba = model.predict_proba(X)
print(f'Prediction: {pred[0]}')
print(f'Probabilities: {proba[0]}')
print('PASS: Model accepts 6-axis input and returns a prediction')
"
```

Expected: No errors; `n_features_in_: 6`; a valid class label printed.

---

## Scenario 3: Verify Inference Pipeline Loads rf_model.pkl (US2)

After updating `predict.py`'s `model_files` dict:

```bash
cd backend
python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json
```

Expected output:
```
Initializing ML Predictor...
  Model directory: ml_models
  Params file: ml_data/params.json

Loading normalization parameters...
[OK] Loaded params: 6 features

Validating and loading models...
[OK] RF: n_features_in_=6
[OK] ML Predictor ready (1 models loaded)  ← or 2 if SVM also present

Test sensor data: [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]
Model: RF

--- Prediction Result ---
Prediction: X
Confidence: X.XXXX
Latency: X.XX ms
[OK] Latency within requirement (<70ms)
```

No `FileNotFoundError` for `rf_model.pkl`, and no shape mismatch errors.

---

## Scenario 4: Validate Model with validate_models.py

```bash
cd backend
python apps/ml/validate_models.py ml_models/rf_model.pkl 6
```

Expected:
```
✓ Model validated: n_features_in_ = 6
```

---

## Scenario 5: Inspect Metrics JSON

```bash
cd backend
python -c "
import json
with open('ml_models/rf_model_metrics.json') as f:
    m = json.load(f)
print(f'Model type: {m[\"model_type\"]}')
print(f'Test accuracy: {m[\"accuracy\"]:.4f}')
print(f'F1 score: {m[\"f1_score\"]:.4f}')
print(f'Best params (GridSearchCV): {m[\"best_params\"]}')
print(f'Best CV score: {m[\"best_cv_score\"]:.4f}')
print(f'n_features: {m[\"n_features\"]}')
assert m['n_features'] == 6, 'Expected 6 features in metrics!'
assert 'best_params' in m, 'best_params must be present (from GridSearchCV)!'
print('PASS: Metrics JSON is valid and contains GridSearchCV best_params')
"
```

---

## Scenario 6: Legacy Backward Compatibility Check

Confirm the old `random_forest.pkl` was NOT deleted and `svm.pkl` still works:

```bash
cd backend
python -c "
import os
print('Old random_forest.pkl still exists (backup):', os.path.exists('ml_models/random_forest.pkl'))
print('SVM model unchanged:', os.path.exists('ml_models/svm.pkl'))
print('New rf_model.pkl is the active model:', os.path.exists('ml_models/rf_model.pkl'))
"
```
