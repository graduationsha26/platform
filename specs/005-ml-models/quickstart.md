# Quickstart: Machine Learning Models Training

**Feature**: 005-ml-models
**Date**: 2026-02-15
**Purpose**: Step-by-step guide for training, validating, and comparing ML models

## Prerequisites

Ensure Feature 004 (ML/DL Data Preparation) is complete:

```bash
# Verify Feature 004 outputs exist
ls backend/ml_data/processed/train_features.csv
ls backend/ml_data/processed/test_features.csv

# Expected output: Files should exist with proper structure
# train_features.csv: 446 rows × 31 columns (30 features + 1 label)
# test_features.csv: 110 rows × 31 columns
```

## Scenario 1: Train Random Forest Model (User Story 1 - MVP)

**Goal**: Train a Random Forest classifier with GridSearchCV, achieve ≥95% accuracy, export model and metadata

### Step 1.1: Run Training Script

```bash
# From repository root
cd "C:\Data from HDD\Graduation Project\Platform"

# Run Random Forest training (US1)
python backend/ml_models/scripts/train_random_forest.py

# Expected output:
# [INFO] Loading training data from backend/ml_data/processed/train_features.csv
# [INFO] Train set: 446 samples, 30 features
# [INFO] Test set: 110 samples, 30 features
# [INFO] Starting GridSearchCV with 16 parameter combinations...
# [INFO] Testing n_estimators=50, max_depth=10... CV score: 0.923
# [INFO] Testing n_estimators=50, max_depth=20... CV score: 0.941
# ... (progress for all 16 combinations)
# [INFO] Best parameters: {'n_estimators': 200, 'max_depth': 20}
# [INFO] Best CV score: 0.956 (±0.010)
# [INFO] Evaluating on test set...
# [INFO] Test Accuracy: 96.4%
# [INFO] Precision: 95.7%, Recall: 97.1%, F1-Score: 96.4%
# [OK] Model meets ≥95% accuracy threshold
# [INFO] Saving model to backend/ml_models/models/random_forest.pkl
# [INFO] Saving metadata to backend/ml_models/models/random_forest.json
# [INFO] Training completed in 127.3 seconds
```

### Step 1.2: Verify Outputs

```bash
# Check model files were created
ls backend/ml_models/models/random_forest.pkl
ls backend/ml_models/models/random_forest.json

# Inspect metadata (human-readable JSON)
cat backend/ml_models/models/random_forest.json

# Expected metadata structure (see data-model.md for full example)
# - hyperparameters: {"n_estimators": 200, "max_depth": 20, ...}
# - performance_metrics: {"accuracy": 0.964, "precision": 0.957, ...}
# - confusion_matrix: [[53, 3], [2, 52]]
# - training_info: {"timestamp": "2026-02-15T14:30:22", ...}
```

### Step 1.3: Validate Model Loading

```bash
# Test loading the saved model (optional validation script)
python -c "
import joblib
import json
import numpy as np

# Load model
model = joblib.load('backend/ml_models/models/random_forest.pkl')
print(f'Model type: {type(model).__name__}')
print(f'Model is fitted: {hasattr(model, \"classes_\")}')
print(f'Number of features: {model.n_features_in_}')
print(f'Classes: {model.classes_}')

# Load metadata
with open('backend/ml_models/models/random_forest.json') as f:
    metadata = json.load(f)
print(f'\\nMetadata - Accuracy: {metadata[\"performance_metrics\"][\"accuracy\"]:.3f}')
print(f'Best parameters: {metadata[\"hyperparameters\"][\"n_estimators\"]} trees, max_depth={metadata[\"hyperparameters\"][\"max_depth\"]}')

# Test prediction on dummy data (30 features)
X_dummy = np.random.randn(5, 30)  # 5 samples, 30 features
predictions = model.predict(X_dummy)
print(f'\\nTest predictions shape: {predictions.shape}')
print(f'Test predictions: {predictions}')
print('[OK] Model loaded and working correctly')
"
```

### Success Criteria (Scenario 1)

- ✅ Training script completes without errors
- ✅ Test accuracy ≥95% (SC-001)
- ✅ Training time <10 minutes (SC-002 - RF only, not combined)
- ✅ Model files created (random_forest.pkl and random_forest.json)
- ✅ Model can be loaded and used for predictions
- ✅ Metadata contains all required fields (hyperparameters, metrics, training_info)
- ✅ Confusion matrix shows balanced performance (no class has <90% recall - SC-005)

---

## Scenario 2: Train SVM Model (User Story 2)

**Goal**: Train an SVM classifier with RBF kernel, compare with Random Forest, export model

### Step 2.1: Run SVM Training Script

