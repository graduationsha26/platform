# Research: ML/DL Inference API Endpoint

**Feature**: 008-ml-inference-api
**Date**: 2026-02-16
**Purpose**: Resolve technical unknowns for implementing ML/DL model inference endpoint

## Research Questions

1. How to efficiently load and cache ML/DL models in Django?
2. Are scikit-learn and TensorFlow models thread-safe for concurrent inference?
3. How to automatically detect model type and apply correct preprocessing?
4. What are best practices for validating ML model inputs?
5. How to handle model loading failures and inference errors?
6. What strategies ensure <2 second response time for inference?

---

## R1: Model Loading and Caching Strategy

### Decision: Django App-Level Model Cache with Lazy Loading

**Rationale**:
- Django doesn't have built-in model caching for ML models
- Loading models on every request is prohibitively slow (500ms-2s per load)
- App-level singleton pattern provides simple, effective caching

**Implementation Approach**:

```python
# backend/inference/services.py
class ModelCache:
    """Singleton cache for loaded ML/DL models"""
    _instance = None
    _models = {}  # {model_name: (model_obj, metadata)}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self, model_name):
        """Load model on first access, cache for subsequent requests"""
        if model_name not in self._models:
            self._models[model_name] = self._load_model(model_name)
        return self._models[model_name]
```

**Key Benefits**:
- First request per model: ~500ms-2s (one-time load cost)
- Subsequent requests: <5ms (cache hit)
- Memory efficient: Only loaded models remain in memory
- Simple implementation: No external dependencies

**Alternatives Considered**:
- Redis caching: Rejected - adds external dependency, serialization overhead
- Django cache framework: Rejected - not designed for large binary objects (models)
- Per-request loading: Rejected - too slow, violates <2s requirement

**Limitations**:
- Models loaded into memory of single Django worker process
- If using multiple workers (e.g., gunicorn), each worker has separate cache
- For graduation project single worker sufficient (local development)

---

## R2: Thread Safety for Concurrent Inference

### Decision: Both scikit-learn and TensorFlow Models are Thread-Safe for Prediction

**Rationale**:
- scikit-learn `.predict()` methods are read-only operations, thread-safe after training
- TensorFlow/Keras models are thread-safe for inference when using `model.predict()` (not `model.fit()`)
- No model modification during inference

**Evidence**:
- scikit-learn documentation: "All estimators are safe for concurrent predictions"
- TensorFlow documentation: "Models are thread-safe for inference operations"
- Common production pattern: Single model instance serves multiple requests

**Implementation Guidance**:
- Load model once, cache in memory
- Multiple threads/requests can call `.predict()` simultaneously
- No locking required for inference operations
- DO NOT call `.fit()` or modify model during serving

**Concurrency Limits**:
- CPU-bound inference: Python GIL limits true parallelism
- Practical concurrency: ~4-8 requests benefit from concurrent execution
- Beyond that, requests queue waiting for CPU
- For 100 concurrent requests goal: Requests queue but don't fail

**Performance Expectations**:
- Single request: RF/SVM <100ms, LSTM/CNN <500ms (per Feature 007)
- 10 concurrent requests: ~2-3x slowdown per request (queue + GIL)
- 100 concurrent requests: Longer queue but eventual completion
- No race conditions or data corruption

---

## R3: Automatic Model Type Detection and Preprocessing

### Decision: File Extension-Based Detection + Metadata JSON

**Rationale**:
- File extensions reliably indicate model type: `.pkl` = ML, `.h5` = DL
- Metadata JSON files (from Features 005/006) contain preprocessing requirements
- No need for complex introspection or heuristics

**Detection Logic**:

```python
def detect_model_type(model_path: str) -> str:
    """Detect model type from file extension"""
    if model_path.endswith('.pkl'):
        return 'ml'  # Scikit-learn: RF, SVM
    elif model_path.endswith('.h5') or model_path.endswith('.keras'):
        return 'dl'  # TensorFlow/Keras: LSTM, CNN
    else:
        raise ValueError(f"Unsupported model format: {model_path}")
```

**Preprocessing Mapping**:

| Model Type | Input Format | Preprocessing Steps |
|------------|--------------|---------------------|
| ML (RF, SVM) | 18 engineered features | 1. Validate shape (N, 18)<br>2. Feature scaling (StandardScaler - params in metadata)<br>3. No sequence handling |
| DL (LSTM, CNN) | 128×6 raw sequences | 1. Validate shape (N, 128, 6)<br>2. Normalize per axis (mean/std in metadata)<br>3. Reshape if needed |

**Metadata JSON Structure** (from Features 005/006):

