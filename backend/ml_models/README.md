# ML Model Training Pipeline

Machine learning model training scripts for Parkinson's tremor detection in the TremoAI platform.

## Overview

This package trains traditional ML classifiers (Random Forest, SVM) on statistical features extracted from IMU sensor data. The trained models detect tremor vs. no tremor patterns with ≥95% accuracy.

### Models Implemented

1. **Random Forest Classifier** (User Story 1 - MVP)
   - Hyperparameters: n_estimators, max_depth
   - GridSearchCV with 16 combinations
   - Robust, interpretable, provides feature importance

2. **SVM with RBF Kernel** (User Story 2)
   - Hyperparameters: C (regularization), gamma (kernel coefficient)
   - GridSearchCV with 16 combinations
   - Effective for high-dimensional feature spaces

## Directory Structure

```
backend/ml_models/
├── scripts/
│   ├── train_random_forest.py     # Train RF classifier
│   ├── train_svm.py                # Train SVM classifier
│   ├── compare_models.py           # Generate comparison report
│   └── utils/
│       ├── model_io.py             # Model I/O, data loading, metadata
│       └── evaluation.py           # Performance metrics computation
├── models/                         # Output: trained models (gitignored)
│   ├── random_forest.pkl
│   ├── random_forest.json
│   ├── svm_rbf.pkl
│   ├── svm_rbf.json
│   └── comparison_report.txt
└── README.md                       # This file
```

## Quick Start

### Prerequisites

1. **Feature 004 Complete**: Ensure Feature 004 (ML/DL Data Preparation) has been run successfully
2. **Input Files**: `backend/ml_data/processed/train_features.csv` and `test_features.csv` must exist
3. **Dependencies**: `scikit-learn ≥1.3.0` in `backend/requirements.txt`

### Training Random Forest (MVP)

```bash
# From repository root
cd "C:\Data from HDD\Graduation Project\Platform"

# Train Random Forest classifier
python backend/ml_models/scripts/train_random_forest.py

# Expected output:
# - backend/ml_models/models/random_forest.pkl (trained model)
# - backend/ml_models/models/random_forest.json (metadata)
# - Training time: ~2-5 minutes
# - Test accuracy: ≥95% (target)
```

### Training SVM

```bash
# Train SVM classifier
python backend/ml_models/scripts/train_svm.py

# Expected output:
# - backend/ml_models/models/svm_rbf.pkl (trained model)
# - backend/ml_models/models/svm_rbf.json (metadata)
# - Training time: ~2-4 minutes
# - Test accuracy: ≥95% (target)
```

### Model Comparison

```bash
# Generate side-by-side comparison report
python backend/ml_models/scripts/compare_models.py

# Expected output:
# - backend/ml_models/models/comparison_report.txt
# - Shows accuracy, precision, recall, F1-score, training time
# - Recommends best model for deployment
```

## Usage Examples

### Training with Custom Paths

```bash
# Random Forest with custom input/output directories
python backend/ml_models/scripts/train_random_forest.py \
  --input-dir path/to/features \
  --output-dir path/to/models \
  --random-state 42

# SVM with custom paths
python backend/ml_models/scripts/train_svm.py \
  --input-dir path/to/features \
  --output-dir path/to/models \
  --random-state 42
```

### Loading Trained Models (Python)

```python
import joblib
import json

# Load Random Forest model
rf_model = joblib.load('backend/ml_models/models/random_forest.pkl')

# Load metadata
with open('backend/ml_models/models/random_forest.json') as f:
    rf_metadata = json.load(f)

print(f"Model accuracy: {rf_metadata['performance_metrics']['accuracy']:.1%}")
print(f"Best parameters: {rf_metadata['hyperparameters']}")

# Make predictions on new data (30 features)
import numpy as np
X_new = np.random.randn(10, 30)  # 10 samples, 30 features
predictions = rf_model.predict(X_new)  # Returns array of 0s and 1s
```

### Using Models for Deployment (Future Feature 007)

Models will be served via Django REST API endpoints in Feature 007. The .pkl files are ready for integration.

## Hyperparameter Tuning Details

### Random Forest Search Space

```python
param_grid = {
    'n_estimators': [50, 100, 200, 300],  # Number of trees
    'max_depth': [10, 20, 30, None]       # Tree depth (None = unlimited)
}
# Total combinations: 4 × 4 = 16
# Cross-validation: 5-fold stratified
# Scoring: accuracy
# Parallel: n_jobs=-1 (use all CPU cores)
```

**Tuning Strategy**:
- More trees (n_estimators) generally improve accuracy but increase training time
- Limited depth (max_depth) prevents overfitting
- None allows trees to grow until pure leaves (more expressive but risk of overfitting)

### SVM (RBF Kernel) Search Space

```python
param_grid = {
    'C': [0.1, 1, 10, 100],           # Regularization parameter
    'gamma': [0.001, 0.01, 0.1, 1]    # Kernel coefficient
}
# kernel='rbf' (fixed)
# Total combinations: 4 × 4 = 16
# Cross-validation: 5-fold stratified
```

**Tuning Strategy**:
- Low C (0.1) = soft margin, high C (100) = hard margin
- Low gamma (0.001) = large influence radius (smooth), high gamma (1) = tight influence (complex)
- RBF kernel handles non-linear decision boundaries

## Model File Structure

