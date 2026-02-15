# ML/DL Inference API Endpoint

**Feature 008**: ML/DL Inference API for real-time tremor prediction

## Overview

This Django app provides a REST API endpoint for deploying trained machine learning and deep learning models for tremor prediction. Doctors and smart glove devices can send sensor data to receive immediate tremor predictions with severity assessments.

## Features

### User Story 1 (P1-MVP): Basic Inference
- **Endpoint**: `POST /api/inference/`
- **Authentication**: JWT token required (doctor or patient role)
- **Default model**: Configured via `settings.DEFAULT_INFERENCE_MODEL`
- **Response**: `prediction` (boolean), `severity` (0-3), `timestamp`
- **Performance**: <2 seconds response time (95th percentile)

### User Story 2 (P2): Model Selection
- **Query parameter**: `?model=rf|svm|lstm|cnn_1d`
- **Supported models**:
  - `rf`: Random Forest (ML, ~50-100ms)
  - `svm`: Support Vector Machine (ML, ~50-100ms)
  - `lstm`: Long Short-Term Memory (DL, ~300-500ms)
  - `cnn_1d`: 1D Convolutional Neural Network (DL, ~300-500ms)
- **Response**: Includes `model_used` field

### User Story 3 (P3): Enhanced Metadata
- **Additional response fields**:
  - `confidence_score`: Model confidence (0.0-1.0)
  - `inference_time_ms`: Actual inference duration
  - `model_version`: Model version identifier
  - `input_validation`: Data quality assessment
    - `data_quality`: "good", "degraded", or "poor"
    - `missing_values`: NaN/Inf detection
    - `out_of_range_values`: Values outside typical sensor range

## API Usage

### Basic Request (Default Model)

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "sensor_data": [
      [0.12, -0.45, 0.89, -1.23, 2.34, -0.56],
      [0.15, -0.43, 0.91, -1.20, 2.30, -0.54],
      ...
    ]
  }'
```

**Response**:
```json
{
  "prediction": true,
  "severity": 2,
  "model_used": "rf",
  "confidence_score": 0.87,
  "inference_time_ms": 423,
  "model_version": "rf_v1.0_2026-02-10",
  "input_validation": {
    "data_quality": "good",
    "missing_values": false,
    "out_of_range_values": false
  },
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

### Model Selection Request

```bash
curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"sensor_data": [[...]]}'
```

## Input Formats

### Deep Learning Models (LSTM, 1D-CNN)
- **Format**: 2D array with shape `(128, 6)`
- **Description**: 128 timesteps × 6 axes (3 accelerometer + 3 gyroscope)
- **Example**: `[[0.12, -0.45, ...], [0.15, -0.43, ...], ...]`  (128 rows)

### Machine Learning Models (RF, SVM)
- **Format**: 1D array with 18 engineered features
- **Description**: Statistical features extracted from sensor data
- **Example**: `[0.34, -1.23, 2.45, ..., -0.34]` (18 values)

## Error Responses

### 400 Bad Request - Invalid Input
```json
{
  "error": "Invalid input shape: expected (128, 6), received (100, 6)",
  "error_code": "INVALID_INPUT_SHAPE"
}
```

### 400 Bad Request - Invalid Model
```json
{
  "error": "Invalid model name: gpt4",
  "error_code": "MODEL_NOT_FOUND",
  "available_models": ["rf", "svm", "lstm", "cnn_1d"],
  "suggestion": "Please select from available models"
}
```

### 401 Unauthorized
```json
{
  "error": "Invalid or expired authentication token",
  "error_code": "UNAUTHORIZED"
}
```

### 413 Payload Too Large
```json
{
  "error": "Request payload too large. Maximum 100KB allowed.",
  "error_code": "PAYLOAD_TOO_LARGE"
}
```

### 503 Service Unavailable
```json
{
  "error": "Model file not found: lstm. Please ensure Feature 006 is complete.",
  "error_code": "MODEL_UNAVAILABLE"
}
```

### 504 Gateway Timeout
```json
{
  "error": "Inference took 5234ms (>5000ms limit)",
  "error_code": "INFERENCE_TIMEOUT"
}
```

## Dependencies

### Required Features
- **Feature 004**: ML/DL Data Preparation (data format definitions)
- **Feature 005**: ML Models Training (RF, SVM models)
- **Feature 006**: DL Models Training (LSTM, 1D-CNN models)

### Model Files Location
- **ML models**: `backend/ml_models/models/*.pkl` + `*.json`
- **DL models**: `backend/dl_models/models/*.h5` + `*.json`

## Configuration

### Django Settings

```python
# backend/tremoai_backend/settings.py

# Model paths
ML_MODELS_DIR = BASE_DIR / 'ml_models' / 'models'
DL_MODELS_DIR = BASE_DIR / 'dl_models' / 'models'

# Default model for inference
DEFAULT_INFERENCE_MODEL = 'rf'  # Options: rf, svm, lstm, cnn_1d
```

## Performance

### Model Caching
- Models are loaded once and cached in memory
- First request: 500ms-2s (includes model loading)
- Subsequent requests: <5ms cache hit

### Inference Times
- **ML models (RF, SVM)**: 50-100ms
- **DL models (LSTM, 1D-CNN)**: 300-500ms
- **Total API response**: <2 seconds (95th percentile)

### Concurrency
- Models are thread-safe for concurrent inference
- Supports 100+ concurrent requests without blocking
- No model reloading needed for concurrent access

## Logging

All inference requests are logged to:
- **Console**: Django logger output (INFO level)
- **Database**: `InferenceLog` model for audit trail
- **Log fields**: user, model_used, prediction, severity, confidence, inference_time, timestamp

## Development

### Run Migrations
```bash
cd backend
python manage.py makemigrations inference
python manage.py migrate inference
```

### Test Inference Endpoint
```bash
# Obtain JWT token
curl -X POST http://localhost:8000/api/auth/login/ \
  -d '{"username": "doctor1", "password": "password"}'

# Use token for inference
export TOKEN="your_jwt_token_here"

curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [[0.1, -0.2, ...]]}'
```

## Architecture

### Components
- **ModelCache**: Singleton for caching loaded models
- **ModelLoader**: Load .pkl and .h5 model files
- **PreprocessingService**: Auto-detect model type and preprocess data
- **InferenceService**: Orchestrate inference workflow
- **SeverityMapper**: Map probabilities to 0-3 severity scale
- **InputValidationService**: Assess data quality
- **InferenceAPIView**: Main API endpoint

### Workflow
1. Authenticate user (JWT)
2. Validate request payload
3. Parse model selection (query parameter or default)
4. Assess input data quality
5. Load model (with caching)
6. Preprocess input data
7. Execute model prediction
8. Map probability to severity
9. Log to database
10. Return JSON response

## Troubleshooting

### "Model file not found" error
**Cause**: Models from Features 005/006 not trained yet

**Solution**: Complete ML/DL model training
```bash
cd backend/ml_models
python train_ml_models.py  # Feature 005

cd backend/dl_models
python train_dl_models.py  # Feature 006
```

### "Invalid input shape" error
**Cause**: Input format doesn't match model type

**Solution**:
- For DL models: Send 128×6 array (2D)
- For ML models: Send 18 features (1D)

### Slow inference (>2 seconds)
**Cause**: First request loads model from disk

**Solution**: Normal behavior for first request. Subsequent requests use cache.

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourproject/issues
- Documentation: See `specs/008-ml-inference-api/`
- Planning docs: `specs/008-ml-inference-api/plan.md`
- API contract: `specs/008-ml-inference-api/contracts/inference-api.yaml`
