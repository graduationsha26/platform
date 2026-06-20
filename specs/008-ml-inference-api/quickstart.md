# Quickstart: ML/DL Inference API Endpoint

**Feature**: 008-ml-inference-api
**Date**: 2026-02-16
**Purpose**: Quick integration guide for using the inference API

## Prerequisites

Before using the inference API, ensure:

1. ✅ **Feature 004** (ML/DL Data Preparation) is complete
   - Data preprocessing utilities available
   - Test datasets available in `backend/ml_data/processed/`

2. ✅ **Feature 005** (ML Models Training) is complete
   - RF and SVM models trained: `backend/ml_models/models/*.pkl`
   - Model metadata files: `backend/ml_models/models/*.json`

3. ✅ **Feature 006** (DL Models Training) is complete
   - LSTM and 1D-CNN models trained: `backend/dl_models/models/*.h5`
   - Model metadata files: `backend/dl_models/models/*.json`

4. ✅ **Authentication** is configured
   - JWT authentication enabled (Feature 001)
   - Valid JWT token available (patient or doctor role)

---

## Installation

### 1. Ensure Dependencies Installed

The inference API uses libraries already installed for Features 005 and 006:

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- Django 5.x
- Django REST Framework
- joblib (for scikit-learn models)
- tensorflow (for Keras models)
- numpy

### 2. Configure Django Settings

Add inference app to `backend/config/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'inference',
]

# Model paths configuration
ML_MODELS_DIR = BASE_DIR / 'ml_models' / 'models'
DL_MODELS_DIR = BASE_DIR / 'dl_models' / 'models'

# Default model selection
DEFAULT_INFERENCE_MODEL = 'rf'  # Options: 'rf', 'svm', 'lstm', 'cnn_1d'
```

### 3. Run Migrations

```bash
python manage.py makemigrations inference
python manage.py migrate
```

This creates the `inference_inferencelog` table for audit trail.

### 4. Include URLs

Add to `backend/config/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('api/inference/', include('inference.urls')),
]
```

### 5. Start Development Server

```bash
python manage.py runserver
```

Server runs at: `http://localhost:8000`

---

## Usage Examples

### Scenario 1: Basic Inference (P1 - MVP)

**Use case**: Doctor sends sensor data for tremor prediction using default model

#### Request

```bash
curl -X POST http://localhost:8000/api/inference/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "sensor_data": [
      [0.12, -0.45, 0.89, -1.23, 2.34, -0.56],
      [0.15, -0.43, 0.91, -1.20, 2.30, -0.54],
      ...
    ]
  }'
```

**Note**: For DL models (default), provide 128 timesteps × 6 axes. For ML models, provide 18 engineered features.

#### Response

```json
{
  "prediction": true,
  "severity": 2,
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

#### Interpretation

- `prediction: true` → Tremor detected
- `severity: 2` → Moderate tremor (probability 0.5-0.7)
- Response time: <2 seconds (first request may take longer for model loading)

---

### Scenario 2: Model Selection (P2)

**Use case**: Researcher compares different models on same patient data

#### Request: Random Forest (ML Model)

```bash
curl -X POST "http://localhost:8000/api/inference/?model=rf" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "sensor_data": [0.34, -1.23, 2.45, -0.67, 1.89, -0.12, 3.45, -2.34, 0.78, -0.98, 1.56, -1.34, 2.12, -0.45, 0.89, -1.67, 2.89, -0.34]
  }'
