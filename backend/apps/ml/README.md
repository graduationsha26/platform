# ML Pipeline - 6 Raw Feature Architecture

## Overview

This ML pipeline has been refactored to use only **6 raw sensor features** from the accelerometer and gyroscope data, eliminating calculated statistical features for improved performance and data consistency.

## Features

The pipeline processes exactly **6 raw sensor values**:

- **aX, aY, aZ**: Accelerometer 3-axis readings (m/s²)
- **gX, gY, gZ**: Gyroscope 3-axis readings (°/s)

## Architecture

```
Dataset.csv (6 features)
    ↓
Training Scripts → Trained Models (.pkl)
    ↓
params.json (normalization parameters)
    ↓
Inference Pipeline → Predictions
```

## Quick Start

### 1. Generate Normalization Parameters

```bash
python apps/ml/generate_params.py --dataset ../Dataset.csv --output ml_data/params.json
```

### 2. Train Models

```bash
# Train both Random Forest and SVM
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models

# Train specific model
python apps/ml/train.py --dataset ../Dataset.csv --output ml_models --models rf
```

### 3. Run Inference

```python
from apps.ml.predict import MLPredictor
import numpy as np

# Initialize predictor (loads models and params)
predictor = MLPredictor('ml_models', 'ml_data/params.json')

# Predict from 6 sensor values
sensor_data = np.array([54.17, 5756.36, -13338.66, 5002.23, -239.64, 275.45])
result = predictor.predict(sensor_data, model_type='rf')

print(f"Prediction: {result['prediction']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Latency: {result['latency_ms']:.2f} ms")
```

## Files

### Utilities

- **`feature_utils.py`**: Feature extraction and validation
  - `FEATURE_COLUMNS`: Standard 6-feature schema
  - `load_training_data()`: Load Dataset.csv with validation
  - `extract_features_from_dict()`: Parse MQTT messages

- **`normalize.py`**: Z-score normalization
  - `load_params()`: Load params.json
  - `normalize_features()`: Apply (x - mean) / std
  - `denormalize_features()`: Reverse normalization

- **`validate_models.py`**: Model shape validation
  - `validate_sklearn_model()`: Check n_features_in_=6
  - `validate_keras_model()`: Check input_shape[-1]==6
  - `validate_all_models()`: Startup validation for all models

- **`generate_params.py`**: Generate params.json from Dataset.csv

### Training

- **`train.py`**: Train Random Forest and SVM models
  - Extracts 6 features from Dataset.csv
  - Saves models to ml_models/
  - Generates metrics JSON files

### Inference

- **`predict.py`**: ML model inference
  - `MLPredictor`: Singleton predictor with validation
  - `predict()`: Convenience function for single predictions
  - Automatic normalization using params.json

## Validation

All models undergo startup validation:

```bash
# Validate all models
python apps/ml/validate_models.py

# Validate specific model
python apps/ml/validate_models.py ml_models/random_forest.pkl 6
```

## Performance

**Latency** (95th percentile):
- Random Forest: ~31ms
- SVM: ~0.7ms
- **Target**: <70ms ✓

**Accuracy** (F1 Score):
- Random Forest: 0.9971 (99.71%)
- SVM: 0.9044 (90.44%)
- **Target**: ≥0.85 ✓

## Model Specifications

| Model | File | Input Shape | F1 Score | Latency |
|-------|------|-------------|----------|---------|
| Random Forest | `ml_models/random_forest.pkl` | (6,) | 0.9971 | ~31ms |
| SVM | `ml_models/svm.pkl` | (6,) | 0.9044 | ~0.7ms |

## params.json Schema

```json
{
  "features": [
    {"name": "aX", "mean": 54.17, "std": 5220.68},
    {"name": "aY", "mean": 5756.36, "std": 5201.58},
    {"name": "aZ", "mean": -13338.66, "std": 3058.98},
    {"name": "gX", "mean": 5002.23, "std": 485.18},
    {"name": "gY", "mean": -239.64, "std": 999.92},
    {"name": "gZ", "mean": 275.45, "std": 3340.56}
  ],
  "metadata": {
    "generated_from": "Dataset.csv",
    "n_samples": 27995,
    "generated_date": "2026-02-16T11:23:55Z"
  }
}
```

## Testing

```bash
# Test feature extraction
python apps/ml/feature_utils.py ../Dataset.csv

# Test normalization
python apps/ml/normalize.py ml_data/params.json

# Test inference
python apps/ml/predict.py --model-dir ml_models --params ml_data/params.json --test-data "54.17,5756.36,-13338.66,5002.23,-239.64,275.45"
```

## Troubleshooting

### Model dimension mismatch

If you see "model expects N features" errors:
1. Retrain models: `python apps/ml/train.py --dataset ../Dataset.csv`
2. Verify params.json has 6 features: `python apps/ml/generate_params.py --verify`

### NaN values in normalization

Check params.json for zero std values:
```bash
python -c "import json; p=json.load(open('ml_data/params.json')); print([f for f in p['features'] if f['std']==0])"
```

### Latency exceeds 70ms

Profile the inference pipeline:
```bash
python -m cProfile -o profile.stats apps/ml/predict.py
python -c "import pstats; p=pstats.Stats('profile.stats'); p.sort_stats('cumtime'); p.print_stats(10)"
```

## Migration from Previous Version

If upgrading from a version with statistical features:

1. **Backup old models**: Already done in `ml_models/backup/`
2. **Regenerate params.json**: `python apps/ml/generate_params.py`
3. **Retrain models**: `python apps/ml/train.py`
4. **Validate**: `python apps/ml/validate_models.py`

## References

- Feature specification: `specs/011-raw-feature-pipeline/spec.md`
- Implementation plan: `specs/011-raw-feature-pipeline/plan.md`
- Data model: `specs/011-raw-feature-pipeline/data-model.md`
- Quickstart guide: `specs/011-raw-feature-pipeline/quickstart.md`
