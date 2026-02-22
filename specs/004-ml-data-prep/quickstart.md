# Quickstart: ML/DL Data Preparation

**Feature**: 004-ml-data-prep
**Date**: 2026-02-15
**Purpose**: Usage examples and validation scenarios for data preparation pipeline

## Prerequisites

1. **Dataset**: Ensure Dataset.csv is at project root
   ```bash
   ls "C:\Data from HDD\Graduation Project\Platform\Dataset.csv"
   # Should show: Dataset.csv (8 MB, 27996 lines)
   ```

2. **Dependencies**: Install required Python libraries
   ```bash
   cd backend
   pip install numpy>=1.24.0 pandas>=2.0.0 scipy>=1.10.0 scikit-learn>=1.3.0
   ```

3. **Directory Structure**: Create output directory
   ```bash
   mkdir -p backend/ml_data/processed
   ```

---

## Quick Start (Run All Stages)

**Master Script** (recommended):
```bash
cd backend/ml_data/scripts
python run_all.py
```

**Expected Output**:
```
Stage 1: Dataset Preprocessing...
  [INFO] Loading Dataset.csv (27,995 samples)
  [INFO] Dropped magnetometer columns (mX, mY, mZ)
  [INFO] No null values detected
  [INFO] Splitting 80/20 stratified (random_state=42)
  [INFO] Train: 22,396 samples (45.4% class 0)
  [INFO] Test: 5,599 samples (45.4% class 0)
  [INFO] Fitting StandardScaler on training set
  [INFO] Normalizing train and test sets
  [INFO] Saved preprocessed data to backend/ml_data/processed/
  ✓ Story 1 complete (elapsed: 2.3s)

Stage 2: Feature Engineering...
  [INFO] Loading preprocessed train data (22,396 samples)
  [INFO] Creating sliding windows (size=100, stride=50)
  [INFO] Generated 447 windows from train set
  [INFO] Extracting 5 features per axis (RMS, mean, std, skew, kurt)
  [INFO] Feature matrix shape: (447, 30)
  [INFO] Assigning window labels via majority voting
  [INFO] Saved train_features.csv (447 windows, 30 features)
  [INFO] Processing test set (111 windows)
  [INFO] Saved test_features.csv
  ✓ Story 2 complete (elapsed: 3.1s)

Stage 3: Sequence Preparation...
  [INFO] Loading preprocessed train data (22,396 samples)
  [INFO] Creating sliding windows (size=128, stride=64)
  [INFO] Generated 349 sequences from train set
  [INFO] Reshaping to 3D tensor: (349, 128, 6)
  [INFO] Assigning sequence labels via majority voting
  [INFO] Saved train_sequences.npy
  [INFO] Processing test set (87 sequences)
  [INFO] Saved test_sequences.npy
  ✓ Story 3 complete (elapsed: 1.8s)

Pipeline complete! Total time: 7.2s
Check outputs in: backend/ml_data/processed/
```

---

## Individual Stage Execution

### Story 1: Dataset Preprocessing

```bash
cd backend/ml_data/scripts
python 1_preprocess.py
```

**Outputs**:
- `processed/train_normalized.npy` (22,396 × 6)
- `processed/test_normalized.npy` (5,599 × 6)
- `processed/train_labels.npy` (22,396,)
- `processed/test_labels.npy` (5,599,)
- `processed/normalization_params.json`
- `processed/preprocessing_report.txt`

**Validation**:
```python
import numpy as np
import json

# Load and check shapes
X_train = np.load('backend/ml_data/processed/train_normalized.npy')
X_test = np.load('backend/ml_data/processed/test_normalized.npy')
y_train = np.load('backend/ml_data/processed/train_labels.npy')
y_test = np.load('backend/ml_data/processed/test_labels.npy')

print(f"Train data: {X_train.shape}")  # Should be (22396, 6)
print(f"Test data: {X_test.shape}")    # Should be (5599, 6)
print(f"Train labels: {y_train.shape}") # Should be (22396,)
print(f"Test labels: {y_test.shape}")   # Should be (5599,)

# Check normalization (mean ≈ 0, std ≈ 1 per axis)
print(f"Train mean per axis: {X_train.mean(axis=0)}")  # Should be close to [0,0,0,0,0,0]
print(f"Train std per axis: {X_train.std(axis=0)}")     # Should be close to [1,1,1,1,1,1]

# Check class distribution
print(f"Train class 0: {(y_train == 0).sum()} ({(y_train == 0).mean()*100:.1f}%)")
print(f"Train class 1: {(y_train == 1).sum()} ({(y_train == 1).mean()*100:.1f}%)")

# Load normalization parameters
with open('backend/ml_data/processed/normalization_params.json', 'r') as f:
    params = json.load(f)
print(f"Normalization method: {params['method']}")
print(f"Fitted on: {params['fitted_on']}")
```

