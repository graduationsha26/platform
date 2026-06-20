# Feature Specification: ML/DL Inference API Endpoint

**Feature Branch**: `008-ml-inference-api`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "2.5 Deployment - Django ML/DL API Endpoint: REST endpoint: POST sensor data → load selected model → return tremor prediction + severity. Support switching models."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Tremor Prediction via API (Priority: P1-MVP)

A doctor or smart glove device sends real-time sensor data to the API and receives an immediate tremor prediction with severity assessment. The system uses a pre-selected deployed model to analyze the sensor readings and return actionable diagnostic information.

**Why this priority**: This is the core value proposition - deploying trained models for real-world tremor detection. Without this, the ML/DL models developed in Features 005 and 006 cannot be used in clinical practice. This is the minimum viable deployment that enables the platform to assist doctors with Parkinson's tremor monitoring.

**Independent Test**: Can be fully tested by sending a POST request with valid sensor data (6 axes × 128 timesteps from Feature 004 format) to the inference endpoint and verifying that a tremor prediction (detected/not detected) and severity level (0-3) are returned in JSON format within 2 seconds.

**Acceptance Scenarios**:

1. **Given** a trained model is deployed and configured as default, **When** a doctor sends POST request with valid 6-axis sensor data (128 timesteps), **Then** the system returns JSON response with `prediction` (boolean: tremor detected/not detected), `severity` (integer 0-3), and `timestamp` within 2 seconds
2. **Given** sensor data indicates clear tremor pattern, **When** inference request is processed, **Then** prediction is `true` (tremor detected) and severity is 1-3 (mild/moderate/severe)
3. **Given** sensor data indicates no tremor (stable readings), **When** inference request is processed, **Then** prediction is `false` (no tremor) and severity is 0 (none)
4. **Given** multiple consecutive inference requests, **When** sent within 1 minute, **Then** each request completes independently with consistent results for identical input data
5. **Given** an authenticated doctor user with valid JWT token, **When** making inference request, **Then** request is processed successfully
6. **Given** an unauthenticated request (no JWT token), **When** inference request is made, **Then** system returns 401 Unauthorized error

---

### User Story 2 - Model Selection for Inference (Priority: P2)

A doctor or researcher can specify which trained model (RF, SVM, LSTM, 1D-CNN) to use for a specific inference request, enabling comparison of different models' predictions on the same patient data and allowing selection of the most appropriate model for each clinical scenario.

**Why this priority**: After MVP deployment, doctors need flexibility to compare model performance in real clinical scenarios. Feature 007 provides offline comparison, but this enables real-time model switching to validate deployment decisions or adjust to specific patient characteristics. This builds on the MVP by adding model selection capability without changing the core inference flow.

**Independent Test**: Can be tested independently by sending inference requests with different `model` query parameters (`?model=rf`, `?model=svm`, `?model=lstm`, `?model=cnn_1d`) and verifying that each request uses the specified model (confirmed by different inference times and prediction characteristics documented in Feature 007).

**Acceptance Scenarios**:

1. **Given** all 4 models (RF, SVM, LSTM, 1D-CNN) are trained and deployed, **When** doctor sends request with `?model=rf` query parameter, **Then** system uses Random Forest model for inference and includes `model_used: "rf"` in response
2. **Given** doctor sends request with `?model=lstm`, **When** processing DL model inference, **Then** system loads the LSTM model (.h5 file) and returns prediction with `model_used: "lstm"` in response
3. **Given** doctor sends request without specifying model parameter, **When** inference is processed, **Then** system uses the default deployed model (configured in settings) and includes `model_used: "[default_model_name]"` in response
4. **Given** doctor sends request with invalid model name `?model=invalid_model`, **When** system validates model parameter, **Then** returns 400 Bad Request with error message listing valid model options: "rf", "svm", "lstm", "cnn_1d"
5. **Given** doctor sends request for a model that hasn't been trained yet (e.g., `?model=lstm` when Feature 006 incomplete), **When** system attempts to load model, **Then** returns 503 Service Unavailable with error "Model not available: lstm. Please complete model training."

---

### User Story 3 - Enhanced Inference Metadata and Debugging (Priority: P3)

The API response includes additional metadata such as confidence scores, inference time, model version, and input validation details to help doctors understand prediction reliability and enable technical debugging of model performance in production.

