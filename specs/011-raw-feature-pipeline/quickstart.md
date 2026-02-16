# Quickstart Guide: Raw Feature Pipeline Refactoring

**Feature**: 011-raw-feature-pipeline
**Date**: 2026-02-16
**Purpose**: Step-by-step integration testing scenarios for validating the 6-feature ML/DL pipeline

## Overview

This guide provides hands-on scenarios for testing each component of the refactored ML/DL pipeline. All scenarios assume you're working from the repository root: `C:\Data from HDD\Graduation Project\Platform`

## Prerequisites

- Python 3.9+ with virtual environment activated
- Django development server configured
- Dataset.csv present in repository root with 6 columns (aX, aY, aZ, gX, gY, gZ)
- Required Python packages: scikit-learn, tensorflow, pandas, numpy, paho-mqtt, django

## Scenario 1: Training Workflow

**Goal**: Retrain all ML/DL models using only 6 raw features from Dataset.csv

### Step 1.1: Verify Dataset Schema

```bash
# Navigate to backend directory
cd backend

# Run Python to inspect Dataset.csv columns
python -c "import pandas as pd; df = pd.read_csv('../Dataset.csv'); print('Columns:', df.columns.tolist()); print('Shape:', df.shape)"
```

**Expected Output**:
```
Columns: ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ', 'label']
Shape: (50000, 7)
```

### Step 1.2: Retrain ML Models (Random Forest, SVM)

```bash
# Run ML training script
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models/

# Verify model files created
ls -lh ml_models/random_forest.pkl ml_models/svm.pkl
```

**Expected Output**:
```
Training Random Forest with 50000 samples and 6 features...
Training SVM with 50000 samples and 6 features...
Saved models to ml_models/
```

**Validation Check**: Model files should be 1-50MB and loadable without errors

### Step 1.3: Retrain DL Models (LSTM, CNN)

```bash
# Retrain LSTM
python apps/dl/train_lstm.py --dataset ../Dataset.csv --output dl_models/lstm.h5

# Retrain CNN
python apps/dl/train_cnn.py --dataset ../Dataset.csv --output dl_models/cnn.h5

# Verify model files
ls -lh dl_models/lstm.h5 dl_models/cnn.h5
```

**Expected Output**:
```
LSTM training: Epoch 1/50, Loss: 0.234...
CNN training: Epoch 1/30, Loss: 0.189...
Model saved to dl_models/
```

**Validation Check**: Model files should be 5-200MB and contain correct input shape

---

## Scenario 2: Normalization Generation

**Goal**: Generate params.json with mean/std statistics for exactly 6 features

### Step 2.1: Generate Normalization Parameters

```bash
# Run parameter generation script
cd backend
python apps/ml/generate_params.py --dataset ../Dataset.csv --output ml_data/params.json
```

**Expected Output**:
```
Loading dataset from ../Dataset.csv...
Calculating statistics for 6 features: aX, aY, aZ, gX, gY, gZ
Generated ml_data/params.json with 6 features
```

### Step 2.2: Validate params.json Schema

```bash
# Inspect generated file
python -c "import json; params = json.load(open('ml_data/params.json')); print('Features:', len(params['features'])); print(json.dumps(params, indent=2))"
```

**Expected Output**:
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
    "generated_from": "../Dataset.csv",
    "n_samples": 50000,
    "generated_date": "2026-02-16T10:30:00Z"
  }
}
```

**Validation Checks**:
- Exactly 6 feature entries
- All std values > 0.0
- Feature names match Dataset.csv columns
- Mean values within expected sensor ranges

---

## Scenario 3: Model Validation

**Goal**: Verify that all trained models expect 6-dimensional input vectors

### Step 3.1: Validate ML Model Input Shapes

```bash
cd backend
python -c "
import joblib

# Load Random Forest
rf = joblib.load('ml_models/random_forest.pkl')
print(f'Random Forest n_features_in_: {rf.n_features_in_}')

# Load SVM
svm = joblib.load('ml_models/svm.pkl')
print(f'SVM n_features_in_: {svm.n_features_in_}')
"
```

**Expected Output**:
```
Random Forest n_features_in_: 6
SVM n_features_in_: 6
```

### Step 3.2: Validate DL Model Input Shapes

```bash
python -c "
import tensorflow as tf

# Load LSTM
lstm = tf.keras.models.load_model('dl_models/lstm.h5')
print(f'LSTM input shape: {lstm.input_shape}')

