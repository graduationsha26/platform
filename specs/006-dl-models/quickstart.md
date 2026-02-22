# Quick Start Guide: Deep Learning Models Training

**Feature**: 006-dl-models | **Date**: 2026-02-15
**Purpose**: Validation scenarios and usage examples for deep learning model training

## Prerequisites

Before running these scenarios, ensure:

1. **Feature 004 Complete**: `backend/ml_data/processed/` contains:
   - `train_sequences.npy` (training sequences - 349 samples × 128 timesteps × 6 features)
   - `train_seq_labels.npy` (training labels - 349 binary labels)
   - `test_sequences.npy` (test sequences - 87 samples × 128 timesteps × 6 features)
   - `test_seq_labels.npy` (test labels - 87 binary labels)

2. **Dependencies Installed**: TensorFlow ≥2.13.0, NumPy, scikit-learn in `backend/requirements.txt`

3. **Directory Structure**: `backend/dl_models/` directory exists with subdirectories:
   - `scripts/` (training scripts)
   - `scripts/utils/` (utility modules)
   - `models/` (output directory for trained models)

4. **Working Directory**: Execute all commands from repository root: `C:\Data from HDD\Graduation Project\Platform\`

---

## Scenario 1: Train LSTM Model (User Story 1 - MVP)

**Goal**: Train LSTM model, verify ≥95% accuracy, confirm model export.

**Command**:
```bash
python backend/dl_models/scripts/train_lstm.py
```

**Expected Output**:
```
======================================================================
LSTM Model Training
======================================================================
[INFO] Loading training data from backend/ml_data/processed/...
[INFO] Train set: 446 samples, 50 timesteps, 6 features
[INFO] Test set: 110 samples, 50 timesteps, 6 features
[INFO] Validating input data...
[INFO] [OK] Data validation passed
[INFO] Splitting training data (80/20 train/validation)...
[INFO] Train: 357 samples, Validation: 89 samples
[INFO] Building LSTM model...
[INFO] Model architecture:
  - LSTM(64, return_sequences=True) + Dropout(0.3)
  - LSTM(32) + Dropout(0.3)
  - Dense(1, sigmoid)
[INFO] Total parameters: 30,625
[INFO] Setting up EarlyStopping (monitor=val_loss, patience=10)...
[INFO] Starting training (max_epochs=100, batch_size=32)...

Epoch 1/100
12/12 [==============================] - 3s 120ms/step - loss: 0.6931 - accuracy: 0.5210 - val_loss: 0.7012 - val_accuracy: 0.4944
Epoch 2/100
12/12 [==============================] - 1s 85ms/step - loss: 0.5124 - accuracy: 0.7423 - val_loss: 0.4893 - val_accuracy: 0.7303
...
Epoch 23/100
12/12 [==============================] - 1s 88ms/step - loss: 0.1563 - accuracy: 0.9384 - val_loss: 0.2014 - val_accuracy: 0.9101

[INFO] Early stopping triggered at epoch 23
[INFO] Restored weights from best epoch: 13 (val_loss: 0.1234)
[INFO] Evaluating on test set...
[INFO] Test Accuracy: 96.4%
[INFO] Test Precision: 95.7%
[INFO] Test Recall: 97.1%
[INFO] Test F1-Score: 96.4%
[INFO] Confusion Matrix:
       Predicted
       0    1
Actual
0     53    3
1      2   52
[INFO] [OK] Model meets >=95% accuracy threshold
[INFO] Saving model to backend/dl_models/models/...
[INFO] Model saved: backend/dl_models/models/lstm_model.h5
[INFO] Metadata saved: backend/dl_models/models/lstm_model.json
[INFO] Validating model loading...
[INFO] Test predictions (first 5): [1 0 1 0 1]
[INFO] [OK] Model loading validation passed
======================================================================
Training completed in 342.50 seconds
LSTM model ready for deployment
======================================================================
```

**Validation Checks**:
- ✅ Training completes without errors
- ✅ Early stopping triggers (epochs < 100)
- ✅ Test accuracy ≥95%
- ✅ Files created: `lstm_model.h5` (~50-100 MB), `lstm_model.json` (~10 KB)
- ✅ Training time <15 minutes
- ✅ Model loads successfully and produces predictions

---

## Scenario 2: Train 1D-CNN Model (User Story 2)

**Goal**: Train 1D-CNN model, verify ≥95% accuracy, confirm model export.

**Command**:
```bash
python backend/dl_models/scripts/train_cnn_1d.py
```

**Expected Output**:
```
======================================================================
1D-CNN Model Training
======================================================================
[INFO] Loading training data from backend/ml_data/processed/...
[INFO] Train set: 446 samples, 50 timesteps, 6 features
[INFO] Test set: 110 samples, 50 timesteps, 6 features
[INFO] Validating input data...
[INFO] [OK] Data validation passed
[INFO] Splitting training data (80/20 train/validation)...
[INFO] Train: 357 samples, Validation: 89 samples
[INFO] Building 1D-CNN model...
[INFO] Model architecture:
  - Conv1D(64, kernel=3) + BatchNorm + MaxPool(2)
  - Conv1D(128, kernel=3) + BatchNorm + MaxPool(2)
  - Conv1D(256, kernel=3) + BatchNorm + MaxPool(2)
  - Flatten + Dense(128) + Dropout(0.5) + Dense(1, sigmoid)