---

### Story 2: Feature Engineering

**Prerequisites**: Story 1 outputs must exist

```bash
cd backend/ml_data/scripts
python 2_feature_engineering.py
```

**Outputs**:
- `processed/train_features.csv` (~447 rows × 31 columns)
- `processed/test_features.csv` (~111 rows × 31 columns)

**Validation**:
```python
import pandas as pd
import numpy as np

# Load feature matrices
train_df = pd.read_csv('backend/ml_data/processed/train_features.csv')
test_df = pd.read_csv('backend/ml_data/processed/test_features.csv')

print(f"Train features: {train_df.shape}")  # Should be (~447, 31)
print(f"Test features: {test_df.shape}")    # Should be (~111, 31)

# Check column names (30 features + 1 label)
print(f"Columns: {train_df.columns.tolist()}")
# Expected: ['RMS_aX', 'mean_aX', 'std_aX', 'skew_aX', 'kurt_aX', ... 'label']

# Check for missing values
print(f"Missing values: {train_df.isnull().sum().sum()}")  # Should be 0

# Check label distribution
print(f"Train labels: {train_df['label'].value_counts()}")

# Verify feature ranges (no extreme outliers)
print(train_df.describe())

# Extract features and labels for ML
X_train = train_df.iloc[:, :-1].values  # All columns except last
y_train = train_df.iloc[:, -1].values   # Last column
print(f"X_train shape: {X_train.shape}")  # (N, 30)
print(f"y_train shape: {y_train.shape}")  # (N,)
```

**Train a Quick ML Model**:
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load data
train_df = pd.read_csv('backend/ml_data/processed/train_features.csv')
test_df = pd.read_csv('backend/ml_data/processed/test_features.csv')

X_train = train_df.iloc[:, :-1].values
y_train = train_df.iloc[:, -1].values
X_test = test_df.iloc[:, :-1].values
y_test = test_df.iloc[:, -1].values

# Train Random Forest
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# Evaluate
train_acc = accuracy_score(y_train, rf.predict(X_train))
test_acc = accuracy_score(y_test, rf.predict(X_test))

print(f"Train Accuracy: {train_acc:.3f}")
print(f"Test Accuracy: {test_acc:.3f}")
print("\nClassification Report:")
print(classification_report(y_test, rf.predict(X_test)))
```

---

### Story 3: Sequence Preparation

**Prerequisites**: Story 1 outputs must exist

```bash
cd backend/ml_data/scripts
python 3_sequence_preparation.py
```

**Outputs**:
- `processed/train_sequences.npy` (~349, 128, 6)
- `processed/test_sequences.npy` (~87, 128, 6)
- `processed/train_seq_labels.npy` (~349,)
- `processed/test_seq_labels.npy` (~87,)

**Validation**:
```python
import numpy as np

# Load sequence tensors
X_train = np.load('backend/ml_data/processed/train_sequences.npy')
X_test = np.load('backend/ml_data/processed/test_sequences.npy')
y_train = np.load('backend/ml_data/processed/train_seq_labels.npy')
y_test = np.load('backend/ml_data/processed/test_seq_labels.npy')

print(f"Train sequences: {X_train.shape}")  # Should be (~349, 128, 6)
print(f"Test sequences: {X_test.shape}")    # Should be (~87, 128, 6)
print(f"Train labels: {y_train.shape}")     # Should be (~349,)
print(f"Test labels: {y_test.shape}")       # Should be (~87,)

# Check for NaN/Inf
print(f"NaN values: {np.isnan(X_train).sum()}")    # Should be 0
print(f"Inf values: {np.isinf(X_train).sum()}")    # Should be 0

# Check value ranges (normalized data)
print(f"Min value: {X_train.min()}")  # Typically around -5
print(f"Max value: {X_train.max()}")  # Typically around +5
print(f"Mean value: {X_train.mean()}")  # Should be close to 0

# Check label distribution
unique, counts = np.unique(y_train, return_counts=True)
print(f"Label distribution: {dict(zip(unique, counts))}")
```

**Train a Quick LSTM Model** (TensorFlow):
```python
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

# Load sequences
X_train = np.load('backend/ml_data/processed/train_sequences.npy')
X_test = np.load('backend/ml_data/processed/test_sequences.npy')
y_train = np.load('backend/ml_data/processed/train_seq_labels.npy')
y_test = np.load('backend/ml_data/processed/test_seq_labels.npy')

