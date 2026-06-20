# Research: Raw Feature Pipeline Refactoring

**Feature**: 011-raw-feature-pipeline
**Date**: 2026-02-16
**Purpose**: Resolve technical unknowns before implementation

## Research Topics

### 1. Model Input Shape Validation Best Practices

**Decision**: Implement startup validation using model introspection for both scikit-learn and TensorFlow/Keras models.

**Rationale**:
- Catching dimension mismatches at startup (fail-fast) prevents silent prediction errors
- Model introspection has zero runtime overhead after initial validation
- Provides clear diagnostic messages for debugging

**Implementation Pattern**:

```python
# For scikit-learn models (.pkl)
import joblib

def validate_sklearn_model(model_path, expected_features=6):
    model = joblib.load(model_path)
    # Check n_features_in_ attribute (set during fit())
    if hasattr(model, 'n_features_in_'):
        if model.n_features_in_ != expected_features:
            raise ValueError(
                f"Model expects {model.n_features_in_} features, "
                f"but pipeline provides {expected_features}"
            )
    return model

# For TensorFlow/Keras models (.h5)
import tensorflow as tf

def validate_keras_model(model_path, expected_features=6):
    model = tf.keras.models.load_model(model_path)
    input_shape = model.input_shape
    # input_shape is (None, features) for Dense, (None, timesteps, features) for LSTM
    if input_shape[-1] != expected_features:
        raise ValueError(
            f"Model expects {input_shape[-1]} features, "
            f"but pipeline provides {expected_features}"
        )
    return model
```

