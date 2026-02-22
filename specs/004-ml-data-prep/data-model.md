# Data Model: ML/DL Data Preparation

**Feature**: 004-ml-data-prep
**Date**: 2026-02-15
**Purpose**: Define data structures and entities for preprocessing pipeline

## Overview

This feature transforms raw IMU sensor data through three stages, producing distinct data formats optimized for different ML/DL workflows. Unlike typical features with database models, this pipeline works with file-based data structures.

**Data Flow**:
```
Raw Dataset (CSV)
    ↓
[Story 1: Preprocessing]
    ↓
Preprocessed Dataset (.npy) ──────┬─→ [Story 2] → Feature Matrix (CSV)
                                  └─→ [Story 3] → Sequence Tensor (.npy)
```

---

## Entity 1: Raw Dataset (Input)

**Source**: Dataset.csv (Kaggle tremor detection dataset)
**Format**: CSV file
**Location**: Project root (C:\Data from HDD\Graduation Project\Platform\Dataset.csv)

### Structure

| Column | Type    | Description                           | Value Range       | Notes                    |
|--------|---------|---------------------------------------|-------------------|--------------------------|
| aX     | int     | Accelerometer X-axis (milli-g)        | -32768 to 32767   | Active sensor            |
| aY     | int     | Accelerometer Y-axis (milli-g)        | -32768 to 32767   | Active sensor            |
| aZ     | int     | Accelerometer Z-axis (milli-g)        | -32768 to 32767   | Active sensor            |
| gX     | int     | Gyroscope X-axis (deg/s * 131)        | -32768 to 32767   | Active sensor            |
| gY     | int     | Gyroscope Y-axis (deg/s * 131)        | -32768 to 32767   | Active sensor            |
| gZ     | int     | Gyroscope Z-axis (deg/s * 131)        | -32768 to 32767   | Active sensor            |
| mX     | int     | Magnetometer X-axis                   | -1                | Disabled (all -1)        |
| mY     | int     | Magnetometer Y-axis                   | -1                | Disabled (all -1)        |
| mZ     | int     | Magnetometer Z-axis                   | -1                | Disabled (all -1)        |
| Result | int     | Binary label (tremor classification)  | 0 or 1            | 0=no tremor, 1=tremor    |

### Properties

- **Total Samples**: 27,995 (including 1 header row → 27,995 data rows)
- **Sampling Rate**: 100 Hz (confirmed in spec clarifications)
- **Class Distribution**:
  - Class 0 (no tremor): 12,749 samples (45.4%)
  - Class 1 (tremor): 15,246 samples (54.6%)
- **File Size**: ~8 MB (text format)
- **Integrity**: No null values, all numeric columns

### Preprocessing Actions

1. **Drop columns**: mX, mY, mZ (all values are -1)
2. **Separate**: Features (6 sensor axes) from labels (Result column)
3. **Validate**: Check for nulls, outliers, data types
4. **Output**: 27,995 samples × 6 axes + 27,995 labels

---

## Entity 2: Preprocessed Dataset (Story 1 Output)

**Purpose**: Clean, normalized, split data ready for windowing
**Format**: NumPy binary (.npy files)
**Location**: backend/ml_data/processed/

### Files

| File                      | Shape              | dtype   | Description                                    |
|---------------------------|--------------------|---------|------------------------------------------------|
| train_normalized.npy      | (22396, 6)         | float64 | Training set, normalized sensor values         |
| test_normalized.npy       | (5599, 6)          | float64 | Test set, normalized sensor values             |
| train_labels.npy          | (22396,)           | int64   | Training labels (0 or 1)                       |
| test_labels.npy           | (5599,)            | int64   | Test labels (0 or 1)                           |
| normalization_params.json | -                  | JSON    | Mean and std per axis (6 means, 6 stds)        |
| preprocessing_report.txt  | -                  | Text    | Statistics report (counts, distributions, etc.)|

### Normalization Parameters (JSON)

```json
{
  "method": "z-score",
  "axes": ["aX", "aY", "aZ", "gX", "gY", "gZ"],
  "mean": {
    "aX": -1234.56,
    "aY": 14567.89,
    "aZ": -6789.01,
    "gX": 4012.34,
    "gY": 123.45,
    "gZ": -456.78
  },
  "std": {
    "aX": 1987.65,
    "aY": 432.10,
    "aZ": 3210.98,
    "gX": 876.54,
    "gY": 1234.56,
    "gZ": 2345.67
  },
  "fitted_on": "train",
  "train_samples": 22396,
  "test_samples": 5599,
  "random_state": 42
}
```