[INFO] Total parameters: 154,753
[INFO] Setting up EarlyStopping (monitor=val_loss, patience=10)...
[INFO] Starting training (max_epochs=100, batch_size=32)...

Epoch 1/100
12/12 [==============================] - 2s 95ms/step - loss: 0.6928 - accuracy: 0.5294 - val_loss: 0.6895 - val_accuracy: 0.5056
Epoch 2/100
12/12 [==============================] - 1s 52ms/step - loss: 0.4732 - accuracy: 0.7647 - val_loss: 0.4321 - val_accuracy: 0.7865
...
Epoch 19/100
12/12 [==============================] - 1s 55ms/step - loss: 0.1234 - accuracy: 0.9524 - val_loss: 0.1789 - val_accuracy: 0.9326

[INFO] Early stopping triggered at epoch 19
[INFO] Restored weights from best epoch: 9 (val_loss: 0.1012)
[INFO] Evaluating on test set...
[INFO] Test Accuracy: 97.3%
[INFO] Test Precision: 96.8%
[INFO] Test Recall: 97.7%
[INFO] Test F1-Score: 97.2%
[INFO] Confusion Matrix:
       Predicted
       0    1
Actual
0     54    2
1      1   53
[INFO] [OK] Model meets >=95% accuracy threshold
[INFO] Saving model to backend/dl_models/models/...
[INFO] Model saved: backend/dl_models/models/cnn_1d_model.h5
[INFO] Metadata saved: backend/dl_models/models/cnn_1d_model.json
[INFO] Validating model loading...
[INFO] Test predictions (first 5): [1 0 1 0 1]
[INFO] [OK] Model loading validation passed
======================================================================
Training completed in 187.30 seconds
1D-CNN model ready for deployment
======================================================================
```

**Validation Checks**:
- ✅ Training completes without errors
- ✅ Early stopping triggers (epochs < 100)
- ✅ Test accuracy ≥95%
- ✅ Files created: `cnn_1d_model.h5` (~150-300 MB), `cnn_1d_model.json` (~12 KB)
- ✅ Training time <15 minutes
- ✅ Model loads successfully and produces predictions

---

## Scenario 3: Generate Model Comparison Report

**Goal**: Compare LSTM and 1D-CNN models, identify best performer.

**Prerequisites**: Both models trained (Scenarios 1 and 2 complete).

**Command**:
```bash
python backend/dl_models/scripts/compare_models.py
```

**Expected Output**:
```
======================================================================
Model Comparison Report Generator
======================================================================
[INFO] Loading LSTM metadata...
[INFO] [OK] LSTM metadata loaded
[INFO] Loading 1D-CNN metadata...
[INFO] [OK] 1D-CNN metadata loaded
[INFO] Generating comparison report...

======================================================================
MODEL COMPARISON REPORT
======================================================================
Generated: 2026-02-15 14:45:30

LSTM Model:
  Accuracy:   96.4%
  Precision:  95.7%
  Recall:     97.1%
  F1-Score:   96.4%
  Training Time: 342.5 seconds

1D-CNN Model:
  Accuracy:   97.3%
  Precision:  96.8%
  Recall:     97.7%
  F1-Score:   97.2%
  Training Time: 187.3 seconds

Best Model: 1D-CNN [97.3% accuracy]

Recommendation:
  1D-CNN achieves higher accuracy with faster training time. Recommended for deployment.
  Note: Consider LSTM if model interpretability (attention weights) is needed.
======================================================================

[INFO] Report saved to backend/dl_models/models/comparison_report.txt
======================================================================
```

**Validation Checks**:
- ✅ Report loads both model metadata successfully
- ✅ Report displays all metrics (accuracy, precision, recall, F1, training time)
- ✅ Report identifies best model based on accuracy
- ✅ Report provides deployment recommendation
- ✅ File created: `comparison_report.txt` (~1-2 KB)

---

## Scenario 4: Test Model Inference (Prediction)

**Goal**: Load trained model and perform inference on test sequences.

**Prerequisites**: LSTM model trained (Scenario 1 complete).

**Test Script** (`test_inference.py`):
```python
import numpy as np
import tensorflow as tf
import time

