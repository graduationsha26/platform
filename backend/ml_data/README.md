# ML/DL Data Preparation Pipeline

This directory contains the data preprocessing pipeline for the TremoAI tremor detection dataset. It transforms raw IMU sensor data into three formats optimized for different ML/DL workflows.

## Overview

**Input**: `Dataset.csv` (27,995 samples of 6-axis IMU sensor data)

**Outputs**:
1. **Preprocessed Data** (Story 1): Clean, normalized train/test splits
2. **Feature Matrices** (Story 2): Statistical features for ML models
3. **Sequence Tensors** (Story 3): Time-windowed data for DL models

## Quick Start

### Prerequisites

```bash
# Install dependencies
cd backend
pip install numpy pandas scipy scikit-learn
```

### Run Complete Pipeline

```bash
# Run all three stages at once
python ml_data/scripts/run_all.py
```

### Run Individual Stages

```bash
# Story 1: Dataset Preprocessing
python ml_data/scripts/1_preprocess.py

# Story 2: Feature Engineering (requires Story 1 output)
python ml_data/scripts/2_feature_engineering.py

# Story 3: Sequence Preparation (requires Story 1 output)
python ml_data/scripts/3_sequence_preparation.py
```

## Directory Structure

```
ml_data/
├── scripts/                # Main preprocessing scripts
│   ├── 1_preprocess.py    # Clean, normalize, split (Story 1)
│   ├── 2_feature_engineering.py  # Extract ML features (Story 2)
│   ├── 3_sequence_preparation.py # Create DL sequences (Story 3)
│   └── run_all.py         # Master script
├── utils/                  # Shared utilities
│   ├── data_loader.py     # CSV loading and validation
│   ├── windowing.py       # Sliding window functions
│   ├── feature_extractors.py  # Statistical calculations
│   └── validators.py      # Data integrity checks
├── processed/             # Output directory (gitignored)
│   ├── train_normalized.npy
│   ├── test_normalized.npy
│   ├── train_features.csv
│   ├── test_features.csv
│   ├── train_sequences.npy
│   ├── test_sequences.npy
│   └── normalization_params.json
└── README.md              # This file
```

## Pipeline Stages

### Stage 1: Dataset Preprocessing (P1 - MVP)

**Script**: `1_preprocess.py`

**Actions**:
- Load Dataset.csv (27,995 samples)
- Drop disabled magnetometer columns (mX, mY, mZ)
- Handle missing values (drop if <5%, impute if >=5%)
- Split 80/20 stratified (train: 22,396, test: 5,599)
- Normalize per axis using z-score (mean=0, std=1)
- Save train/test .npy files + normalization params JSON

**Outputs**:
- `processed/train_normalized.npy` - Training data (22,396 × 6)
- `processed/test_normalized.npy` - Test data (5,599 × 6)
- `processed/train_labels.npy` - Training labels
- `processed/test_labels.npy` - Test labels
- `processed/normalization_params.json` - Mean/std per axis
- `processed/preprocessing_report.txt` - Statistics report

### Stage 2: Feature Engineering (P2)

**Script**: `2_feature_engineering.py`

**Actions**:
- Load preprocessed data from Story 1
- Create sliding windows (100 samples, 50% overlap)
- Extract 5 features per axis: RMS, mean, std, skewness, kurtosis
- Generate feature matrix (30 features + label)
- Save as CSV for ML model consumption

**Outputs**:
- `processed/train_features.csv` - Training features (~447 windows × 31)
- `processed/test_features.csv` - Test features (~111 windows × 31)

**Feature Columns** (30 total):
- 6 axes × 5 features = 30
- Axes: aX, aY, aZ, gX, gY, gZ
- Features: RMS, mean, std, skewness, kurtosis
- Plus 1 label column (0 or 1)

### Stage 3: Sequence Preparation (P3)

**Script**: `3_sequence_preparation.py`

**Actions**:
- Load preprocessed data from Story 1
- Create sliding windows (128 samples, 50% overlap)
- Reshape to 3D tensors (num_windows, 128, 6)
- Assign labels via majority voting
- Save as numpy binary for DL frameworks

**Outputs**:
- `processed/train_sequences.npy` - Training sequences (~349, 128, 6)
- `processed/test_sequences.npy` - Test sequences (~87, 128, 6)
- `processed/train_seq_labels.npy` - Training labels
- `processed/test_seq_labels.npy` - Test labels