**Why this priority**: While not required for basic operation, metadata helps doctors assess prediction confidence and helps developers monitor and troubleshoot model performance in production. This is a polish feature that enhances trust and debuggability but doesn't change core functionality.

**Independent Test**: Can be tested by sending inference requests and verifying that response includes additional fields: `confidence_score` (0-1 float), `inference_time_ms` (integer), `model_version` (string), `input_validation` (object with data quality flags) beyond the basic prediction and severity.

**Acceptance Scenarios**:

1. **Given** a valid inference request, **When** prediction is generated, **Then** response includes `confidence_score` field (0.0 to 1.0 float) indicating model's confidence in the prediction
2. **Given** inference is processed, **When** response is returned, **Then** includes `inference_time_ms` field showing actual inference duration in milliseconds
3. **Given** a trained model with metadata, **When** inference uses that model, **Then** response includes `model_version` field (e.g., "rf_v1.0_2026-02-15") from model's metadata JSON file
4. **Given** incoming sensor data, **When** system validates input before inference, **Then** response includes `input_validation` object with fields: `data_quality` (good/degraded/poor), `missing_values` (boolean), `out_of_range_values` (boolean)
5. **Given** sensor data with missing values or out-of-range readings, **When** validation detects issues, **Then** `input_validation.data_quality` is "degraded" or "poor" and inference proceeds with warning in response
6. **Given** doctor needs to compare multiple models on same data, **When** sending batch inference request with `models` array parameter, **Then** system returns array of predictions, one for each specified model, enabling side-by-side comparison

---

### Edge Cases

- **What happens when sensor data is incomplete (< 128 timesteps)?**
  System should return 400 Bad Request with clear error message: "Invalid input: expected 128 timesteps, received [N]". Partial data cannot produce reliable predictions.

- **What happens when sensor data format doesn't match expected shape (not 6 axes)?**
  System should validate input shape and return 400 Bad Request: "Invalid input shape: expected (128, 6), received ([actual_shape])".

- **How does system handle model loading failures (corrupted .pkl or .h5 files)?**
  System should detect corrupted models on startup or first request, log error, and return 503 Service Unavailable: "Model unavailable due to loading error. Please contact administrator."

- **What happens when inference takes longer than expected (> 5 seconds)?**
  System should enforce timeout, abort inference, and return 504 Gateway Timeout: "Inference timeout exceeded. Please try again."

- **How does system handle concurrent requests to the same model?**
  System should support concurrent inference without model reloading. Model should be loaded once and reused for multiple requests. Thread-safe inference required.

- **What happens when requested model doesn't exist in deployment?**
  System should return 400 Bad Request with specific error: "Model '[model_name]' not found. Available models: [list]". Do not expose file paths or internal structure.

- **How does API handle different data preprocessing requirements for ML vs DL models?**
  System should automatically apply correct preprocessing based on model type:
  - ML models (RF, SVM): Expect 18 engineered features from Feature 004
  - DL models (LSTM, 1D-CNN): Expect raw 128×6 sequences
  System should detect model type from file extension (.pkl vs .h5) and apply appropriate preprocessing automatically.

- **What happens when JWT token is expired or invalid?**
  System should return 401 Unauthorized: "Invalid or expired authentication token" and reject inference request. No inference should be performed without valid authentication.

- **What happens if client sends extremely large payload (e.g., 1MB of sensor data)?**
  System should enforce request size limit (e.g., max 100KB for single inference) and return 413 Payload Too Large if exceeded.

- **How does system handle rapid successive requests from same user (rate limiting)?**
  No rate limiting enforced for MVP. Doctors should be able to make unlimited inference requests during patient monitoring sessions. Rate limiting may be added in future based on production load analysis and abuse patterns. System should handle concurrent requests efficiently (per FR-017).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide REST API endpoint at `/api/inference/` accepting POST requests with JSON payload containing sensor data
