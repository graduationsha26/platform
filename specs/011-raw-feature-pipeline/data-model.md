# Data Model: Raw Feature Pipeline Refactoring

**Feature**: 011-raw-feature-pipeline
**Date**: 2026-02-16
**Purpose**: Define entities, relationships, and data structures for simplified ML pipeline

## Overview

This feature refactors the ML/DL pipeline to use only 6 raw sensor features, eliminating calculated statistical features. The data model reflects this simplification across training data, normalization parameters, model inputs, and database storage.

## Core Entities

### 1. Sensor Reading (Conceptual Entity)

**Description**: A single timestamped measurement from the wearable glove containing 6 raw sensor values from accelerometer and gyroscope.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| timestamp | DateTime | Required, ISO 8601 format | When the reading was captured by IoT device |
| patient_id | String | Required, FK to Patient | Which patient's glove generated this reading |
| aX | Float | Required, range: -20.0 to +20.0 m/s² | Accelerometer X-axis |
| aY | Float | Required, range: -20.0 to +20.0 m/s² | Accelerometer Y-axis |
| aZ | Float | Required, range: -20.0 to +20.0 m/s² | Accelerometer Z-axis |
| gX | Float | Required, range: -2000 to +2000 °/s | Gyroscope X-axis |
| gY | Float | Required, range: -2000 to +2000 °/s | Gyroscope Y-axis |
| gZ | Float | Required, range: -2000 to +2000 °/s | Gyroscope Z-axis |