```bash
# Run SVM training (US2)
python backend/ml_models/scripts/train_svm.py

# Expected output:
# [INFO] Loading training data from backend/ml_data/processed/train_features.csv
# [INFO] Train set: 446 samples, 30 features
# [INFO] Test set: 110 samples, 30 features
# [INFO] Starting GridSearchCV with 16 parameter combinations...
# [INFO] Testing C=0.1, gamma=0.001... CV score: 0.876
# [INFO] Testing C=0.1, gamma=0.01... CV score: 0.921
# ... (progress for all 16 combinations)
# [INFO] Best parameters: {'C': 10, 'gamma': 0.01}
# [INFO] Best CV score: 0.962 (±0.012)
# [INFO] Evaluating on test set...
# [INFO] Test Accuracy: 97.3%
# [INFO] Precision: 96.8%, Recall: 97.8%, F1-Score: 97.3%
# [OK] Model meets ≥95% accuracy threshold
# [INFO] Saving model to backend/ml_models/models/svm_rbf.pkl
# [INFO] Saving metadata to backend/ml_models/models/svm_rbf.json
# [INFO] Training completed in 89.7 seconds
```

### Step 2.2: Verify SVM Outputs

```bash
# Check SVM model files
ls backend/ml_models/models/svm_rbf.pkl
ls backend/ml_models/models/svm_rbf.json

# Inspect SVM metadata
cat backend/ml_models/models/svm_rbf.json

# Expected SVM-specific metadata:
# - hyperparameters: {"C": 10, "gamma": 0.01, "kernel": "rbf", ...}
# - performance_metrics: {"accuracy": 0.973, ...}
```

### Success Criteria (Scenario 2)

- ✅ SVM training completes without errors
- ✅ Test accuracy ≥95% (SC-001)
- ✅ Training time <10 minutes (SC-002 - SVM only)
- ✅ Both RF and SVM combined training time <10 minutes (SC-002 combined)
- ✅ SVM model files created (svm_rbf.pkl and svm_rbf.json)
- ✅ SVM can be loaded and used for predictions
- ✅ SVM metadata includes kernel type ('rbf') in hyperparameters

---

## Scenario 3: Model Comparison Report (FR-012)

**Goal**: Generate side-by-side comparison of RF vs SVM performance

### Step 3.1: Run Comparison Script

```bash
# Generate comparison report (requires both models trained)
python backend/ml_models/scripts/compare_models.py

# Expected output:
# [INFO] Loading Random Forest model and metadata...
# [INFO] Loading SVM model and metadata...
# [INFO] Generating comparison report...
# [INFO] Report saved to backend/ml_models/models/comparison_report.txt
```

### Step 3.2: Review Comparison Report

```bash
# View the comparison report
cat backend/ml_models/models/comparison_report.txt

# Expected report format (see plan.md for full example):
# ======================================================================
# MODEL COMPARISON REPORT
# ======================================================================
# Generated: 2026-02-15 14:35:10
#
# Random Forest Classifier:
#   Accuracy:   96.4%
#   Precision:  95.7%
#   Recall:     97.1%
#   F1-Score:   96.4%
#   Training Time: 127.3 seconds
#
# SVM (RBF kernel):
#   Accuracy:   97.3%
#   Precision:  96.8%
#   Recall:     97.8%
#   F1-Score:   97.3%
#   Training Time: 89.7 seconds
#
# Best Model: SVM (RBF kernel) [97.3% accuracy]
# ======================================================================
```

### Success Criteria (Scenario 3)

- ✅ Comparison script loads both models successfully
- ✅ Report shows accuracy, precision, recall, F1-score for both models
- ✅ Report shows training time for both models
- ✅ Report identifies which model has higher accuracy
- ✅ Both models meet ≥95% accuracy threshold (SC-001)
- ✅ Combined training time <10 minutes (SC-002)

---

## Scenario 4: Reproducibility Validation (SC-004)

**Goal**: Verify that training with the same random seed produces identical results

### Step 4.1: Train Model Twice

```bash
# First training run
python backend/ml_models/scripts/train_random_forest.py
mv backend/ml_models/models/random_forest.json backend/ml_models/models/random_forest_run1.json

# Second training run (same script, same random_state=42)
python backend/ml_models/scripts/train_random_forest.py
mv backend/ml_models/models/random_forest.json backend/ml_models/models/random_forest_run2.json
```

### Step 4.2: Compare Results

```python
# Compare accuracy from both runs
import json

with open('backend/ml_models/models/random_forest_run1.json') as f:
    run1 = json.load(f)
with open('backend/ml_models/models/random_forest_run2.json') as f:
    run2 = json.load(f)

acc1 = run1['performance_metrics']['accuracy']
acc2 = run2['performance_metrics']['accuracy']

print(f'Run 1 Accuracy: {acc1:.6f}')
print(f'Run 2 Accuracy: {acc2:.6f}')
print(f'Difference: {abs(acc1 - acc2):.6f}')

# Success criterion: difference ≤ 0.0001 (0.01%)
assert abs(acc1 - acc2) <= 0.0001, "Reproducibility check failed"
print('[OK] Reproducibility validated: identical accuracy scores')
```