- **FR-002**: System MUST accept sensor data in two formats: (a) raw sequences (128 timesteps × 6 axes) for DL models, (b) engineered features (18 features) for ML models
- **FR-003**: System MUST validate incoming sensor data format and shape before inference, returning specific error messages for invalid inputs
- **FR-004**: System MUST support model selection via `model` query parameter with values: "rf", "svm", "lstm", "cnn_1d"
- **FR-005**: System MUST load and cache ML models (.pkl files via joblib) and DL models (.h5 files via tensorflow.keras) on first use
- **FR-006**: System MUST return JSON response with minimum fields: `prediction` (boolean), `severity` (integer 0-3), `timestamp` (ISO 8601)
- **FR-007**: System MUST complete inference and return response within 2 seconds for single sample (P1), 5 seconds for enhanced metadata (P3)
- **FR-008**: System MUST use default model (configured in Django settings) when `model` parameter is not provided
- **FR-009**: System MUST require authentication via JWT token (patient or doctor role) for all inference requests
- **FR-010**: System MUST log all inference requests with: user ID, timestamp, model used, prediction result, inference time
- **FR-011**: System MUST return appropriate HTTP status codes: 200 (success), 400 (invalid input), 401 (unauthorized), 503 (model unavailable), 504 (timeout)
- **FR-012**: System MUST apply correct preprocessing automatically based on model type: feature extraction for ML models, sequence normalization for DL models
- **FR-013**: System MUST return `model_used` field in response indicating which model was used for inference (P2)
- **FR-014**: System MUST include `confidence_score` (0.0-1.0 float) in response when available from model (P3)
- **FR-015**: System MUST include `inference_time_ms` field showing actual inference duration (P3)
- **FR-016**: System MUST validate that requested model exists before attempting inference, returning 400 Bad Request with available model list if not found
- **FR-017**: System MUST support concurrent inference requests without blocking or model reloading
- **FR-018**: System MUST enforce request size limit (max 100KB) and return 413 Payload Too Large if exceeded
- **FR-019**: System MUST map model probability outputs to severity levels: 0 (no tremor), 1 (mild: 0.3-0.5 probability), 2 (moderate: 0.5-0.7), 3 (severe: >0.7)
- **FR-020**: System MUST include `input_validation` object in response with data quality assessment when enhanced metadata is enabled (P3)

### Key Entities

- **Inference Request**: Represents a single prediction request containing sensor data, optional model selection parameter, user authentication token, and timestamp. Each request is independent and stateless.

- **Inference Response**: Represents the prediction result with core fields (prediction, severity, timestamp) and optional metadata fields (confidence score, model used, inference time, input validation). Response format must be consistent across all model types.

- **Deployed Model**: Represents a trained ML/DL model loaded into memory and ready for inference. Contains model object (scikit-learn or TensorFlow), metadata (name, version, training date), and preprocessing requirements. Models are cached after first load.

- **Model Metadata**: Information about each trained model stored alongside model files (.json files from Features 005/006) including accuracy metrics, training date, version number, expected input format, and preprocessing requirements.

- **Sensor Data Input**: Structured data from smart glove containing either raw sequences (128×6 for DL) or engineered features (18 features for ML). Must conform to Feature 004 data format specifications.

- **Severity Assessment**: Categorical rating (0-3 integer) derived from model prediction probability, representing clinical tremor intensity: 0=none, 1=mild, 2=moderate, 3=severe. Thresholds defined in FR-019.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Doctors can send sensor data and receive tremor predictions with severity assessment in under 2 seconds for 95% of requests
- **SC-002**: System correctly handles 100 concurrent inference requests without errors or timeouts
- **SC-003**: Prediction accuracy in production matches offline validation accuracy from Feature 007 (>95% for deployed model) when tested on 100 real patient samples
- **SC-004**: All 4 trained models (RF, SVM, LSTM, 1D-CNN) can be selected and used for inference via query parameter with response times matching Feature 007 benchmarks (ML models <100ms, DL models <500ms)
- **SC-005**: Invalid inputs (wrong format, missing data, authentication failures) are rejected with clear error messages, with 0% false accepts
- **SC-006**: System maintains 99.9% uptime during 1-week production trial with real patient monitoring
- **SC-007**: Doctors successfully switch between different models for comparison in 100% of test scenarios without API errors
- **SC-008**: API response format is consistent and parsable by frontend/device clients in 100% of successful requests
- **SC-009**: All inference requests are logged with complete metadata (user, model, result, timing) enabling audit trail and performance monitoring
- **SC-010**: Enhanced metadata (confidence, inference time, validation) when enabled adds <100ms overhead to response time
