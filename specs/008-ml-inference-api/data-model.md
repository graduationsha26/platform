# Data Model: ML/DL Inference API Endpoint

**Feature**: 008-ml-inference-api
**Date**: 2026-02-16
**Purpose**: Define data entities and their relationships for ML/DL inference

## Overview

This feature primarily deals with **request/response data structures** rather than persistent database entities. The only persistent entity is `InferenceLog` for audit trail purposes.

---

## Entity 1: Inference Request (API Input Schema)

**Type**: Request DTO (Data Transfer Object) - Not a database model
**Purpose**: Structure sensor data for inference prediction

### Attributes

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `sensor_data` | Array<Array<Float>> | Yes | Shape: (128, 6) for DL or (18,) for ML | Raw sensor readings or engineered features |
| `model` | String | No | Enum: "rf", "svm", "lstm", "cnn_1d" | Model selection (defaults to configured default if omitted) |

### Validation Rules

1. **Shape Validation**:
   - For DL models (lstm, cnn_1d): `sensor_data` must be 128 timesteps × 6 axes
   - For ML models (rf, svm): `sensor_data` must be 18 engineered features
   - API auto-detects based on selected model

2. **Value Range Validation**:
   - Sensor values typically -10 to +10 (accelerometer/gyroscope readings)
   - Warning if values outside -50 to +50 (likely data corruption)
   - Reject if NaN or Inf values detected

3. **Size Constraints**:
   - Maximum request payload: 100KB
   - Prevents abuse and ensures reasonable processing time

### Example: DL Model Request

```json
{
  "sensor_data": [
    [0.12, -0.45, 0.89, -1.23, 2.34, -0.56],
    [0.15, -0.43, 0.91, -1.20, 2.30, -0.54],
    // ... 128 timesteps total
  ],
  "model": "lstm"
}
```

### Example: ML Model Request

```json
{
  "sensor_data": [0.34, -1.23, 2.45, -0.67, ...],  // 18 features
  "model": "rf"
}
```

---

## Entity 2: Inference Response (API Output Schema)

**Type**: Response DTO - Not a database model
**Purpose**: Return prediction results with metadata

### Attributes (Minimum - P1)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prediction` | Boolean | Yes | Tremor detected (true) or not detected (false) |
| `severity` | Integer | Yes | Severity level: 0 (none), 1 (mild), 2 (moderate), 3 (severe) |
| `timestamp` | String (ISO 8601) | Yes | Server timestamp when prediction was generated |

### Additional Attributes (P2 - Model Selection)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model_used` | String | Yes (P2) | Which model was used: "rf", "svm", "lstm", "cnn_1d" |

### Additional Attributes (P3 - Enhanced Metadata)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confidence_score` | Float | Yes (P3) | Model confidence: 0.0 to 1.0 |
| `inference_time_ms` | Integer | Yes (P3) | Inference duration in milliseconds |
| `model_version` | String | Yes (P3) | Model version (e.g., "rf_v1.0_2026-02-15") |
| `input_validation` | Object | Yes (P3) | Data quality assessment |
| └─ `data_quality` | String | Yes | "good", "degraded", or "poor" |
| └─ `missing_values` | Boolean | Yes | Any NaN/missing values detected |
| └─ `out_of_range_values` | Boolean | Yes | Any values outside expected range |

### Severity Mapping Logic

| Prediction Probability | Severity Level | Description |
|------------------------|----------------|-------------|
| < 0.3 | 0 | No tremor detected |
| 0.3 - 0.5 | 1 | Mild tremor |
| 0.5 - 0.7 | 2 | Moderate tremor |
| > 0.7 | 3 | Severe tremor |

### Example: P1 Response (Basic)