# Load trained model
model = tf.keras.models.load_model('backend/dl_models/models/lstm_model.h5')

# Load test data
X_test = np.load('backend/ml_data/processed/test_sequences.npy')
y_test = np.load('backend/ml_data/processed/test_seq_labels.npy')

# Test single sequence inference
single_sequence = X_test[0:1]  # Shape: (1, 50, 6)
start_time = time.time()
prediction = model.predict(single_sequence, verbose=0)
inference_time = (time.time() - start_time) * 1000  # Convert to ms

print(f"Prediction: {prediction[0][0]:.4f} (class: {int(prediction[0][0] > 0.5)})")
print(f"Actual: {y_test[0]}")
print(f"Inference time: {inference_time:.2f} ms")

# Test batch inference
batch = X_test[:10]  # 10 sequences
start_time = time.time()
predictions = model.predict(batch, verbose=0)
batch_time = (time.time() - start_time) * 1000

print(f"\nBatch inference (10 sequences): {batch_time:.2f} ms")
print(f"Average per sequence: {batch_time/10:.2f} ms")
```

**Expected Output**:
```
Prediction: 0.9823 (class: 1)
Actual: 1
Inference time: 45.32 ms

Batch inference (10 sequences): 123.45 ms
Average per sequence: 12.35 ms
```

**Validation Checks**:
- ✅ Model loads without errors
- ✅ Single sequence inference <100ms
- ✅ Batch inference improves per-sequence time (~10-20ms per sequence)
- ✅ Predictions match expected labels (≥95% accuracy)

---

## Scenario 5: Verify Reproducibility

**Goal**: Confirm that training produces identical results with same random seed.

**Commands**:
```bash
# Train LSTM twice with same seed
python backend/dl_models/scripts/train_lstm.py --random-state 42
python backend/dl_models/scripts/train_lstm.py --random-state 42
```

**Validation**:
```python
import json

# Load metadata from both runs
with open('backend/dl_models/models/lstm_model.json') as f:
    metadata1 = json.load(f)

# Rename first model, train again
# ... (manual step to save first model with different name)

with open('backend/dl_models/models/lstm_model.json') as f:
    metadata2 = json.load(f)

# Compare results
assert metadata1['performance_metrics']['accuracy'] == metadata2['performance_metrics']['accuracy']
assert metadata1['training_history']['epochs_completed'] == metadata2['training_history']['epochs_completed']
assert metadata1['hyperparameters']['random_state'] == metadata2['hyperparameters']['random_state'] == 42

print("[OK] Training is reproducible with fixed random seed")
```

**Validation Checks**:
- ✅ Same accuracy across runs (CPU training)
- ✅ Same number of epochs before early stopping
- ✅ Same training/validation split

**Note**: GPU training may produce slight variations (~0.1% accuracy difference) due to non-deterministic CUDA operations.

---

## Scenario 6: Test Edge Case - Below Threshold Accuracy

**Goal**: Verify that models below 95% accuracy are still exported with warning.

**Simulation**: Intentionally reduce training data or use suboptimal hyperparameters.

**Command**:
```bash
python backend/dl_models/scripts/train_lstm.py --max-epochs 5
```

**Expected Output**:
```
...
[INFO] Evaluating on test set...
[INFO] Test Accuracy: 87.3%
[INFO] Test Precision: 85.1%
[INFO] Test Recall: 89.7%
[INFO] Test F1-Score: 87.3%
[WARNING] Model achieved 87.3%, below 95% threshold
[INFO] Saving model to backend/dl_models/models/...
[INFO] Model saved: backend/dl_models/models/lstm_model.h5
[INFO] Metadata saved: backend/dl_models/models/lstm_model.json
...
```

**Metadata Check**:
```json
{
    "performance_metrics": {
        "accuracy": 0.873,
        "meets_threshold": false
    }
}
```

**Validation Checks**:
- ✅ Warning logged (not error)
- ✅ Model still exported (.h5 and .json files created)
- ✅ `meets_threshold: false` flag set in metadata
- ✅ Script exits with code 0 (success)

---

## Scenario 7: Test GPU Availability and CPU Fallback

**Goal**: Verify training works on both CPU and GPU (if available).

**Command**:
```bash
python backend/dl_models/scripts/train_lstm.py
```

**GPU Detection**:
```python
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"[INFO] GPU available: {len(gpus)} device(s)")
    print(f"[INFO] Using GPU for training")
else:
    print(f"[INFO] No GPU detected, using CPU")