### Properties

- **Normalization**: Z-score (mean=0, std=1) per axis, fitted on train only
- **Split Ratio**: 80/20 (train/test)
- **Stratification**: Class distribution preserved (±0.5% tolerance)
- **Random Seed**: 42 (reproducibility)
- **Value Range**: Typically [-5, +5] after normalization (99.7% within 3 std devs)

### Validation Rules

- ✅ train_normalized.shape[0] + test_normalized.shape[0] = 27995
- ✅ No NaN or Inf values in any array
- ✅ train_labels and test_labels contain only {0, 1}
- ✅ Class distribution: train ~45% class 0, test ~45% class 0 (within 2%)
- ✅ All arrays are C-contiguous (efficient for subsequent processing)

---

## Entity 3: Feature Matrix (Story 2 Output)

**Purpose**: Statistical features extracted from time windows for traditional ML models
**Format**: CSV files
**Location**: backend/ml_data/processed/

### Files

| File               | Shape           | Description                                     |
|--------------------|-----------------|-------------------------------------------------|
| train_features.csv | (~447, 31)      | Training windows with 30 features + 1 label     |
| test_features.csv  | (~111, 31)      | Test windows with 30 features + 1 label         |

**Window Count Calculation**:
- Train: (22396 - 100) // 50 + 1 = 447 windows
- Test: (5599 - 100) // 50 + 1 = 111 windows
- Actual counts may vary slightly due to edge handling

### Schema

**Columns (31 total)**:

| Column Index | Column Name | Type    | Description                          | Value Range    |
|--------------|-------------|---------|--------------------------------------|----------------|
| 0            | RMS_aX      | float64 | Root Mean Square of aX in window     | [0, ∞)         |
| 1            | mean_aX     | float64 | Mean of aX in window                 | [-5, +5]       |
| 2            | std_aX      | float64 | Standard deviation of aX in window   | [0, ∞)         |
| 3            | skew_aX     | float64 | Skewness of aX in window             | (-∞, +∞)       |
| 4            | kurt_aX     | float64 | Kurtosis of aX in window             | (-∞, +∞)       |
| 5-9          | [aY]        | float64 | Same 5 features for aY               | (varies)       |
| 10-14        | [aZ]        | float64 | Same 5 features for aZ               | (varies)       |
| 15-19        | [gX]        | float64 | Same 5 features for gX               | (varies)       |
| 20-24        | [gY]        | float64 | Same 5 features for gY               | (varies)       |
| 25-29        | [gZ]        | float64 | Same 5 features for gZ               | (varies)       |
| 30           | label       | int64   | Window label (majority vote)         | {0, 1}         |

### Feature Definitions

**RMS (Root Mean Square)**:
```python
rms = np.sqrt(np.mean(window ** 2))
```
- Measures overall signal energy/intensity
- Always non-negative
- Higher RMS → more intense tremor

**Mean**:
```python
mean = np.mean(window)
```
- Central tendency, DC offset
- Should be near 0 for normalized data
- Deviation indicates systematic bias in window

**Standard Deviation**:
```python
std = np.std(window)
```
- Signal variability
- Higher std → more variable tremor amplitude
- Captures tremor severity

**Skewness**:
```python
skewness = scipy.stats.skew(window)
```
- Asymmetry of distribution
- Skew = 0: symmetric
- Skew > 0: right tail (positive spikes)
- Skew < 0: left tail (negative spikes)

**Kurtosis**:
```python
kurtosis = scipy.stats.kurtosis(window)
```
- Tail heaviness, outlier presence
- Kurt = 0: normal distribution (excess kurtosis)
- Kurt > 0: heavy tails (sharp peaks, outliers)
- Kurt < 0: light tails (flat distribution)

### Properties

- **Window Size**: 100 samples (1 second at 100 Hz)
- **Stride**: 50 samples (50% overlap)
- **Label Assignment**: Majority vote (e.g., 60+ samples class 1 → window labeled 1)
- **File Format**: CSV with header row for easy pandas loading

### Validation Rules