# Define LSTM model
model = Sequential([
    LSTM(64, input_shape=(128, 6), return_sequences=True),
    Dropout(0.3),
    LSTM(32),
    Dropout(0.3),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train with early stopping
early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=50,
    batch_size=32,
    callbacks=[early_stop],
    verbose=1
)

# Evaluate
train_loss, train_acc = model.evaluate(X_train, y_train, verbose=0)
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)

print(f"Train Accuracy: {train_acc:.3f}")
print(f"Test Accuracy: {test_acc:.3f}")
```

---

## Validation Scenarios

### Scenario 1: Verify Data Integrity (No Leakage)

**Purpose**: Ensure no samples appear in both train and test sets

```python
import numpy as np

# Load preprocessed data
X_train = np.load('backend/ml_data/processed/train_normalized.npy')
X_test = np.load('backend/ml_data/processed/test_normalized.npy')

# Convert to tuples for set operations
train_tuples = set(map(tuple, X_train))
test_tuples = set(map(tuple, X_test))

# Check intersection (should be empty)
overlap = train_tuples.intersection(test_tuples)
print(f"Overlapping samples: {len(overlap)}")  # Should be 0

if len(overlap) == 0:
    print("✓ No data leakage detected!")
else:
    print("✗ WARNING: Data leakage detected!")
```

### Scenario 2: Verify Class Distribution

**Purpose**: Confirm stratification preserved class balance

```python
import numpy as np

y_train = np.load('backend/ml_data/processed/train_labels.npy')
y_test = np.load('backend/ml_data/processed/test_labels.npy')

# Calculate class distribution
train_class0_pct = (y_train == 0).mean() * 100
train_class1_pct = (y_train == 1).mean() * 100
test_class0_pct = (y_test == 0).mean() * 100
test_class1_pct = (y_test == 1).mean() * 100

print(f"Train: Class 0: {train_class0_pct:.1f}%, Class 1: {train_class1_pct:.1f}%")
print(f"Test:  Class 0: {test_class0_pct:.1f}%, Class 1: {test_class1_pct:.1f}%")

# Check if within tolerance (±2%)
tolerance = 2.0
diff = abs(train_class0_pct - test_class0_pct)
if diff <= tolerance:
    print(f"✓ Class distribution preserved (diff: {diff:.2f}%)")
else:
    print(f"✗ WARNING: Class imbalance detected (diff: {diff:.2f}%)")
```

### Scenario 3: Verify Normalization

**Purpose**: Confirm z-score normalization applied correctly

```python
import numpy as np

X_train = np.load('backend/ml_data/processed/train_normalized.npy')

# Check mean and std per axis
means = X_train.mean(axis=0)
stds = X_train.std(axis=0)

print("Per-axis statistics:")
for i, (m, s) in enumerate(zip(means, stds)):
    print(f"  Axis {i}: mean={m:.4f}, std={s:.4f}")

# Verify close to 0 mean, 1 std (within floating point tolerance)
mean_ok = np.allclose(means, 0, atol=1e-10)
std_ok = np.allclose(stds, 1, atol=1e-2)

if mean_ok and std_ok:
    print("✓ Normalization correct (mean≈0, std≈1)")
else:
    print("✗ WARNING: Normalization may be incorrect")
```

### Scenario 4: Verify Reproducibility

**Purpose**: Confirm same random seed produces identical output

```bash
# Run preprocessing twice
cd backend/ml_data/scripts
python 1_preprocess.py  # First run
cp processed/train_normalized.npy processed/train_normalized_v1.npy

python 1_preprocess.py  # Second run
cp processed/train_normalized.npy processed/train_normalized_v2.npy

# Compare outputs (should be identical)
python -c "
import numpy as np
v1 = np.load('processed/train_normalized_v1.npy')
v2 = np.load('processed/train_normalized_v2.npy')
identical = np.array_equal(v1, v2)
print(f'Outputs identical: {identical}')
if identical:
    print('✓ Reproducibility confirmed')
else:
    print('✗ WARNING: Non-reproducible results')
"
```

### Scenario 5: Feature Matrix Compatibility with scikit-learn

**Purpose**: Verify feature matrices can be loaded and used with scikit-learn

```python
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier

# Load feature matrix
train_df = pd.read_csv('backend/ml_data/processed/train_features.csv')
X = train_df.iloc[:, :-1].values
y = train_df.iloc[:, -1].values

# Run cross-validation (should complete without errors)
rf = RandomForestClassifier(n_estimators=10, random_state=42)
scores = cross_val_score(rf, X, y, cv=5)