### Success Criteria (Scenario 4)

- ✅ Two training runs produce identical accuracy scores (within 0.01% - SC-004)
- ✅ Best hyperparameters are identical across runs
- ✅ Confusion matrix is identical across runs
- ✅ CV scores are identical across runs

---

## Scenario 5: Model Inference Performance (SC-003)

**Goal**: Verify that model loading and prediction happens in <1 second

### Step 5.1: Benchmark Model Loading

```python
import time
import joblib
import numpy as np

# Benchmark model loading
start = time.time()
model = joblib.load('backend/ml_models/models/random_forest.pkl')
load_time = time.time() - start

print(f'Model loading time: {load_time:.3f} seconds')
assert load_time < 1.0, f"Loading too slow: {load_time}s"
print('[OK] Model loads in <1 second')

# Benchmark single prediction
X_single = np.random.randn(1, 30)  # Single sample
start = time.time()
prediction = model.predict(X_single)
predict_time = time.time() - start

print(f'Single prediction time: {predict_time:.6f} seconds')
assert predict_time < 1.0, f"Prediction too slow: {predict_time}s"
print('[OK] Prediction completes in <1 second')

# Benchmark batch predictions (100 samples)
X_batch = np.random.randn(100, 30)
start = time.time()
predictions = model.predict(X_batch)
batch_time = time.time() - start

print(f'Batch prediction (100 samples): {batch_time:.3f} seconds')
print(f'Average per sample: {batch_time / 100:.6f} seconds')
```

### Success Criteria (Scenario 5)

- ✅ Model loads in <1 second (SC-003)
- ✅ Single prediction completes in <1 second (SC-003)
- ✅ Batch predictions are efficient (<1 second for 100 samples)

---

## Scenario 6: Model File Size Validation (Performance Targets)

**Goal**: Verify that exported model files are under size limits

### Step 6.1: Check File Sizes

```bash
# Check .pkl file sizes
ls -lh backend/ml_models/models/random_forest.pkl
ls -lh backend/ml_models/models/svm_rbf.pkl

# Check .json file sizes
ls -lh backend/ml_models/models/random_forest.json
ls -lh backend/ml_models/models/svm_rbf.json

# Expected sizes:
# random_forest.pkl: ~2-5 MB (depends on n_estimators and max_depth)
# svm_rbf.pkl: ~500 KB - 2 MB (depends on number of support vectors)
# random_forest.json: ~2-5 KB
# svm_rbf.json: ~2-5 KB
```

### Step 6.2: Validate Size Constraints

```python
import os

# Check .pkl file sizes (<10 MB limit)
rf_size = os.path.getsize('backend/ml_models/models/random_forest.pkl') / (1024 * 1024)  # MB
svm_size = os.path.getsize('backend/ml_models/models/svm_rbf.pkl') / (1024 * 1024)

print(f'Random Forest model size: {rf_size:.2f} MB')
print(f'SVM model size: {svm_size:.2f} MB')

assert rf_size < 10, f"RF model too large: {rf_size:.2f} MB"
assert svm_size < 10, f"SVM model too large: {svm_size:.2f} MB"
print('[OK] Model files under 10 MB limit')

# Check .json file sizes (<10 KB limit)
rf_json_size = os.path.getsize('backend/ml_models/models/random_forest.json') / 1024  # KB
svm_json_size = os.path.getsize('backend/ml_models/models/svm_rbf.json') / 1024

print(f'RF metadata size: {rf_json_size:.2f} KB')
print(f'SVM metadata size: {svm_json_size:.2f} KB')

assert rf_json_size < 10, f"RF metadata too large: {rf_json_size:.2f} KB"
assert svm_json_size < 10, f"SVM metadata too large: {svm_json_size:.2f} KB"
print('[OK] Metadata files under 10 KB limit')
```

### Success Criteria (Scenario 6)

- ✅ Random Forest .pkl file <10 MB (Performance Target)
- ✅ SVM .pkl file <10 MB (Performance Target)
- ✅ Both .json metadata files <10 KB (Performance Target)

---

## Scenario 7: Edge Case - Model Doesn't Reach 95% Accuracy

**Goal**: Verify graceful handling when no hyperparameter combination achieves threshold

### Simulated Test (Manual)