- ✅ Exactly 31 columns (30 features + 1 label)
- ✅ No missing values
- ✅ No infinite values
- ✅ Label column contains only {0, 1}
- ✅ Feature values within reasonable ranges (no extreme outliers)

### Usage Example

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Load feature matrix
train_df = pd.read_csv('backend/ml_data/processed/train_features.csv')
X_train = train_df.iloc[:, :-1]  # First 30 columns
y_train = train_df.iloc[:, -1]   # Last column (label)

# Train ML model
model = RandomForestClassifier()
model.fit(X_train, y_train)
```

---

## Entity 4: Sequence Tensor (Story 3 Output)

**Purpose**: Fixed-length time windows for deep learning models (LSTM, CNN)
**Format**: NumPy binary (.npy files)
**Location**: backend/ml_data/processed/

### Files

| File                  | Shape              | dtype   | Description                                      |
|-----------------------|--------------------|---------|--------------------------------------------------|
| train_sequences.npy   | (~349, 128, 6)     | float64 | Training sequences (3D tensor)                   |
| test_sequences.npy    | (~87, 128, 6)      | float64 | Test sequences (3D tensor)                       |
| train_seq_labels.npy  | (~349,)            | int64   | Training sequence labels                         |
| test_seq_labels.npy   | (~87,)             | int64   | Test sequence labels                             |

**Sequence Count Calculation**:
- Train: (22396 - 128) // 64 + 1 = 349 sequences
- Test: (5599 - 128) // 64 + 1 = 87 sequences

### Tensor Structure

**3D Shape: (num_windows, sequence_length, num_channels)**

- **Axis 0 (samples)**: Window/batch dimension, varies by dataset
  - train_sequences: ~349 windows
  - test_sequences: ~87 windows
- **Axis 1 (time)**: Time step dimension, fixed at 128 samples (~1.28 seconds at 100 Hz)
  - Represents temporal sequence
  - DL models process along this axis (LSTM unrolls, CNN convolves)
- **Axis 2 (features)**: Sensor channel dimension, fixed at 6 axes
  - Order: [aX, aY, aZ, gX, gY, gZ]
  - Represents multivariate time-series

### Properties

- **Sequence Length**: 128 samples (~1.28 seconds)
- **Stride**: 64 samples (50% overlap)
- **Channels**: 6 sensor axes (normalized values)
- **Data Type**: float64 (normalized sensor readings)
- **Label Assignment**: Majority vote per sequence

### Validation Rules

- ✅ Shape matches (N, 128, 6) where N = number of windows
- ✅ No NaN or Inf values
- ✅ Values typically in range [-5, +5] (normalized)
- ✅ Labels array length matches axis 0 dimension
- ✅ Labels contain only {0, 1}

### Usage Example (TensorFlow/Keras)

```python
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Load sequences
X_train = np.load('backend/ml_data/processed/train_sequences.npy')  # Shape: (349, 128, 6)
y_train = np.load('backend/ml_data/processed/train_seq_labels.npy')  # Shape: (349,)