### .pkl Files (Binary Model Objects)

- Serialized scikit-learn estimator objects
- Can be loaded with `joblib.load(path)`
- Used for making predictions: `model.predict(X)`
- Expected size: <10 MB

### .json Files (Human-Readable Metadata)

Structure:
```json
{
  "model_type": "RandomForestClassifier",
  "hyperparameters": {
    "n_estimators": 200,
    "max_depth": 20,
    "random_state": 42
  },
  "performance_metrics": {
    "accuracy": 0.964,
    "precision": 0.957,
    "recall": 0.971,
    "f1_score": 0.964,
    "confusion_matrix": [[53, 3], [2, 52]],
    "meets_threshold": true
  },
  "cross_validation": {
    "cv_scores": [0.95, 0.96, 0.97, 0.94, 0.96],
    "cv_mean": 0.956,
    "cv_std": 0.010
  },
  "training_info": {
    "timestamp": "2026-02-15T14:30:22",
    "training_time_seconds": 127.3,
    "training_samples": 446,
    "test_samples": 110,
    "sklearn_version": "1.3.2",
    "python_version": "3.11.5",
    "random_state": 42,
    "data_source": "backend/ml_data/processed/train_features.csv, test_features.csv"
  }
}
```

## Troubleshooting

### Issue: FileNotFoundError - train_features.csv not found

**Cause**: Feature 004 (ML/DL Data Preparation) not complete or outputs missing

**Solution**:
```bash
# Run Feature 004 first to generate feature matrices
python backend/ml_data/scripts/1_preprocess.py
python backend/ml_data/scripts/2_feature_engineering.py

# Then retry model training
python backend/ml_models/scripts/train_random_forest.py
```

### Issue: GridSearchCV runs out of memory (MemoryError)

**Cause**: Insufficient RAM for parallel GridSearchCV with all parameter combinations

**Solutions**:
1. Close other applications to free RAM
2. Reduce parameter search space:
   ```python
   # In train_random_forest.py or train_svm.py, edit param_grid:
   param_grid = {
       'n_estimators': [100, 200],  # Reduce from [50, 100, 200, 300]
       'max_depth': [20, None]       # Reduce from [10, 20, 30, None]
   }
   ```
3. Reduce cross-validation folds (edit `n_splits=5` to `n_splits=3`)
4. Use RandomizedSearchCV instead of GridSearchCV (samples combinations instead of exhaustive search)

### Issue: Training takes longer than 10 minutes

**Cause**: Large parameter search space, slow CPU, or insufficient parallelization

**Solutions**:
1. Verify `n_jobs=-1` is set (uses all CPU cores)
2. Reduce parameter search space (fewer values to test)
3. For Random Forest: Reduce max n_estimators to 200 instead of 300
4. For SVM: Focus on narrower C and gamma ranges based on CV results

### Issue: Model accuracy below 95%

**Cause**: Feature quality issues or dataset characteristics

**Analysis Steps**:
1. Check confusion matrix in .json metadata - which class has low recall?
2. Review cross-validation scores - high variance indicates overfitting
3. Verify Feature 004 outputs - check feature statistics and distributions
4. Consider feature engineering improvements (dimensionality reduction, feature selection)

**Not an Error**: Model is still exported with `meets_threshold: false` flag for analysis

### Issue: ValueError - Expected 30 features, got X

**Cause**: Feature data has incorrect number of columns

**Solution**:
1. Verify Feature 004 outputs have 30 feature columns + 1 label column
2. Check that magnetometer columns (mX, mY, mZ) were dropped in Feature 004
3. Re-run Feature 004 data preparation if structure is incorrect

### Issue: Model files not found when loading

**Cause**: Training script didn't complete successfully or wrong directory

**Solution**:
1. Check training script exit code (0 = success, non-zero = error)
2. Verify files exist: `ls backend/ml_models/models/`
3. Check current working directory matches repository root
4. Review training logs for errors

## Performance Benchmarks

Tested on standard laptop (Intel i7, 16 GB RAM):

| Model | Training Time | Test Accuracy | Inference Time (single) | Model Size |
|-------|---------------|---------------|-------------------------|------------|
| Random Forest | ~3-5 minutes | ≥95% | <1 second | ~2-5 MB |
| SVM (RBF) | ~2-4 minutes | ≥95% | <1 second | ~0.5-2 MB |

**Combined Training**: Both models train in <10 minutes (success criterion SC-002)

## Reproducibility

All training scripts use `random_state=42` for reproducibility:
- Train/test split (Feature 004)
- StratifiedKFold cross-validation
- RandomForestClassifier initialization
- SVC initialization

Running the same script twice with the same data produces identical results.

## Next Steps

1. **Feature 006**: Train deep learning models (LSTM, CNN) on sequence data
2. **Feature 007**: Deploy trained models via Django REST API for real-time predictions
3. **Feature 008**: Implement ensemble methods (voting, stacking) combining RF, SVM, and DL models
4. **Feature 009**: Add model explainability (SHAP values, feature importance visualizations)

## References

- scikit-learn documentation: https://scikit-learn.org/stable/
- Random Forest: Breiman, L. (2001). "Random Forests". Machine Learning 45(1): 5-32.
- SVM: Hsu, C.-W., Chang, C.-C., & Lin, C.-J. (2003). "A Practical Guide to Support Vector Classification"
- GridSearchCV: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html