# Load CNN
cnn = tf.keras.models.load_model('dl_models/cnn.h5')
print(f'CNN input shape: {cnn.input_shape}')
"
```

**Expected Output**:
```
LSTM input shape: (None, timesteps, 6)
CNN input shape: (None, 6, 1)
```

**Validation Check**: Last dimension of input shape must be 6 for all models

### Step 3.3: Run Startup Validation Script

```bash
# Run validation script that checks all models
python apps/ml/validate_models.py
```

**Expected Output**:
```
✓ Random Forest: Input shape (6,) - PASS
✓ SVM: Input shape (6,) - PASS
✓ LSTM: Input shape (None, timesteps, 6) - PASS
✓ CNN: Input shape (None, 6, 1) - PASS

All models validated successfully.
```

---

## Scenario 4: Inference Testing

**Goal**: Test inference pipeline with 6-element sensor arrays

### Step 4.1: Test ML Inference

```bash
cd backend
python -c "
import numpy as np
from apps.ml.predict import predict

# Test sensor reading with 6 values
sensor_data = np.array([0.5, -0.3, 10.2, 0.05, -0.02, 0.01])
print(f'Input shape: {sensor_data.shape}')

# Run inference
result = predict(sensor_data, model_type='random_forest')
print(f'Prediction: {result}')
"
```

**Expected Output**:
```
Input shape: (6,)
Loading model from ml_models/random_forest.pkl
Normalizing input with params.json
Prediction: {'tremor_severity': 0.72, 'confidence': 0.89}
```

### Step 4.2: Test DL Inference

```bash
python -c "
import numpy as np
from apps.dl.inference import predict_dl

# Test with sequence of sensor readings (for LSTM)
sensor_sequence = np.random.randn(10, 6)  # 10 timesteps, 6 features
print(f'Sequence shape: {sensor_sequence.shape}')

# Run LSTM inference
result = predict_dl(sensor_sequence, model_type='lstm')
print(f'Prediction: {result}')
"
```

**Expected Output**:
```
Sequence shape: (10, 6)
Loading LSTM model from dl_models/lstm.h5
Normalizing sequence with params.json
Prediction: {'tremor_severity': 0.68, 'confidence': 0.92}
```

### Step 4.3: Test API Endpoint

```bash
# Start Django development server in background
python manage.py runserver &

# Wait for server startup
sleep 3

# Test inference endpoint
curl -X POST http://localhost:8000/api/ml/predict/ \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]}'
```

**Expected Response**:
```json
{
  "tremor_severity": 0.72,
  "confidence": 0.89,
  "model_type": "random_forest",
  "timestamp": "2026-02-16T10:35:00Z"
}
```

**Validation Check**: Response time should be under 70ms (check response headers)

---

## Scenario 5: MQTT Simulation

**Goal**: Send test MQTT messages with 6 sensor values and verify processing

### Step 5.1: Start MQTT Client

```bash
cd backend
# Ensure MQTT broker is running (Mosquitto or equivalent)

# Start Django MQTT client
python mqtt/mqtt_client.py &
```

**Expected Output**:
```
Connecting to MQTT broker at localhost:1883
Subscribed to topic: tremor/sensor/#
Waiting for messages...
```

### Step 5.2: Publish Test Message

```bash
# Install mosquitto-clients if needed: sudo apt-get install mosquitto-clients

# Publish test sensor reading
mosquitto_pub -h localhost -t tremor/sensor/PAT123 -m '{
  "timestamp": "2026-02-16T10:40:00.123Z",
  "patient_id": "PAT123",
  "sensor_data": {
    "aX": 0.123,
    "aY": -0.456,
    "aZ": 9.801,
    "gX": 0.012,
    "gY": -0.008,
    "gZ": 0.003
  }
}'
```

**Expected Output** (from MQTT client logs):
```
Received message on tremor/sensor/PAT123
Parsed sensor data: 6 values
Stored BiometricReading for patient PAT123
Running inference...
Prediction: tremor_severity=0.65
```

### Step 5.3: Verify Database Storage

```bash
# Check database for stored reading
python manage.py shell -c "
from models.biometric_reading import BiometricReading
reading = BiometricReading.objects.filter(patient_id='PAT123').latest('timestamp')
print(f'Stored fields: aX={reading.aX}, aY={reading.aY}, aZ={reading.aZ}')
print(f'              gX={reading.gX}, gY={reading.gY}, gZ={reading.gZ}')
print(f'RMS field exists: {hasattr(reading, \"rms\")}')
"
```

**Expected Output**:
```
Stored fields: aX=0.123, aY=-0.456, aZ=9.801
              gX=0.012, gY=-0.008, gZ=0.003