```json
{
  "model_type": "ml" | "dl",
  "preprocessing": {
    "scaler_params": {...},  // For ML models
    "normalization": {...}   // For DL models
  },
  "input_shape": [128, 6] | [18],
  "expected_features": [...]
}
```

**Preprocessing Service**:

```python
class PreprocessingService:
    def preprocess(self, data, model_type, metadata):
        if model_type == 'ml':
            return self._preprocess_ml(data, metadata)
        elif model_type == 'dl':
            return self._preprocess_dl(data, metadata)
```

**Alternatives Considered**:
- Runtime model introspection: Rejected - unreliable, adds complexity
- Client specifies preprocessing: Rejected - error-prone, violates API simplicity
- Unified preprocessing for all models: Rejected - different requirements for ML vs DL

---

## R4: Input Validation Best Practices

### Decision: Multi-Layer Validation (DRF Serializer + Custom Validators)

**Rationale**:
- Django REST Framework serializers provide schema validation
- Custom validators add ML-specific checks (shape, range, data quality)
- Early validation prevents wasted inference compute

**Validation Layers**:

**Layer 1: DRF Serializer (Schema Validation)**
```python
class InferenceRequestSerializer(serializers.Serializer):
    sensor_data = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        required=True
    )
    model = serializers.ChoiceField(
        choices=['rf', 'svm', 'lstm', 'cnn_1d'],
        required=False
    )
```

**Layer 2: Custom Validators (Shape & Range)**
```python
def validate_sensor_data(data, expected_shape):
    # Check dimensions
    if np.array(data).shape != expected_shape:
        raise ValidationError(f"Invalid shape: expected {expected_shape}")

    # Check value ranges (sensor readings typically -10 to +10)
    arr = np.array(data)
    if np.any(arr < -50) or np.any(arr > 50):
        raise ValidationError("Sensor values out of valid range")

    # Check for NaN/Inf
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValidationError("Invalid values detected (NaN/Inf)")
```

**Layer 3: Data Quality Assessment (P3 Feature)**
```python
def assess_data_quality(data):
    arr = np.array(data)
    quality = {
        'missing_values': np.any(np.isnan(arr)),
        'out_of_range': np.any((arr < -10) | (arr > 10)),
        'data_quality': 'good'  # 'good', 'degraded', 'poor'
    }

    if quality['missing_values'] or quality['out_of_range']:
        quality['data_quality'] = 'degraded'

    return quality
```

**Validation Strategy**:
- Fail fast: Invalid schema → 400 Bad Request immediately
- Warn on quality issues: Degraded data → proceed with warning in response
- Log validation failures: Audit trail for debugging

**Alternatives Considered**:
- Pydantic models: Rejected - adds dependency, DRF sufficient
- No validation (trust client): Rejected - unsafe, causes cryptic model errors
- Strict validation (reject degraded data): Rejected - too restrictive for clinical use

---

## R5: Error Handling and Recovery Patterns

### Decision: Hierarchical Error Handling with Specific Error Codes

**Rationale**:
- Different error types require different responses (4xx vs 5xx)
- Clients need specific error messages to diagnose issues
- Graceful degradation for partial failures

**Error Hierarchy**:

```python
# backend/inference/exceptions.py

class InferenceError(Exception):
    """Base exception for inference errors"""
    status_code = 500
    default_message = "Inference error occurred"

class ModelNotFoundError(InferenceError):
    status_code = 400
    default_message = "Requested model not available"

class ModelLoadError(InferenceError):
    status_code = 503
    default_message = "Model loading failed"

class InvalidInputError(InferenceError):
    status_code = 400
    default_message = "Invalid input data"

class InferenceTimeoutError(InferenceError):
    status_code = 504
    default_message = "Inference timeout exceeded"
```

**Error Response Format** (per constitutional API standards):

```json
{
  "error": "Requested model not available: lstm",
  "error_code": "MODEL_NOT_FOUND",
  "available_models": ["rf", "svm", "cnn_1d"],
  "suggestion": "Complete Feature 006 training or select available model"
}
```

**Handling Strategy by Error Type**:

| Error Type | HTTP Code | Action | User Message |
|------------|-----------|--------|--------------|
| Invalid input shape | 400 | Reject request | "Invalid shape: expected (128, 6), got (...)" |
| Missing model file | 400 | List available | "Model 'lstm' not found. Available: [...]" |
| Corrupted model | 503 | Log + admin alert | "Model unavailable. Contact administrator." |
| Inference timeout | 504 | Abort + retry | "Inference timeout. Please retry." |
| Unexpected error | 500 | Log traceback | "Internal error. Request ID: {uuid}" |

**Recovery Mechanisms**:
- Model loading failure: Fall back to available models, never crash server
- Timeout: Use Python `signal` or threading timeout to abort long-running inference
- Partial failures: For batch inference (P3), return partial results with error list