print(f"Cross-validation scores: {scores}")
print(f"Mean accuracy: {scores.mean():.3f} (+/- {scores.std()*2:.3f})")
print("✓ Feature matrix compatible with scikit-learn")
```

### Scenario 6: Sequence Tensor Compatibility with TensorFlow

**Purpose**: Verify sequence tensors can be loaded and used with TensorFlow

```python
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Load sequences
X_train = np.load('backend/ml_data/processed/train_sequences.npy')
y_train = np.load('backend/ml_data/processed/train_seq_labels.npy')

# Define simple LSTM model (should accept input shape)
model = Sequential([
    LSTM(16, input_shape=(128, 6)),
    Dense(1, activation='sigmoid')
])
model.compile(optimizer='adam', loss='binary_crossentropy')

# Test forward pass (should complete without errors)
try:
    model.fit(X_train[:32], y_train[:32], epochs=1, verbose=0)
    print("✓ Sequence tensor compatible with TensorFlow/Keras")
except Exception as e:
    print(f"✗ ERROR: {e}")
```

### Scenario 7: Verify File Sizes

**Purpose**: Confirm all output files created and within expected size ranges

```python
import os

output_dir = 'backend/ml_data/processed/'
expected_files = {
    'train_normalized.npy': (0.8, 1.2),      # ~1 MB
    'test_normalized.npy': (0.2, 0.3),       # ~0.25 MB
    'train_labels.npy': (0.15, 0.25),        # ~0.2 MB
    'test_labels.npy': (0.04, 0.06),         # ~0.05 MB
    'train_features.csv': (0.4, 0.6),        # ~0.5 MB
    'test_features.csv': (0.1, 0.2),         # ~0.15 MB
    'train_sequences.npy': (20, 24),         # ~22 MB
    'test_sequences.npy': (5, 6),            # ~5.5 MB
    'train_seq_labels.npy': (0.002, 0.004),  # ~0.003 MB
    'test_seq_labels.npy': (0.0005, 0.002),  # ~0.001 MB
    'normalization_params.json': (0.0005, 0.002),
    'preprocessing_report.txt': (0.005, 0.02)
}

print("File size validation:")
for filename, (min_mb, max_mb) in expected_files.items():
    filepath = os.path.join(output_dir, filename)
    if os.path.exists(filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        status = "✓" if min_mb <= size_mb <= max_mb else "✗"
        print(f"{status} {filename}: {size_mb:.2f} MB (expected {min_mb}-{max_mb} MB)")
    else:
        print(f"✗ {filename}: NOT FOUND")
```

---

## Troubleshooting

### Issue: "Dataset.csv not found"

```bash
# Check if file exists
ls "C:\Data from HDD\Graduation Project\Platform\Dataset.csv"

# If missing, verify path or re-download from Kaggle
```

### Issue: "ImportError: No module named 'numpy'"

```bash
# Install missing dependencies
pip install numpy pandas scipy scikit-learn
```

### Issue: "MemoryError during windowing"

```python
# If dataset is too large for RAM, process in batches
# Modify scripts to use batch processing instead of loading all at once
# (Unlikely with 28K samples, but relevant for larger datasets)
```

### Issue: "Values not normalized (mean != 0)"

- Check that normalization was fitted on train set, not test set
- Verify StandardScaler is applied correctly
- Re-run preprocessing with clean slate

### Issue: "Class imbalance > 2% difference"

- Check random_state is set correctly (42)
- Verify stratify=y is used in train_test_split
- Re-run preprocessing to regenerate split

---

## Performance Benchmarks

**Expected Processing Times** (on Intel i5 / 16GB RAM):

| Stage                     | Time    | Throughput         |
|---------------------------|---------|---------------------|
| Story 1: Preprocessing    | 2-3s    | ~10K samples/sec    |
| Story 2: Feature Eng.     | 3-4s    | ~150 windows/sec    |
| Story 3: Sequence Prep.   | 1-2s    | ~200 windows/sec    |
| **Total Pipeline**        | **7-9s**| -                   |

**File I/O Times**:

| Operation                  | Time    |
|----------------------------|---------|
| Load Dataset.csv           | 0.5s    |
| Save .npy files            | 0.1-0.3s|
| Save .csv files            | 0.2-0.4s|
| Load .npy files            | 0.01s   |
| Load .csv files            | 0.1s    |

---

## Next Steps

After running this pipeline, you're ready to:

1. **Train ML Models** (Feature 005): Use feature matrices for Random Forest, SVM, XGBoost
2. **Train DL Models** (Feature 006): Use sequence tensors for LSTM, CNN, hybrid models
3. **Model Evaluation**: Compare ML vs DL performance on tremor classification
4. **Model Deployment**: Serve best model via Django REST API for real-time inference

**Command to proceed**:
```bash
# After data prep complete, move to model training
/speckit.specify "ML Model Training - Train and evaluate Random Forest, SVM, XGBoost"
```