RMS field exists: False
```

**Validation Check**: Only 6 sensor fields stored, no statistical fields present

---

## Scenario 6: Database Migration

**Goal**: Apply BiometricReading schema changes safely

### Step 6.1: Create Migration

```bash
cd backend
python manage.py makemigrations --name make_statistical_fields_nullable
```

**Expected Output**:
```
Migrations for 'models':
  models/migrations/0012_make_statistical_fields_nullable.py
    - Alter field rms on biometricreading
    - Alter field mean on biometricreading
    - Alter field std on biometricreading
    - Alter field skewness on biometricreading
    - Alter field kurtosis on biometricreading
```

### Step 6.2: Inspect Migration

```bash
# View generated migration file
cat models/migrations/0012_make_statistical_fields_nullable.py
```

**Expected Content**:
```python
operations = [
    migrations.AlterField(
        model_name='biometricreading',
        name='rms',
        field=models.FloatField(null=True, blank=True),
    ),
    # ... (other fields made nullable)
]
```

### Step 6.3: Apply Migration

```bash
# Test migration on local database first
python manage.py migrate --plan

# Apply migration
python manage.py migrate
```

**Expected Output**:
```
Running migrations:
  Applying models.0012_make_statistical_fields_nullable... OK
```

### Step 6.4: Verify Schema

```bash
# Inspect table schema
python manage.py dbshell -c "\d biometric_readings"
```

**Expected Output**:
```
Column      | Type                        | Nullable
------------+-----------------------------+---------
id          | bigint                      | not null
patient_id  | bigint                      | not null
timestamp   | timestamp with time zone    | not null
aX          | double precision            | not null
aY          | double precision            | not null
aZ          | double precision            | not null
gX          | double precision            | not null
gY          | double precision            | not null
gZ          | double precision            | not null
rms         | double precision            | YES
mean        | double precision            | YES
std         | double precision            | YES
skewness    | double precision            | YES
kurtosis    | double precision            | YES
```

**Validation Check**: 6 sensor fields NOT NULL, 5 statistical fields NULL (nullable)

---

## Scenario 7: Performance Validation

**Goal**: Measure inference latency and ensure it stays under 70ms

### Step 7.1: Benchmark Single Prediction

```bash
cd backend
python -c "
import time
import numpy as np
from apps.ml.predict import predict

# Generate test data
sensor_data = np.random.randn(6)

# Measure latency over 100 predictions
latencies = []
for _ in range(100):
    start = time.perf_counter()
    predict(sensor_data, model_type='random_forest')
    end = time.perf_counter()
    latencies.append((end - start) * 1000)  # Convert to ms

# Calculate statistics
import statistics
print(f'Mean latency: {statistics.mean(latencies):.2f} ms')
print(f'Median latency: {statistics.median(latencies):.2f} ms')
print(f'95th percentile: {sorted(latencies)[94]:.2f} ms')
print(f'Max latency: {max(latencies):.2f} ms')
"
```

**Expected Output**:
```
Mean latency: 45.23 ms
Median latency: 43.12 ms
95th percentile: 58.67 ms
Max latency: 68.45 ms
```

**Validation Check**: 95th percentile must be < 70ms

### Step 7.2: Benchmark All Model Types

```bash
python apps/ml/benchmark.py --iterations 100 --all-models
```

**Expected Output**:
```
Benchmarking inference latency (100 iterations per model)...

Random Forest:
  Mean: 45.2 ms, 95th: 58.7 ms - PASS (<70ms)

SVM:
  Mean: 38.1 ms, 95th: 51.3 ms - PASS (<70ms)

LSTM:
  Mean: 52.4 ms, 95th: 64.8 ms - PASS (<70ms)

CNN:
  Mean: 48.9 ms, 95th: 62.1 ms - PASS (<70ms)

All models meet latency requirement (<70ms)
```

### Step 7.3: Profile Inference Pipeline

```bash
# Run cProfile to identify bottlenecks
python -m cProfile -s cumtime apps/ml/predict.py > profile_output.txt

# View top time consumers
head -20 profile_output.txt
```

**Expected Output**:
```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.001    0.001    0.045    0.045 predict.py:12(predict)
        1    0.015    0.015    0.025    0.025 sklearn/ensemble/_forest.py:545(predict)
        1    0.005    0.005    0.010    0.010 normalize.py:8(normalize_features)
        1    0.003    0.003    0.005    0.005 json.py:293(load)