# Define LSTM model
model = Sequential([
    LSTM(64, input_shape=(128, 6)),  # Matches axis 1 and 2
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.fit(X_train, y_train, epochs=10, batch_size=32)
```

### Usage Example (PyTorch)

```python
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

# Load sequences
X_train = np.load('backend/ml_data/processed/train_sequences.npy')
y_train = np.load('backend/ml_data/processed/train_seq_labels.npy')

# Convert to PyTorch tensors
X_tensor = torch.FloatTensor(X_train)  # Shape: (349, 128, 6)
y_tensor = torch.LongTensor(y_train)   # Shape: (349,)

# Create DataLoader
dataset = TensorDataset(X_tensor, y_tensor)
loader = DataLoader(dataset, batch_size=32, shuffle=True)

# Model expects input shape: (batch, time, features) = (32, 128, 6)
```

---

## Entity 5: Normalization Parameters (Metadata)

**Purpose**: Store normalization statistics for consistent preprocessing at inference time
**Format**: JSON file
**Location**: backend/ml_data/processed/normalization_params.json

### Schema

```json
{
  "method": "z-score",
  "description": "Standardization (mean=0, std=1) fitted on training set",
  "axes": ["aX", "aY", "aZ", "gX", "gY", "gZ"],
  "mean": {
    "aX": -1234.5678,
    "aY": 14567.8901,
    "aZ": -6789.0123,
    "gX": 4012.3456,
    "gY": 123.4567,
    "gZ": -456.7890
  },
  "std": {
    "aX": 1987.6543,
    "aY": 432.1098,
    "aZ": 3210.9876,
    "gX": 876.5432,
    "gY": 1234.5678,
    "gZ": 2345.6789
  },
  "fitted_on": "train",
  "train_samples": 22396,
  "test_samples": 5599,
  "random_state": 42,
  "created_at": "2026-02-15T20:30:00Z",
  "dataset_source": "Dataset.csv"
}
```

### Properties

- **Human-readable**: JSON format for easy inspection
- **Portable**: Can be loaded in any language
- **Versioned**: Include creation timestamp
- **Complete**: All information needed for inference-time normalization

### Usage (Inference)

```python
import json
import numpy as np

# Load normalization parameters
with open('backend/ml_data/processed/normalization_params.json', 'r') as f:
    params = json.load(f)

# Apply to new data
def normalize_inference(raw_data):
    """
    raw_data: numpy array shape (N, 6) with columns [aX, aY, aZ, gX, gY, gZ]
    returns: normalized array same shape
    """
    axes = params['axes']
    mean = np.array([params['mean'][ax] for ax in axes])
    std = np.array([params['std'][ax] for ax in axes])
    return (raw_data - mean) / std
```

---

## Relationships Between Entities

```
Raw Dataset (CSV)
    |
    | [1_preprocess.py]
    | - Drop magnetometer columns
    | - Handle nulls
    | - Stratified split 80/20
    | - Fit StandardScaler on train
    | - Normalize train and test
    |
    v
Preprocessed Dataset (.npy) + Normalization Params (JSON)
    |
    +-----------------------------------+
    |                                   |
    | [2_feature_engineering.py]        | [3_sequence_preparation.py]
    | - Sliding window (100, stride 50) | - Sliding window (128, stride 64)
    | - Extract 5 features per axis     | - Reshape to 3D tensor
    | - Majority vote labels            | - Majority vote labels
    |                                   |
    v                                   v
Feature Matrix (CSV)                Sequence Tensor (.npy)
    |                                   |
    v                                   v
[Traditional ML Models]             [Deep Learning Models]
- Random Forest                     - LSTM
- SVM                               - 1D CNN
- XGBoost                           - CNN-LSTM Hybrid
```

---

## File Size Estimates

| File                      | Estimated Size | Notes                                    |
|---------------------------|----------------|------------------------------------------|
| Dataset.csv               | 8 MB           | Raw text format                          |
| train_normalized.npy      | 1 MB           | 22396 × 6 × 8 bytes (float64)            |
| test_normalized.npy       | 0.25 MB        | 5599 × 6 × 8 bytes                       |
| train_labels.npy          | 0.2 MB         | 22396 × 8 bytes (int64)                  |
| test_labels.npy           | 0.05 MB        | 5599 × 8 bytes                           |
| train_features.csv        | 0.5 MB         | 447 × 31 columns, text format            |
| test_features.csv         | 0.15 MB        | 111 × 31 columns, text format            |
| train_sequences.npy       | 22 MB          | 349 × 128 × 6 × 8 bytes                  |
| test_sequences.npy        | 5.5 MB         | 87 × 128 × 6 × 8 bytes                   |
| train_seq_labels.npy      | 0.003 MB       | 349 × 8 bytes                            |
| test_seq_labels.npy       | 0.001 MB       | 87 × 8 bytes                             |
| normalization_params.json | 0.001 MB       | Small JSON file                          |
| preprocessing_report.txt  | 0.01 MB        | Text report                              |
| **TOTAL**                 | **~37 MB**     | All processed outputs                    |

---

## Summary

**5 Entities**:
1. **Raw Dataset**: Input CSV with 27,995 samples
2. **Preprocessed Dataset**: Cleaned, normalized, split data (Story 1 output)
3. **Feature Matrix**: Statistical features for ML (Story 2 output)
4. **Sequence Tensor**: Time windows for DL (Story 3 output)
5. **Normalization Parameters**: Metadata for inference

**Key Design Decisions**:
- File-based storage (no database interaction)
- NumPy binary format for efficiency
- CSV for ML feature matrices (pandas-friendly)
- JSON for human-readable metadata
- All outputs independently validated

**Total Storage**: ~37 MB for all processed data