```

**Expected Behavior**:
- **With GPU**: Faster training (~3-5x speedup), logged in metadata
  ```json
  "training_info": {
      "gpu_available": true,
      "gpu_device": "NVIDIA GeForce RTX 3060",
      "training_time_seconds": 87.3
  }
  ```

- **Without GPU**: Training proceeds on CPU, logged in metadata
  ```json
  "training_info": {
      "gpu_available": false,
      "training_time_seconds": 342.5
  }
  ```

**Validation Checks**:
- ✅ Training completes successfully on both CPU and GPU
- ✅ GPU status logged in metadata
- ✅ No errors when GPU unavailable (graceful fallback)

---

## Scenario 8: Validate Model Export Format

**Goal**: Confirm models are exported in .h5 format (not .keras or SavedModel).

**Validation**:
```bash
ls -lh backend/dl_models/models/

# Expected output:
# lstm_model.h5          85M
# lstm_model.json        12K
# cnn_1d_model.h5       234M
# cnn_1d_model.json      15K
# comparison_report.txt  1.2K
```

**Load Test**:
```python
import tensorflow as tf

# Verify .h5 format loads correctly
model = tf.keras.models.load_model('backend/dl_models/models/lstm_model.h5')
print(f"Model type: {type(model)}")  # <class 'keras.src.engine.sequential.Sequential'>
print(f"Model format: HDF5")

# Verify model is callable
import numpy as np
dummy_input = np.random.randn(1, 50, 6)
output = model.predict(dummy_input, verbose=0)
print(f"Output shape: {output.shape}")  # (1, 1)
```

**Validation Checks**:
- ✅ Models saved with .h5 extension
- ✅ Models loadable with `tf.keras.models.load_model()`
- ✅ No .keras or SavedModel directories created
- ✅ Model files are single-file archives (not directories)

---

## Integration Scenarios (Future Features)

### Feature 007: Model Serving via Django API

**Endpoint**: `POST /api/tremor/predict`

**Request**:
```json
{
    "model": "lstm",
    "sequence": [[...], [...], ...],  // 50 timesteps × 6 features
}
```

**Response**:
```json
{
    "prediction": 1,
    "confidence": 0.9823,
    "model_used": "lstm",
    "model_version": "1.0.0",
    "inference_time_ms": 45.32
}
```

### Feature 008: Ensemble Methods

Combine LSTM + 1D-CNN predictions using:
- **Voting**: Majority vote (or average probabilities)
- **Stacking**: Meta-learner on top of base models
- **Weighted Average**: Weight by model accuracy

---

## Troubleshooting

### Issue: TensorFlow Not Installed

**Error**: `ModuleNotFoundError: No module named 'tensorflow'`

**Solution**:
```bash
pip install tensorflow>=2.13.0
```

### Issue: Sequence Data Not Found

**Error**: `FileNotFoundError: backend/ml_data/processed/train_sequences.npy`

**Solution**: Run Feature 004 data preparation first:
```bash
python backend/ml_data/scripts/1_preprocess.py
python backend/ml_data/scripts/2_feature_engineering.py
```

### Issue: Training is Very Slow

**Cause**: CPU training on large sequences

**Solutions**:
1. Verify GPU availability: `python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`
2. Install CUDA-enabled TensorFlow: `pip install tensorflow-gpu`
3. Reduce batch size: `--batch-size 16` (slower convergence but less memory)
4. Reduce max epochs: `--max-epochs 50` (risk of underfitting)

### Issue: Out of Memory (OOM)

**Error**: `ResourceExhaustedError: OOM when allocating tensor`

**Solutions**:
1. Reduce batch size: `--batch-size 16` or `--batch-size 8`
2. Close other applications to free RAM/VRAM
3. Use CPU instead of GPU (if GPU memory limited): `export CUDA_VISIBLE_DEVICES=-1`

### Issue: Model Accuracy Below 95%

**Cause**: Hyperparameters not optimal or data quality issues

**Analysis Steps**:
1. Check training history in metadata - is model overfitting (train accuracy >> val accuracy)?
2. Review loss curves - is validation loss decreasing or plateauing early?
3. Verify Feature 004 data quality - check for class imbalance, outliers
4. Consider hyperparameter tuning (future work - out of scope for MVP)

---

## Performance Benchmarks

Tested on standard laptop (Intel i7, 16 GB RAM, no GPU):

| Model   | Training Time | Test Accuracy | Inference Time (single) | Model Size |
|---------|---------------|---------------|-------------------------|------------|
| LSTM    | ~5-7 minutes  | ≥95%         | <100 ms                | 50-100 MB  |
| 1D-CNN  | ~3-5 minutes  | ≥95%         | <50 ms                 | 150-300 MB |

**Combined Training**: Both models train in <15 minutes (success criterion SC-002).

---

## Next Steps

1. **Feature 007**: Deploy trained models via Django REST API for real-time predictions
2. **Feature 008**: Implement ensemble methods (voting, stacking) combining LSTM + 1D-CNN
3. **Feature 009**: Add model explainability (attention visualizations, feature importance)
