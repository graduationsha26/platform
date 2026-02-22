# Quickstart: Retrain SVM on 6 Axes (Feature 023)

**Branch**: `023-retrain-svm-6axis` | **Date**: 2026-02-18

This guide shows how to retrain, verify, and test the updated SVM model.

---

## Prerequisites

- `Dataset.csv` present at repo root: `C:/Data from HDD/Graduation Project/Platform/Dataset.csv`
- Python environment active with scikit-learn and joblib installed
- Working directory: `backend/` unless stated otherwise
- `rf_model.pkl` already present (produced by Feature 022); SVM training does not depend on it

---

## Scenario 1: Run SVM Training (US1)

After the `save_model(svm_model, ...)` filename is updated in `train.py`:

```bash
cd backend
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models svm
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

=== Training SVM ===
Training samples: 22396
Test samples: 5599
Features: 6 (aX, aY, aZ, gX, gY, gZ)

Training SVM...
[LibSVM progress output...]

--- SVM Results ---
Accuracy: X.XXXX
F1 Score: X.XXXX
n_features_in_: 6

Classification Report:
              precision    recall  f1-score   support
           0       X.XX      X.XX      X.XX      XXXX
           1       X.XX      X.XX      X.XX      XXXX

✓ Saved model to ml_models/svm_model.pkl
✓ Saved metrics to ml_models/svm_model_metrics.json

============================================================
TRAINING SUMMARY
============================================================

SVM:
  F1 Score: X.XXXX
  Accuracy: X.XXXX
  Features: 6

============================================================
VALIDATION CHECK
============================================================
✓ All models meet F1 score requirement (≥ 0.85)

✓ Training complete!
```

**Verify model artifact exists**:

```bash
python -c "import os; print('svm_model.pkl exists:', os.path.exists('ml_models/svm_model.pkl'))"
```

Expected: `svm_model.pkl exists: True`

---

## Scenario 2: Verify Model Accepts 6-Axis Input (US1 acceptance)

```bash
cd backend
python -c "
import joblib, numpy as np
model = joblib.load('ml_models/svm_model.pkl')
print(f'n_features_in_: {model.n_features_in_}')
assert model.n_features_in_ == 6, 'Expected 6 features!'
assert model.kernel == 'rbf', 'Expected RBF kernel!'

# Test prediction with 6-axis input
X = np.array([[0.5, -0.3, 10.2, 0.05, -0.02, 0.01]])
pred = model.predict(X)
print(f'Prediction: {pred[0]}')
print(f'Kernel: {model.kernel}')
print('PASS: SVM accepts 6-axis input and returns a prediction')
"
```

Expected: No errors; `n_features_in_: 6`; `Kernel: rbf`; a valid class label printed.

---

## Scenario 3: Verify Inference Pipeline Loads svm_model.pkl (US2)

After updating `predict.py`'s `model_files` dict:

```bash
cd backend
python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json --model-type svm
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
[OK] SVM: n_features_in_=6
[OK] ML Predictor ready (2 models loaded)

Test sensor data: [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]
Model: SVM

--- Prediction Result ---
Prediction: X
Confidence: 1.0000
Latency: X.XX ms
[OK] Latency within requirement (<70ms)
```

No `FileNotFoundError` for `svm_model.pkl`, and no shape mismatch errors.

---

## Scenario 4: Validate Model with validate_models.py

```bash
cd backend
python apps/ml/validate_models.py ml_models/svm_model.pkl 6
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
with open('ml_models/svm_model_metrics.json') as f:
    m = json.load(f)
print(f'Model type: {m[\"model_type\"]}')
print(f'Test accuracy: {m[\"accuracy\"]:.4f}')
print(f'F1 score: {m[\"f1_score\"]:.4f}')
print(f'Kernel: {m[\"kernel\"]}')
print(f'n_features: {m[\"n_features\"]}')
assert m['n_features'] == 6, 'Expected 6 features in metrics!'
assert m['kernel'] == 'rbf', 'Expected rbf kernel in metrics!'
assert m['f1_score'] >= 0.85, f'F1 score {m[\"f1_score\"]:.4f} below threshold!'
print('PASS: Metrics JSON is valid')
"
```

---

## Scenario 6: Legacy Backward Compatibility Check

Confirm the old `svm.pkl` was NOT deleted and `rf_model.pkl` still works:

```bash
cd backend
python -c "
import os
print('Old svm.pkl still exists (backup):', os.path.exists('ml_models/svm.pkl'))
print('RF model unchanged:', os.path.exists('ml_models/rf_model.pkl'))
print('New svm_model.pkl is the active model:', os.path.exists('ml_models/svm_model.pkl'))
"
```

---

## Combined Inference Test (Both Models)

After both RF (Feature 022) and SVM (Feature 023) are trained:

```bash
cd backend
python -c "
from apps.ml.predict import MLPredictor
predictor = MLPredictor('ml_models', 'ml_data/params.json')

sensor_data = [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]

rf_result = predictor.predict(sensor_data, model_type='rf')
svm_result = predictor.predict(sensor_data, model_type='svm')

print(f'RF prediction: {rf_result[\"prediction\"]} (confidence: {rf_result[\"confidence\"]:.4f})')
print(f'SVM prediction: {svm_result[\"prediction\"]} (confidence: {svm_result[\"confidence\"]:.4f})')
print(f'Models agree: {rf_result[\"prediction\"] == svm_result[\"prediction\"]}')
"
```