```json
{
  "prediction": true,
  "severity": 2,
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

### Example: P2 Response (With Model Selection)

```json
{
  "prediction": true,
  "severity": 2,
  "model_used": "lstm",
  "timestamp": "2026-02-16T14:32:45.123Z"
}
```

### Example: P3 Response (Full Metadata)

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

---

## Entity 3: InferenceLog (Database Model)

**Type**: Django Model (PostgreSQL table)
**Purpose**: Audit trail and analytics for inference requests

### Table: `inference_inferencelog`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, Auto | Primary key |
| `user_id` | Integer | FK → auth_user, NOT NULL | User who made request (from JWT) |
| `model_used` | String(50) | NOT NULL | Model name: "rf", "svm", "lstm", "cnn_1d" |
| `prediction` | Boolean | NOT NULL | Inference result: tremor detected or not |
| `severity` | Integer | NOT NULL, CHECK (0-3) | Severity level: 0-3 |
| `confidence_score` | Float | NULL | Prediction confidence (P3 only) |
| `inference_time_ms` | Integer | NULL | Inference duration in ms (P3 only) |
| `input_shape` | String(50) | NOT NULL | Input data shape for debugging |
| `timestamp` | DateTime | NOT NULL, Auto | When inference was performed |
| `created_at` | DateTime | Auto | Record creation timestamp |

### Relationships

- **User (auth_user)**: Many-to-one relationship
  - Each log entry belongs to one user (doctor or patient)
  - User can have multiple inference logs
  - Used for per-user analytics and audit trail

### Indexes

```sql
CREATE INDEX idx_inferencelog_user_timestamp ON inference_inferencelog(user_id, timestamp DESC);
CREATE INDEX idx_inferencelog_model ON inference_inferencelog(model_used);
CREATE INDEX idx_inferencelog_timestamp ON inference_inferencelog(timestamp DESC);
```

### Usage

- **Audit Trail**: Track all inference requests for compliance
- **Analytics**: Aggregate statistics (most used model, average confidence, etc.)
- **Debugging**: Investigate inference issues by user/model/timestamp
- **Performance Monitoring**: Track inference times over time

### Privacy Considerations

- **No sensor data stored**: Only metadata logged (not actual sensor readings)
- **Compliant with minimal data retention**: Stores outcome, not raw inputs
- **User consent**: Logs tied to authenticated user for traceability

---

## Entity 4: Model Metadata (File-Based, Not Database)

**Type**: JSON file stored alongside model files
**Purpose**: Model configuration and preprocessing requirements
**Location**:
  - `backend/ml_models/models/{model_name}.json`
  - `backend/dl_models/models/{model_name}.json`

### Structure

```json
{
  "model_name": "rf",
  "model_type": "ml",
  "version": "1.0",
  "trained_date": "2026-02-10T12:00:00Z",
  "accuracy": 0.96,
  "input_shape": [18],
  "preprocessing": {
    "scaler_type": "StandardScaler",
    "scaler_params": {
      "mean": [0.12, -0.34, ...],
      "std": [1.23, 0.98, ...]
    }
  },
  "output_type": "binary",
  "expected_inference_time_ms": 45
}
```

### Attributes

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | String | Identifier: "rf", "svm", "lstm", "cnn_1d" |
| `model_type` | String | "ml" or "dl" |
| `version` | String | Model version (semantic versioning) |
| `trained_date` | ISO 8601 | When model was trained |
| `accuracy` | Float | Validation accuracy from training |
| `input_shape` | Array | Expected input dimensions |
| `preprocessing` | Object | Preprocessing configuration |
| `output_type` | String | "binary" (tremor yes/no) or "multiclass" |
| `expected_inference_time_ms` | Integer | Benchmark inference time |

### Usage

- Loaded by `ModelLoader` service
- Validates input shape before inference
- Applies correct preprocessing (scaler params for ML, normalization for DL)
- Included in P3 response (`model_version` field)

---

## Entity 5: Model Cache (In-Memory, Not Persistent)

**Type**: Python singleton object
**Purpose**: Cache loaded models to avoid repeated file I/O

### Structure

```python
{
  "rf": (
    <sklearn.ensemble.RandomForestClassifier object>,
    {metadata from rf_model.json}
  ),
  "lstm": (
    <tensorflow.keras.Model object>,
    {metadata from lstm_model.json}
  ),
  # ... other models
}
```

### Lifecycle

- **Initialization**: Empty cache on Django server start
- **First Request**: Load model from disk, cache in memory
- **Subsequent Requests**: Retrieve from cache (no disk I/O)
- **Cache Invalidation**: Manual server restart (or implement LRU eviction)

### Memory Footprint

| Model | File Size | Memory Size |
|-------|-----------|-------------|
| RF (scikit-learn) | ~5 MB | ~10 MB in memory |
| SVM (scikit-learn) | ~2 MB | ~5 MB in memory |
| LSTM (TensorFlow) | ~15 MB | ~30 MB in memory |
| 1D-CNN (TensorFlow) | ~10 MB | ~20 MB in memory |
| **Total** | ~32 MB | ~65 MB in memory |

### Justification

- 65 MB memory overhead acceptable for local development
- Eliminates 500ms-2s load time per request
- Critical for meeting <2 second response time requirement

---

## Data Flow

### Request Flow (P1 - Basic Inference)

```
1. Client sends POST /api/inference/
   └─> InferenceRequestSerializer validates schema