```

**Validation Check**: No single function should take > 20ms

---

## Scenario 8: Accuracy Verification

**Goal**: Validate model performance (F1 ≥ 0.85) on test dataset

### Step 8.1: Split Dataset

```bash
cd backend
python -c "
import pandas as pd
from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_csv('../Dataset.csv')

# Split 80/20
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label'])

# Save test set
test_df.to_csv('ml_data/test_dataset.csv', index=False)
print(f'Test set size: {len(test_df)} samples')
"
```

**Expected Output**:
```
Test set size: 10000 samples
```

### Step 8.2: Evaluate ML Models

```bash
python apps/ml/evaluate.py --test-data ml_data/test_dataset.csv --models ml_models/
```

**Expected Output**:
```
Evaluating models on 10000 test samples...

Random Forest:
  Accuracy: 0.912
  Precision: 0.895
  Recall: 0.887
  F1 Score: 0.891 - PASS (≥0.85)

SVM:
  Accuracy: 0.898
  Precision: 0.873
  Recall: 0.892
  F1 Score: 0.882 - PASS (≥0.85)

Both ML models meet accuracy requirement (F1 ≥ 0.85)
```

### Step 8.3: Evaluate DL Models

```bash
python apps/dl/evaluate.py --test-data ml_data/test_dataset.csv --models dl_models/
```

**Expected Output**:
```
Evaluating DL models on 10000 test samples...

LSTM:
  Accuracy: 0.924
  Precision: 0.908
  Recall: 0.901
  F1 Score: 0.904 - PASS (≥0.85)

CNN:
  Accuracy: 0.918
  Precision: 0.897
  Recall: 0.895
  F1 Score: 0.896 - PASS (≥0.85)

Both DL models meet accuracy requirement (F1 ≥ 0.85)
```

### Step 8.4: Compare with Previous Performance

```bash
# Generate comparison report
python apps/ml/compare_models.py --previous-metrics ml_data/baseline_metrics.json --current-models ml_models/ dl_models/
```

**Expected Output**:
```
Model Performance Comparison:

| Model          | Previous F1 | Current F1 | Change  | Status |
|----------------|-------------|------------|---------|--------|
| Random Forest  | 0.887       | 0.891      | +0.004  | PASS   |
| SVM            | 0.879       | 0.882      | +0.003  | PASS   |
| LSTM           | 0.901       | 0.904      | +0.003  | PASS   |
| CNN            | 0.893       | 0.896      | +0.003  | PASS   |

All models within 5% of previous performance (requirement: ≥-5%)
```

**Validation Check**: No model should have F1 score drop > 5% from baseline

---

## Success Criteria Checklist

Use this checklist to verify all success criteria from spec.md are met:

- [ ] **SC-001**: Inference latency < 70ms for 95% of requests
- [ ] **SC-002**: Model F1 score within 5% of previous performance (≥0.85)
- [ ] **SC-003**: 100 consecutive readings processed without dimension errors
- [ ] **SC-004**: Database storage reduced by 60% (from 15+ to 6 fields)
- [ ] **SC-005**: Training script completes with 6-feature input
- [ ] **SC-006**: params.json contains exactly 6 feature entries
- [ ] **SC-007**: All 4 model types accept 6-dimensional input
- [ ] **SC-008**: Startup validation detects incorrect input dimensions
- [ ] **SC-009**: Zero prediction errors in 24 hours of operation
- [ ] **SC-010**: MQTT processing extracts exactly 6 sensor values

---

## Troubleshooting

### Issue: Model fails to load with "dimension mismatch"

**Solution**: Verify model was retrained with 6 features:
```bash
python -c "import joblib; m = joblib.load('ml_models/random_forest.pkl'); print(m.n_features_in_)"
```

### Issue: Normalization produces NaN values

**Solution**: Check params.json has no zero std values:
```bash
python -c "import json; p = json.load(open('ml_data/params.json')); print([f for f in p['features'] if f['std'] == 0])"
```

### Issue: Inference latency exceeds 70ms

**Solution**: Profile and identify bottleneck:
```bash
python -m cProfile -o profile.stats apps/ml/predict.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime'); p.print_stats(10)"
```

### Issue: MQTT messages fail to parse

**Solution**: Validate message schema:
```bash
# Check MQTT client logs for parsing errors
tail -f logs/mqtt_client.log | grep "ERROR"
```

### Issue: Database migration fails

**Solution**: Check for conflicting migrations:
```bash
python manage.py showmigrations
python manage.py migrate --fake-initial
```

---

**Quickstart Status**: ✅ Complete
**Next Phase**: Run `/speckit.tasks` to generate task breakdown for implementation