```

**Note**: For ML models, provide 18 engineered features (not raw sequences).

#### Response

```json
{
  "prediction": true,
  "severity": 2,
  "model_used": "rf",
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

#### Request: LSTM (DL Model)

```bash
curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "sensor_data": [
      [0.12, -0.45, 0.89, -1.23, 2.34, -0.56],
      ...
    ]
  }'
```

#### Response

```json
{
  "prediction": false,
  "severity": 0,
  "model_used": "lstm",
  "timestamp": "2026-02-16T14:33:12.456Z"
}
```

**Interpretation**: Different models may produce different predictions. Use Feature 007 (Model Comparison) to understand model performance characteristics.

---

### Scenario 3: Enhanced Metadata (P3)

**Use case**: Developer debugging inference performance and data quality

#### Request

```bash
curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "X-Include-Metadata: true" \
  -d '{
    "sensor_data": [...]
  }'
```

**Note**: P3 metadata automatically included when enabled in settings. No special header needed in final implementation.

#### Response

```json
{
  "prediction": true,
  "severity": 2,
  "confidence_score": 0.87,
  "model_used": "lstm",
  "model_version": "lstm_v1.0_2026-02-10",
  "inference_time_ms": 423,
  "input_validation": {
    "data_quality": "good",
    "missing_values": false,
    "out_of_range_values": false
  },
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

#### Interpretation

- `confidence_score: 0.87` → Model is 87% confident in prediction
- `inference_time_ms: 423` → Inference took 423ms (within <500ms target for DL models)
- `data_quality: "good"` → Input data passed all validation checks

---

### Scenario 4: Error Handling

#### Invalid Model Selection

```bash
curl -X POST "http://localhost:8000/api/inference/?model=invalid_model" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{"sensor_data": [...]}'
```

**Response** (400 Bad Request):

```json
{
  "error": "Model not found: invalid_model",
  "error_code": "MODEL_NOT_FOUND",
  "available_models": ["rf", "svm", "lstm", "cnn_1d"],
  "suggestion": "Please select from available models"
}
```

#### Invalid Input Shape

```bash
curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{
    "sensor_data": [
      [0.12, -0.45, 0.89]
    ]
  }'
```

**Response** (400 Bad Request):

```json
{
  "error": "Invalid input shape: expected (128, 6), received (1, 3)",
  "error_code": "INVALID_INPUT_SHAPE"
}
```

#### Missing Authentication

```bash
curl -X POST "http://localhost:8000/api/inference/" \
  -d '{"sensor_data": [...]}'
```

**Response** (401 Unauthorized):

```json
{
  "error": "Invalid or expired authentication token",
  "error_code": "UNAUTHORIZED"
}
```

---

## Frontend Integration

### React Example (using fetch)

```javascript
// frontend/src/services/inferenceService.js

const API_BASE_URL = 'http://localhost:8000/api';

export async function performInference(sensorData, modelName = 'rf') {
  const token = localStorage.getItem('jwt_token');

  const response = await fetch(`${API_BASE_URL}/inference/?model=${modelName}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      sensor_data: sensorData
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Inference failed');
  }

  return await response.json();
}

// Usage in component
import { performInference } from './services/inferenceService';

async function handleInference() {
  try {
    const sensorData = [...]; // 128×6 array from glove or file upload
    const result = await performInference(sensorData, 'lstm');

    console.log('Prediction:', result.prediction);
    console.log('Severity:', result.severity);
  } catch (error) {
    console.error('Inference error:', error.message);
  }
}
```

### React Example (with axios)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add JWT token to all requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function performInference(sensorData, modelName = 'rf') {
  const { data } = await api.post('/inference/', {
    sensor_data: sensorData
  }, {
    params: { model: modelName }
  });

  return data;
}
```

---

## Python Client Example

For testing or backend integrations:

```python
import requests
import json

API_URL = 'http://localhost:8000/api/inference/'
JWT_TOKEN = 'your_jwt_token_here'

def perform_inference(sensor_data, model='rf'):
    """
    Perform tremor inference using TremoAI API

    Args:
        sensor_data: List[List[float]] for DL models or List[float] for ML models
        model: 'rf', 'svm', 'lstm', or 'cnn_1d'

    Returns:
        dict: Inference result
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {JWT_TOKEN}'
    }

    payload = {
        'sensor_data': sensor_data
    }

    params = {'model': model} if model else {}

    response = requests.post(API_URL, json=payload, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        error_data = response.json()
        raise Exception(f"Inference failed: {error_data.get('error')}")

# Example usage
if __name__ == '__main__':
    # ML model example (18 features)
    ml_features = [0.34, -1.23, 2.45, -0.67, 1.89, -0.12, 3.45, -2.34, 0.78, -0.98, 1.56, -1.34, 2.12, -0.45, 0.89, -1.67, 2.89, -0.34]
    result = perform_inference(ml_features, model='rf')
    print(f"Prediction: {result['prediction']}, Severity: {result['severity']}")

    # DL model example (128×6 sequences)
    # dl_sequences = load_sensor_data()  # Load actual data
    # result = perform_inference(dl_sequences, model='lstm')
```

---

## Testing Scenarios

### Test 1: Verify Default Model Works

```bash
# Should use default model (rf) and return valid response
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"sensor_data": [0.34, -1.23, 2.45, -0.67, 1.89, -0.12, 3.45, -2.34, 0.78, -0.98, 1.56, -1.34, 2.12, -0.45, 0.89, -1.67, 2.89, -0.34]}'

# Expected: 200 OK with prediction, severity, timestamp
```

### Test 2: Verify Model Switching

```bash
# Test all 4 models
for model in rf svm lstm cnn_1d; do
  echo "Testing model: $model"
  curl -X POST "http://localhost:8000/api/inference/?model=$model" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d '{"sensor_data": [...]}'
done

# Expected: Each model returns valid response with model_used field
```

### Test 3: Verify Authentication

```bash
# Without token
curl -X POST http://localhost:8000/api/inference/ \
  -d '{"sensor_data": [...]}'

# Expected: 401 Unauthorized

# With invalid token
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer invalid_token" \
  -d '{"sensor_data": [...]}'

# Expected: 401 Unauthorized
```

### Test 4: Verify Error Handling

```bash
# Invalid shape
curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"sensor_data": [[1, 2, 3]]}'  # Wrong shape

# Expected: 400 Bad Request with INVALID_INPUT_SHAPE

# Invalid model
curl -X POST "http://localhost:8000/api/inference/?model=gpt4" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"sensor_data": [...]}'

# Expected: 400 Bad Request with MODEL_NOT_FOUND
```

### Test 5: Performance Benchmark

```bash
# Measure inference time (should be <2 seconds)
time curl -X POST "http://localhost:8000/api/inference/?model=lstm" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d @test_sensor_data.json

# First request: ~2-3s (includes model loading)
# Subsequent requests: <1s (model cached)
```

---

## Troubleshooting

### Issue: "Model not found" error

**Cause**: Model files not trained yet (Features 005/006 incomplete)

**Solution**:
```bash
# Check if model files exist
ls backend/ml_models/models/
ls backend/dl_models/models/

# Complete Feature 005 (ML models) and/or Feature 006 (DL models)
```

### Issue: "Invalid input shape" error

**Cause**: Mismatch between input data format and model type

**Solution**:
- ML models (rf, svm): Provide 18 engineered features (single array)
- DL models (lstm, cnn_1d): Provide 128×6 raw sequences (2D array)

### Issue: Slow inference (>5 seconds)

**Cause**: Model not cached, loading on every request

**Solution**:
- First request per model is always slower (loading time)
- Subsequent requests should be fast (<2s)
- Restart Django server to clear cache if needed

### Issue: "401 Unauthorized" even with valid token

**Cause**: JWT token expired or malformed

**Solution**:
```bash
# Obtain new token from authentication endpoint
curl -X POST http://localhost:8000/api/auth/login/ \
  -d '{"username": "doctor1", "password": "password"}'

# Use the returned access token
```

---

## Next Steps

1. **Integrate with Real-Time Pipeline** (Feature 002)
   - Send sensor data from MQTT handler to inference API
   - Stream predictions via WebSocket to doctors

2. **Build Frontend UI** (Future feature)
   - Display real-time predictions
   - Allow model selection via dropdown
   - Show confidence scores and inference times

3. **Analytics Dashboard** (Feature 003)
   - Aggregate inference logs for model usage statistics
   - Track prediction accuracy over time
   - Monitor inference performance

4. **Production Deployment** (Out of scope for graduation project)
   - Load balancing for concurrent requests
   - Model versioning and rollback
   - A/B testing for model comparison

---

## API Reference

Full API documentation: [contracts/inference-api.yaml](./contracts/inference-api.yaml)

View interactive API docs:
```bash
# Install Swagger UI (optional)
pip install drf-yasg

# Add to Django settings and visit:
http://localhost:8000/swagger/
```