2. Authentication middleware verifies JWT
   └─> Extracts user_id from token

3. ModelLoader.get_model(model_name)
   └─> If cached: return immediately (<5ms)
   └─> If not cached: load from disk, cache, return (~500ms-2s)

4. PreprocessingService.preprocess(data, model_type, metadata)
   └─> Applies correct preprocessing based on model type

5. InferenceService.predict(model, preprocessed_data)
   └─> Calls model.predict()
   └─> Maps probability to severity (0-3)

6. InferenceLog.objects.create(...)
   └─> Async logging (doesn't block response)

7. Return InferenceResponse
   └─> prediction, severity, timestamp
```

### Response Time Breakdown

| Stage | Time | Cumulative |
|-------|------|------------|
| Request parsing | 10ms | 10ms |
| JWT validation | 50ms | 60ms |
| Model cache hit | 5ms | 65ms |
| Preprocessing | 100ms | 165ms |
| Inference (DL worst case) | 500ms | 665ms |
| Response serialization | 20ms | 685ms |
| **Total (cached)** | **685ms** | **<2s ✓** |

First request (cache miss): Add +500ms-2s for model loading

---

## Relationships Between Entities

```
┌─────────────────────┐
│  User (auth_user)   │
└──────────┬──────────┘
           │ 1:N
           ▼
┌─────────────────────┐      ┌──────────────────────┐
│  InferenceLog       │      │  InferenceRequest    │
│  (Database)         │      │  (Request DTO)       │
└─────────────────────┘      └──────────┬───────────┘
                                        │
                                        │ processed by
                                        ▼
                             ┌──────────────────────┐
                             │  InferenceService    │
                             │  (Business Logic)    │
                             └──────────┬───────────┘
                                        │
                                        │ uses
                                        ▼
                             ┌──────────────────────┐
                             │  Model Cache         │
                             │  (In-Memory)         │
                             └──────────┬───────────┘
                                        │ loads from
                                        ▼
                             ┌──────────────────────┐
                             │  Model Files + JSON  │
                             │  (Filesystem)        │
                             └──────────────────────┘
                                        │
                                        │ returns
                                        ▼
                             ┌──────────────────────┐
                             │  InferenceResponse   │
                             │  (Response DTO)      │
                             └──────────────────────┘
```

---

## Database Schema (Django Models)

### InferenceLog Model

```python
# backend/inference/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid

class InferenceLog(models.Model):
    """Audit log for all inference requests"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inference_logs')
    model_used = models.CharField(max_length=50)
    prediction = models.BooleanField()
    severity = models.IntegerField()  # 0-3
    confidence_score = models.FloatField(null=True, blank=True)
    inference_time_ms = models.IntegerField(null=True, blank=True)
    input_shape = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inference_inferencelog'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['model_used']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"Inference {self.id} - {self.model_used} - {self.timestamp}"
```

---

## Summary

| Entity | Type | Persistence | Purpose |
|--------|------|-------------|---------|
| InferenceRequest | DTO | Transient | API input structure |
| InferenceResponse | DTO | Transient | API output structure |
| InferenceLog | Django Model | PostgreSQL | Audit trail and analytics |
| Model Metadata | JSON File | Filesystem | Model configuration |
| Model Cache | Python Object | Memory | Performance optimization |

**Key Design Decisions**:
- Request/response are DTOs (not database models) for performance
- Only audit data persisted in database (not raw sensor data)
- Model caching essential for <2 second response time requirement
- Metadata JSON files enable flexible preprocessing without code changes