```python
# Simulate low-performing model (for testing error handling)
# In training script, if best_score < 0.95:
#   - Log warning: "[WARNING] Model achieved {accuracy:.1%}, below 95% threshold"
#   - Set meets_threshold: false in metadata
#   - Still export model (for analysis)
#   - Exit with status code 0 (not an error, just below target)

# Example metadata when threshold not met:
{
  "performance_metrics": {
    "accuracy": 0.927,  # Below 95%
    "meets_threshold": false,
    # ...
  }
}
```

### Success Criteria (Scenario 7)

- ✅ Training script completes (doesn't crash)
- ✅ Warning logged indicating threshold not met
- ✅ Model still exported with metadata flag `meets_threshold: false`
- ✅ Can analyze metadata to understand why accuracy is low (check confusion matrix, CV scores)

---

## Scenario 8: Edge Case - Missing Input Files

**Goal**: Verify clear error message when Feature 004 outputs are missing

### Simulated Test

```bash
# Temporarily rename input files to simulate missing data
mv backend/ml_data/processed/train_features.csv backend/ml_data/processed/train_features.csv.bak

# Try to run training
python backend/ml_models/scripts/train_random_forest.py

# Expected error message:
# [ERROR] Input file not found: backend/ml_data/processed/train_features.csv
# [ERROR] Please run Feature 004 data preparation pipeline first
# [ERROR] Expected outputs: train_features.csv, test_features.csv
# Exit code: 1

# Restore file
mv backend/ml_data/processed/train_features.csv.bak backend/ml_data/processed/train_features.csv
```

### Success Criteria (Scenario 8)

- ✅ Clear error message indicating missing file
- ✅ Guidance on how to fix (run Feature 004 first)
- ✅ Non-zero exit code (error, not success)

---

## Complete Workflow (All Scenarios)

**End-to-end validation**:

```bash
# 1. Train both models (US1 + US2)
python backend/ml_models/scripts/train_random_forest.py
python backend/ml_models/scripts/train_svm.py

# 2. Generate comparison report
python backend/ml_models/scripts/compare_models.py

# 3. Validate outputs
ls backend/ml_models/models/
# Expected files:
# - random_forest.pkl
# - random_forest.json
# - svm_rbf.pkl
# - svm_rbf.json
# - comparison_report.txt

# 4. Check all success criteria met
echo "Scenario 1 (RF training): ✅"
echo "Scenario 2 (SVM training): ✅"
echo "Scenario 3 (Comparison): ✅"
echo "Scenario 4 (Reproducibility): ✅ (run manual test)"
echo "Scenario 5 (Inference speed): ✅ (run manual test)"
echo "Scenario 6 (File sizes): ✅ (run manual test)"
echo "Scenario 7 (Edge case - low accuracy): ✅ (tested via code review)"
echo "Scenario 8 (Edge case - missing files): ✅ (tested via code review)"

echo ""
echo "Feature 005 ML Models Training: COMPLETE ✅"
echo "Ready for Feature 006 (DL model training) or Feature 007 (Model deployment)"
```

---

## Troubleshooting

### Issue: GridSearchCV runs out of memory

**Symptoms**: Process killed, "MemoryError" or "Killed (signal 9)"

**Solutions**:
1. Reduce parameter search space (fewer values in param_grid)
2. Reduce cross-validation folds (cv=3 instead of cv=5)
3. Use RandomizedSearchCV instead of GridSearchCV (samples parameter combinations)
4. Close other applications to free up RAM

### Issue: Training takes longer than 10 minutes

**Symptoms**: Script runs for >10 minutes, exceeds SC-002

**Solutions**:
1. Reduce parameter search space (fewer combinations to test)
2. Ensure n_jobs=-1 is set (use all CPU cores)
3. Reduce max_depth values in Random Forest search
4. For SVM, reduce C and gamma search space

### Issue: Model accuracy below 95%

**Symptoms**: Test accuracy <0.95, meets_threshold: false in metadata

**Analysis**:
1. Check confusion matrix - which class has low recall?
2. Check CV scores - high variance indicates overfitting
3. Review Feature 004 outputs - verify feature quality
4. Consider feature engineering improvements (future work)

**Not an error**: Model still exported for analysis, just flagged as below threshold

### Issue: Model files not found when loading

**Symptoms**: "FileNotFoundError: backend/ml_models/models/random_forest.pkl"

**Solutions**:
1. Verify training script ran successfully (check for .pkl and .json files)
2. Check current working directory (should be repository root)
3. Check file paths are absolute or relative to correct directory
4. Verify backend/ml_models/models/ directory exists

---

## Next Steps After Successful Training

1. **Feature 006**: Train deep learning models (LSTM, CNN) on sequence data from Feature 004
2. **Feature 007**: Deploy trained models via Django REST API for real-time predictions
3. **Feature 008**: Implement ensemble methods combining RF, SVM, and DL models
4. **Feature 009**: Add model explainability (SHAP values, feature importance)
5. **Feature 010**: Implement model monitoring and drift detection in production