**Alternatives Considered**:
- Runtime validation per prediction: Rejected (adds 1-2ms latency per prediction)
- Manual testing only: Rejected (error-prone, no automated safety net)
- Type hints/static analysis: Rejected (doesn't catch serialized model shape issues)

---

### 2. Normalization Parameter File Format

**Decision**: Use JSON format with explicit feature names and mean/std pairs.

**Rationale**:
- Human-readable for debugging and manual verification
- Version-controllable (can track changes in git)
- Standard format with broad tooling support
- Easy to regenerate from Dataset.csv
- Supports validation against Dataset.csv schema

**JSON Schema**:

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

**Generation Script**:

```python
import pandas as pd
import json
from datetime import datetime

def generate_normalization_params(dataset_path='Dataset.csv', output_path='params.json'):
    # Load dataset
    df = pd.read_csv(dataset_path)

    # Expected columns
    feature_columns = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

    # Validate columns exist
    missing = set(feature_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")

    # Calculate statistics
    features = []
    for col in feature_columns:
        features.append({
            "name": col,
            "mean": float(df[col].mean()),
            "std": float(df[col].std())
        })

    # Build params object
    params = {
        "features": features,
        "metadata": {
            "generated_from": dataset_path,
            "n_samples": len(df),
            "generated_date": datetime.utcnow().isoformat() + 'Z'
        }
    }

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"Generated {output_path} with {len(features)} features")
    return params
```

**Alternatives Considered**:
- Pickle file: Rejected (not human-readable, potential security issues)
- Database storage: Rejected (overkill for 6 simple values, adds DB dependency)
- YAML format: Rejected (JSON is more standard for Python ML pipelines)
- Separate files per feature: Rejected (management overhead, atomic updates impossible)

---

### 3. Django Model Migration Strategy for Schema Changes

**Decision**: Create Django migration to make statistical fields nullable (not remove them immediately), allowing gradual deprecation.

**Rationale**:
- Backwards compatible: Existing data preserved
- Reversible: Can rollback if issues discovered
- Safe: No data loss during migration
- Flexible: Old fields can be removed in future cleanup migration

**Migration Strategy**:

**Step 1**: Make fields nullable (non-destructive)
```python
# migration: 0012_make_statistical_fields_nullable.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('models', '0011_previous_migration'),
    ]

    operations = [
        # Make statistical fields optional
        migrations.AlterField(
            model_name='biometricreading',
            name='rms',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='biometricreading',
            name='mean',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='biometricreading',
            name='std',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='biometricreading',
            name='skewness',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='biometricreading',
            name='kurtosis',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
```

**Step 2**: Update MQTT client to stop populating these fields
```python
# In mqtt_client.py - only set raw sensor fields
biometric_reading = BiometricReading.objects.create(
    patient_id=patient_id,
    timestamp=timestamp,
    aX=sensor_data['aX'],
    aY=sensor_data['aY'],
    aZ=sensor_data['aZ'],
    gX=sensor_data['gX'],
    gY=sensor_data['gY'],
    gZ=sensor_data['gZ'],
    # rms, mean, std, skewness, kurtosis left as NULL
)
```

**Step 3** (Future): Remove fields after verification period
```python
# migration: 0013_remove_statistical_fields.py (run after confidence established)
operations = [
    migrations.RemoveField(model_name='biometricreading', name='rms'),
    migrations.RemoveField(model_name='biometricreading', name='mean'),
    migrations.RemoveField(model_name='biometricreading', name='std'),
    migrations.RemoveField(model_name='biometricreading', name='skewness'),
    migrations.RemoveField(model_name='biometricreading', name='kurtosis'),
]
```

**Alternatives Considered**:
- Immediate field removal: Rejected (risky, no rollback path for data)
- New model/table: Rejected (unnecessary complexity, duplicate code)
- Manual SQL: Rejected (bypasses Django ORM safety, non-portable)
- Keep fields forever: Rejected (storage waste, confusing schema)

---

### 4. Feature Extraction from Pandas DataFrame

**Decision**: Use explicit column list with validation for robust feature extraction.

**Rationale**:
- Explicit column names prevent silent failures if Dataset.csv schema changes
- Validation catches missing columns early (fail-fast)
- Maintains column order (important for model input)
- Clear and readable code

**Implementation Pattern**:

```python
import pandas as pd

def load_training_data(dataset_path='Dataset.csv'):
    # Define expected features (explicit, ordered)
    FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

    # Load dataset
    df = pd.read_csv(dataset_path)

    # Validate all required columns exist
    missing_cols = set(FEATURE_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Dataset missing required columns: {sorted(missing_cols)}\n"
            f"Found columns: {sorted(df.columns)}"
        )

    # Extract features (maintains order)
    X = df[FEATURE_COLUMNS].values  # Shape: (n_samples, 6)

    # Validate no missing values
    if pd.isna(X).any():
        raise ValueError("Dataset contains missing values in feature columns")

    # Extract labels (if present)
    if 'label' in df.columns or 'tremor_severity' in df.columns:
        label_col = 'label' if 'label' in df.columns else 'tremor_severity'
        y = df[label_col].values
    else:
        y = None  # Unsupervised or inference mode

    print(f"Loaded {len(X)} samples with {X.shape[1]} features")
    return X, y
```

**Alternatives Considered**:
- Use all columns except labels: Rejected (includes unwanted columns if schema changes)
- Use iloc[:, :6]: Rejected (assumes column order, fragile)
- Use regex column matching: Rejected (overcomplicated, error-prone)
- Use df.values directly: Rejected (no column validation)

---

### 5. MQTT Message Parsing for Raw Sensor Data

**Decision**: Use JSON parsing with explicit field extraction and comprehensive error handling.

**Rationale**:
- JSON is standard MQTT payload format
- Explicit field extraction prevents silent type coercion errors
- Error handling ensures bad messages don't crash the pipeline
- Logging provides debugging visibility for malformed messages

**Implementation Pattern**:

```python
import json
import logging

logger = logging.getLogger(__name__)

def parse_sensor_message(mqtt_message):
    """
    Parse MQTT message payload to extract 6 raw sensor values.

    Expected message format:
    {
        "timestamp": "2026-02-16T10:30:45.123Z",
        "patient_id": "PAT123",
        "sensor_data": {
            "aX": 0.123,
            "aY": -0.456,
            "aZ": 9.801,
            "gX": 0.012,
            "gY": -0.008,
            "gZ": 0.003
        }
    }

    Returns:
        dict: Parsed sensor data with 6 numeric values
    Raises:
        ValueError: If message format is invalid or missing required fields
    """
    try:
        # Parse JSON payload
        payload = json.loads(mqtt_message.payload)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in MQTT message: {e}")
        raise ValueError(f"Malformed MQTT message: {e}")

    # Validate required fields
    required_fields = ['timestamp', 'patient_id', 'sensor_data']
    missing = [f for f in required_fields if f not in payload]
    if missing:
        logger.error(f"MQTT message missing fields: {missing}")
        raise ValueError(f"Missing required fields: {missing}")

    # Extract sensor data
    sensor_data = payload['sensor_data']
    sensor_fields = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

    # Validate all 6 sensor fields present
    missing_sensors = [f for f in sensor_fields if f not in sensor_data]
    if missing_sensors:
        logger.error(f"MQTT message missing sensor fields: {missing_sensors}")
        raise ValueError(f"Missing sensor fields: {missing_sensors}")

    # Validate all sensor values are numeric
    for field in sensor_fields:
        value = sensor_data[field]
        if not isinstance(value, (int, float)):
            logger.error(f"Non-numeric sensor value: {field}={value}")
            raise ValueError(f"Sensor field '{field}' must be numeric, got {type(value)}")

    # Return validated data
    return {
        'timestamp': payload['timestamp'],
        'patient_id': payload['patient_id'],
        'aX': float(sensor_data['aX']),
        'aY': float(sensor_data['aY']),
        'aZ': float(sensor_data['aZ']),
        'gX': float(sensor_data['gX']),
        'gY': float(sensor_data['gY']),
        'gZ': float(sensor_data['gZ']),
    }
```

**Error Handling Strategy**:
- Malformed JSON: Log error, skip message, continue processing
- Missing fields: Log error, skip message, alert if frequency > 1/minute
- Invalid values: Log error, skip message, alert if frequency > 1/minute
- Type errors: Log error, skip message (don't attempt coercion)

**Alternatives Considered**:
- Assume fixed message structure: Rejected (fragile, no error handling)
- Parse as raw bytes: Rejected (requires manual parsing, error-prone)
- Use Protocol Buffers: Rejected (IoT device sends JSON, changing format out of scope)
- Lenient parsing with defaults: Rejected (silent errors, incorrect predictions)

---

## Summary of Decisions

| Topic | Decision | Key Benefit |
|-------|----------|-------------|
| Model Validation | Startup introspection | Fail-fast, zero runtime overhead |
| Normalization Format | JSON with metadata | Human-readable, version-controllable |
| Database Migration | Nullable fields first | Safe, reversible, no data loss |
| Feature Extraction | Explicit column list | Robust, fail-fast, clear intent |
| MQTT Parsing | JSON with validation | Comprehensive error handling, debuggable |

All decisions prioritize safety (fail-fast validation), maintainability (readable code/config), and performance (startup validation only, no runtime overhead).

---

**Research Status**: ✅ Complete
**Next Phase**: Phase 1 - Generate data-model.md and quickstart.md