**Logging Strategy**:
```python
import logging
logger = logging.getLogger(__name__)

try:
    prediction = model.predict(data)
except Exception as e:
    logger.error(f"Inference failed: {e}", extra={
        'model': model_name,
        'user_id': request.user.id,
        'input_shape': data.shape
    })
    raise InferenceError(str(e))
```

**Alternatives Considered**:
- Generic error messages: Rejected - not helpful for debugging
- Expose stack traces: Rejected - security risk, too technical
- Silent failures: Rejected - users need to know about issues

---

## R6: Performance Optimization for <2 Second Response Time

### Decision: Multi-Pronged Optimization Strategy

**Performance Budget Breakdown** (for 2-second total response time):

| Stage | Target Time | Optimization |
|-------|-------------|--------------|
| Request parsing | <10ms | Native DRF serializer (fast) |
| Authentication | <50ms | JWT validation (cached public key) |
| Input validation | <20ms | NumPy vectorized operations |
| Model loading | <5ms | Cache hit (after first load) |
| Preprocessing | <100ms | Vectorized NumPy operations |
| Inference | <500ms | ML: <100ms, DL: <500ms (per Feature 007) |
| Response serialization | <20ms | Native DRF serializer |
| Network overhead | <300ms | Client-side latency (out of control) |
| **TOTAL** | **<2000ms** | **Budget includes buffer for GIL contention** |

**Optimization Techniques**:

**1. Model Caching** (already covered in R1)
- Eliminates 500ms-2s load time on subsequent requests

**2. NumPy Vectorization**
```python
# Instead of Python loops:
for i in range(len(data)):
    scaled_data[i] = (data[i] - mean) / std

# Use NumPy vectorization:
scaled_data = (data - mean) / std  # 10-50x faster
```

**3. Lazy Preprocessing**
- Only apply preprocessing needed for requested model type
- Skip optional validation for performance-critical paths

**4. Response Caching for Identical Inputs** (optional P3 enhancement)
```python
from django.core.cache import cache

def get_inference(data_hash, model_name):
    cache_key = f"inference:{model_name}:{data_hash}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = perform_inference(data, model_name)
    cache.set(cache_key, result, timeout=3600)  # 1 hour
    return result
```

**5. Async I/O for Logging** (don't block response)
```python
# Log asynchronously after response sent
from django.db import transaction

@transaction.non_atomic_requests
def inference_view(request):
    result = perform_inference(request.data)

    # Return response immediately
    response = Response(result)

    # Log asynchronously (after response)
    log_inference_async.delay(result)

    return response
```

**Performance Monitoring**:
```python
import time

start = time.perf_counter()
result = model.predict(data)
inference_time = (time.perf_counter() - start) * 1000  # ms

# Include in response (P3)
return {
    'prediction': result,
    'inference_time_ms': inference_time
}
```

**Alternatives Considered**:
- GPU acceleration: Rejected - not available in local development, unnecessary for graduation project scale
- Model quantization: Rejected - adds complexity, current models already fast enough
- Batch inference optimization: Deferred to P3 (not MVP requirement)
- Async Django views: Rejected - adds complexity, sync views sufficient for <2s target

**Expected Performance**:
- P1 MVP: 95% of requests <2 seconds (meets SC-001)
- P2 Model selection: Same performance (model caching negates switching overhead)
- P3 Enhanced metadata: +50-100ms for quality checks (still <2.5s)

---

## Summary: Key Technical Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Model caching | App-level singleton cache with lazy loading | Simple, effective, no external dependencies |
| Thread safety | Models are thread-safe for concurrent `.predict()` | Standard ML serving pattern, no locking needed |
| Model type detection | File extension (.pkl vs .h5) + metadata JSON | Reliable, simple, leverages existing metadata |
| Input validation | Multi-layer: DRF serializer + custom validators | Fail fast for invalid schema, warn for quality issues |
| Error handling | Hierarchical exceptions with specific HTTP codes | Clear errors for clients, proper 4xx vs 5xx usage |
| Performance | Caching + vectorization + lazy preprocessing | Meets <2s requirement with room for concurrent load |

---

## Dependencies on Other Features

- **Feature 004** (ML/DL Data Preparation): Defines expected input formats (128×6 sequences, 18 features)
- **Feature 005** (ML Models Training): Provides RF/SVM models (.pkl files) and metadata
- **Feature 006** (DL Models Training): Provides LSTM/CNN models (.h5 files) and metadata
- **Feature 007** (Model Comparison): Establishes expected inference times (ML <100ms, DL <500ms)

---

## Open Questions (None - All Resolved)

All technical unknowns have been researched and resolved. Ready to proceed to Phase 1 (Design).