## Usage Examples

### Load Preprocessed Data

```python
import numpy as np

# Load normalized data
X_train = np.load('ml_data/processed/train_normalized.npy')
y_train = np.load('ml_data/processed/train_labels.npy')

print(f"Train shape: {X_train.shape}")  # (22396, 6)
print(f"Labels shape: {y_train.shape}")  # (22396,)
```

### Train ML Model with Features

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Load feature matrix
train_df = pd.read_csv('ml_data/processed/train_features.csv')
X_train = train_df.iloc[:, :-1].values  # 30 features
y_train = train_df.iloc[:, -1].values   # labels

# Train model
rf = RandomForestClassifier(n_estimators=100)
rf.fit(X_train, y_train)
```

### Train DL Model with Sequences

```python
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Load sequences
X_train = np.load('ml_data/processed/train_sequences.npy')  # (349, 128, 6)
y_train = np.load('ml_data/processed/train_seq_labels.npy')

# Define LSTM model
model = Sequential([
    LSTM(64, input_shape=(128, 6)),
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.fit(X_train, y_train, epochs=10, batch_size=32)
```

## Validation

Run validation scenarios from `specs/004-ml-data-prep/quickstart.md`:

```bash
# Scenario 1: Verify data integrity (no leakage)
python -c "
import numpy as np
X_train = np.load('ml_data/processed/train_normalized.npy')
X_test = np.load('ml_data/processed/test_normalized.npy')
train_set = set(map(tuple, X_train))
test_set = set(map(tuple, X_test))
overlap = train_set.intersection(test_set)
print(f'Overlapping samples: {len(overlap)} (should be 0)')
"

# Scenario 2: Verify class distribution
python -c "
import numpy as np
y_train = np.load('ml_data/processed/train_labels.npy')
y_test = np.load('ml_data/processed/test_labels.npy')
print(f'Train: Class 0: {(y_train==0).mean()*100:.1f}%, Class 1: {(y_train==1).mean()*100:.1f}%')
print(f'Test:  Class 0: {(y_test==0).mean()*100:.1f}%, Class 1: {(y_test==1).mean()*100:.1f}%')
"

# Scenario 3: Verify normalization
python -c "
import numpy as np
X_train = np.load('ml_data/processed/train_normalized.npy')
means = X_train.mean(axis=0)
stds = X_train.std(axis=0)
print('Per-axis statistics:')
for i, (m, s) in enumerate(zip(means, stds)):
    print(f'  Axis {i}: mean={m:.4f}, std={s:.4f}')
"
```

## Troubleshooting

### "Dataset.csv not found"

```bash
# Verify file exists at project root
ls "../Dataset.csv"

# If missing, ensure Dataset.csv is in the correct location
```

### "ImportError: No module named 'pandas'"

```bash
# Install missing dependencies
pip install numpy pandas scipy scikit-learn
```

### "Memory Error"

The pipeline processes the full dataset in memory (~28K samples). If you encounter memory issues:
- Close other applications
- Reduce batch size in scripts (if implemented)
- Use a machine with more RAM

### "Outputs are different on each run"

Verify random seed is set to 42 in all scripts. The pipeline should be fully reproducible.

## Performance

**Expected Processing Times** (Intel i5 / 16GB RAM):
- Story 1 (Preprocessing): 2-3 seconds
- Story 2 (Feature Engineering): 3-4 seconds
- Story 3 (Sequence Preparation): 1-2 seconds
- **Total Pipeline**: 7-9 seconds

**File Sizes**:
- Preprocessed data: ~1.5 MB
- Feature matrices: ~0.65 MB
- Sequence tensors: ~27.5 MB
- **Total Output**: ~37 MB

## Next Steps

After running this pipeline:

1. **Train ML Models** (Feature 005): Use feature matrices for Random Forest, SVM, XGBoost
2. **Train DL Models** (Feature 006): Use sequence tensors for LSTM, CNN, hybrid models
3. **Model Evaluation**: Compare ML vs DL performance on tremor classification
4. **Model Deployment**: Serve best model via Django REST API

## References

- Specification: `specs/004-ml-data-prep/spec.md`
- Implementation Plan: `specs/004-ml-data-prep/plan.md`
- Validation Scenarios: `specs/004-ml-data-prep/quickstart.md`
- Task Breakdown: `specs/004-ml-data-prep/tasks.md`