**Validation Rules**:
- All 6 sensor values must be numeric (no NaN, no Inf)
- Timestamp must be within ±5 minutes of server time (clock sync check)
- Patient ID must reference existing patient record
- Sensor values outside ranges indicate device malfunction (log warning, don't fail)

**State Transitions**:
1. **Received** (from MQTT) → **Parsed** (JSON decoded) → **Validated** (range checks) → **Stored** (in database) → **Normalized** (preprocessing) → **Predicted** (model inference)

**Relationships**:
- Belongs to exactly one Patient (many-to-one)
- Source of one ModelInputVector (one-to-one, ephemeral)
- Stored as one BiometricReading record (one-to-one, persistent)

**Storage**:
- MQTT payload: JSON message on `tremor/sensor/{patient_id}` topic
- Database: BiometricReading Django model
- Memory: NumPy array (6,) during inference

---

### 2. Normalization Parameters (File-Based Entity)

**Description**: Statistical metadata (mean and standard deviation) for each of the 6 sensor axes, calculated from training data and used to scale inputs consistently.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| feature_name | String | One of: aX, aY, aZ, gX, gY, gZ | Sensor axis identifier |
| mean | Float | Required, calculated from training data | Average value across all training samples |
| std | Float | Required, > 0.0 | Standard deviation across training samples |

**Collection Attributes** (6 features × 2 stats = 12 values total):
| Metadata Field | Type | Description |
|----------------|------|-------------|
| generated_from | String | Source file (e.g., "Dataset.csv") |
| n_samples | Integer | Number of training samples used |
| generated_date | DateTime | When params were calculated |

**Validation Rules**:
- Must contain exactly 6 feature entries (one per sensor axis)
- Feature names must match Dataset.csv columns exactly
- Standard deviation must be > 0 (prevent division by zero)
- Mean values should be within expected sensor ranges

**State Transitions**:
1. **Generated** (from Dataset.csv) → **Validated** (schema check) → **Saved** (written to params.json) → **Loaded** (read by inference) → **Applied** (normalization transform)

**Relationships**:
- Generated from Dataset.csv (one-to-one)
- Used by all inference requests (one-to-many)
- Versioned with model files (one params.json per model generation)

**Storage**:
- File: `backend/ml_data/params.json`
- Format: JSON (see research.md for schema)
- Access: Read-only during inference, regenerated during training

**Example**:
```json
{
  "features": [
    {"name": "aX", "mean": 0.123, "std": 1.456},
    {"name": "aY", "mean": -0.045, "std": 1.234},
    {"name": "aZ", "mean": 9.801, "std": 1.789},
    {"name": "gX", "mean": 0.012, "std": 0.567},
    {"name": "gY", "mean": -0.008, "std": 0.432},
    {"name": "gZ", "mean": 0.003, "std": 0.321}
  ],
  "metadata": {
    "generated_from": "Dataset.csv",
    "n_samples": 50000,
    "generated_date": "2026-02-16T10:30:00Z"
  }
}
```

---

### 3. Model Input Vector (Ephemeral Entity)

**Description**: A 6-dimensional numeric array representing one sensor reading after normalization, ready to be passed to ML/DL models.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| features | Float[6] | NumPy array, shape: (6,) | Normalized sensor values [aX, aY, aZ, gX, gY, gZ] |
| original_reading_id | String | Optional, for traceability | Reference to source sensor reading |

**Validation Rules**:
- Must contain exactly 6 numeric values
- No NaN or Inf values (normalization should never produce these)
- Normalized values typically in range [-3, +3] (±3 standard deviations)
- Array dtype must be float32 or float64

**State Transitions**:
1. **Created** (from SensorReading) → **Normalized** (z-score transform) → **Validated** (shape check) → **Predicted** (model inference) → **Discarded** (ephemeral, not persisted)

**Relationships**:
- Created from one SensorReading (one-to-one)
- Consumed by one Model (one-to-one per prediction)
- Not persisted (exists only in memory during inference)

**Normalization Formula**:
```
normalized_value = (raw_value - mean) / std
```

For each of the 6 features, where mean and std come from Normalization Parameters.

**Example**:
```python
# Raw sensor reading
raw = [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]

# After normalization (using params.json)
normalized = [
    (0.5 - 0.123) / 1.456,    # aX
    (-0.3 - (-0.045)) / 1.234, # aY
    (10.2 - 9.801) / 1.789,    # aZ
    (0.05 - 0.012) / 0.567,    # gX
    (-0.02 - (-0.008)) / 0.432, # gY
    (0.01 - 0.003) / 0.321     # gZ
]
# Result shape: (6,)
```

**Storage**:
- In-memory only: NumPy array during inference
- Not persisted to database
- Lifecycle: Created → Used → Garbage collected

---

### 4. Trained Model (File-Based Entity)

**Description**: Serialized ML (scikit-learn) or DL (TensorFlow/Keras) model with input layer expecting exactly 6 features.

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| model_type | Enum | RF, SVM, LSTM, CNN | Which algorithm/architecture |
| input_shape | Tuple | (6,) for ML, (timesteps, 6) for DL | Expected input dimensions |
| trained_date | DateTime | ISO 8601 format | When model was trained |
| training_samples | Integer | > 1000 | Number of samples used for training |
| validation_f1 | Float | 0.0 to 1.0 | F1 score on validation set |

**ML Models** (scikit-learn):
| Model Type | File Path | Input Shape | Training Script |
|------------|-----------|-------------|-----------------|
| Random Forest | backend/ml_models/random_forest.pkl | (6,) | apps/ml/train.py |
| SVM | backend/ml_models/svm.pkl | (6,) | apps/ml/train.py |

**DL Models** (TensorFlow/Keras):
| Model Type | File Path | Input Shape | Training Script |
|------------|-----------|-------------|-----------------|
| LSTM | backend/dl_models/lstm.h5 | (None, timesteps, 6) | apps/dl/train_lstm.py |
| CNN | backend/dl_models/cnn.h5 | (None, 6, 1) | apps/dl/train_cnn.py |

**Validation Rules**:
- Input shape must match 6 features (detected via model introspection)
- Model files must be loadable without errors
- Validation F1 score must be ≥ 0.85 (minimum acceptable performance)
- File size typically: 1-50MB for ML models, 5-200MB for DL models

**State Transitions**:
1. **Training** (fit on Dataset.csv) → **Validated** (test set evaluation) → **Saved** (serialized to disk) → **Loaded** (read by inference) → **Active** (serving predictions)

**Relationships**:
- Trained from one Dataset.csv (many-to-one, one dataset trains all models)
- Uses one NormalizationParameters (one-to-one per training run)
- Produces many Predictions (one-to-many during inference)

**Storage**:
- ML models: Joblib pickle format (.pkl)
- DL models: HDF5 format (.h5)
- Both formats: Gitignored, stored externally or regenerated

---

### 5. BiometricReading (Django Model - Database Entity)

**Description**: Persistent database record storing raw sensor readings from patients, used for analytics and model retraining.

**Django Model Definition**:
```python
class BiometricReading(models.Model):
    # Foreign key to patient
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=False)

    # Raw sensor values (6 features)
    aX = models.FloatField()  # Accelerometer X
    aY = models.FloatField()  # Accelerometer Y
    aZ = models.FloatField()  # Accelerometer Z
    gX = models.FloatField()  # Gyroscope X
    gY = models.FloatField()  # Gyroscope Y
    gZ = models.FloatField()  # Gyroscope Z

    # REMOVED FIELDS (after migration):
    # rms = models.FloatField(null=True, blank=True)  # Deprecated
    # mean = models.FloatField(null=True, blank=True)  # Deprecated
    # std = models.FloatField(null=True, blank=True)  # Deprecated
    # skewness = models.FloatField(null=True, blank=True)  # Deprecated
    # kurtosis = models.FloatField(null=True, blank=True)  # Deprecated

    class Meta:
        db_table = 'biometric_readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['patient', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"BiometricReading({self.patient.id}, {self.timestamp})"
```

**Validation Rules**:
- All 6 sensor fields must be numeric (enforced by Django FloatField)
- Timestamp must be valid datetime
- Patient foreign key must reference existing patient
- Unique constraint: (patient, timestamp) if needed (optional, depends on sampling rate)

**State Transitions**:
1. **Created** (from MQTT message) → **Validated** (Django model validation) → **Saved** (database INSERT) → **Queried** (for analytics) → **Archived** (after 90 days, optional)

**Relationships**:
- Belongs to one Patient (many-to-one)
- Can be associated with one Prediction (one-to-one, via separate Prediction model)
- Source for Dataset.csv regeneration (many-to-one)

**Storage Impact**:
- **Before refactoring**: 15 fields per reading (8 floats + FK + timestamp + 5 statistical fields) ≈ 100 bytes
- **After refactoring**: 9 fields per reading (8 floats + FK + timestamp) ≈ 60 bytes
- **Storage reduction**: 40% per reading, 60% if statistical fields physically removed

**Migration Strategy**: See research.md Section 3 for detailed migration plan.

---

## Entity Relationships Diagram

```
                      +-------------------+
                      |   Dataset.csv     |
                      +-------------------+
                               |
                               | (training)
                               v
         +-------------------------------------+
         |                                     |
         v                                     v
+-------------------+            +-------------------+
| Trained Model     |            | Normalization     |
| (4 model files)   |            | Parameters        |
+-------------------+            | (params.json)     |
         |                       +-------------------+
         |                                 |
         | (loads)                         | (loads)
         v                                 v
+-----------------------------------------------+
|          Inference Pipeline                   |
+-----------------------------------------------+
         ^                                 |
         |                                 |
         | (receives)                      | (produces)
         |                                 v
+-------------------+            +-------------------+
| Sensor Reading    |            | Prediction        |
| (MQTT message)    |            | (output)          |
+-------------------+            +-------------------+
         |
         | (stored as)
         v
+-------------------+
| BiometricReading  |
| (Django model)    |
+-------------------+
         |
         | (belongs to)
         v
+-------------------+
|     Patient       |
+-------------------+
```

**Key Flows**:
1. **Training Flow**: Dataset.csv → Trained Models + Normalization Parameters
2. **Inference Flow**: Sensor Reading (MQTT) → Model Input Vector → Trained Model → Prediction
3. **Storage Flow**: Sensor Reading (MQTT) → BiometricReading (Database)

---

## Data Validation Rules Summary

| Entity | Critical Validations |
|--------|---------------------|
| Sensor Reading | 6 numeric fields, timestamp within ±5 min, patient exists |
| Normalization Parameters | Exactly 6 features, std > 0, schema matches Dataset.csv |
| Model Input Vector | Shape (6,), no NaN/Inf, normalized range [-10, +10] |
| Trained Model | Input shape matches 6 features, F1 ≥ 0.85, loadable |
| BiometricReading | All fields numeric, timestamp valid, patient FK valid |

---

## Storage Requirements

| Entity | Size Per Record | Total Storage | Notes |
|--------|----------------|---------------|-------|
| Sensor Reading | ~100 bytes (MQTT) | Ephemeral (not stored) | Messages retained ~1 minute |
| Normalization Parameters | ~500 bytes (JSON) | Static (1 file) | Regenerated per training run |
| Model Input Vector | 24 bytes (6 floats) | Ephemeral (not stored) | Memory only during inference |
| Trained Model | 1-200 MB (serialized) | 4 models × avg 50MB = 200MB | Gitignored, regenerated |
| BiometricReading | 60 bytes (database row) | 60 bytes × N readings | Grows over time, archivable |

**Database Growth Estimate** (after refactoring):
- 10 predictions/sec/patient × 10 patients = 100 readings/sec
- 100 readings/sec × 60 bytes = 6 KB/sec = 520 MB/day
- With 60% storage reduction: ~200 MB/day savings

---

**Data Model Status**: ✅ Complete
**Next Phase**: Generate quickstart.md for integration testing scenarios
