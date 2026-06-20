# Implementation Plan: ML/DL Inference API Endpoint

**Branch**: `008-ml-inference-api` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-ml-inference-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements a REST API endpoint for deploying trained ML/DL models to perform real-time tremor prediction and severity assessment. Doctors and smart glove devices can send sensor data to receive immediate predictions using any of the 4 trained models (Random Forest, SVM, LSTM, 1D-CNN) with automatic preprocessing, model caching, and comprehensive error handling. The MVP provides a single default model inference endpoint, with P2 adding dynamic model selection and P3 adding enhanced debugging metadata.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework (for RESTful inference endpoint)
**Frontend Stack**: N/A (backend-only feature for MVP - frontend integration via standard API calls)
**Database**: Supabase PostgreSQL (for inference logging only; models not stored in DB)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor) - both roles can request inference
**Testing**: pytest (backend) for API endpoint, model loading, and inference logic
**Project Type**: web (monorepo: backend/ only for this feature)
**Real-time**: Not applicable (synchronous HTTP POST for inference - no WebSocket needed)
**Integration**: Receives preprocessed sensor data (Feature 004 format); loads models from Features 005/006
**AI/ML**:
  - scikit-learn models (.pkl via joblib): Random Forest, SVM
  - TensorFlow/Keras models (.h5 via tf.keras.models.load_model): LSTM, 1D-CNN
  - Model caching in memory for performance
  - Automatic preprocessing based on model type (18 features for ML, 128×6 sequences for DL)
**Performance Goals**:
  - Inference response time <2 seconds (95th percentile)
  - Model loading cached (first request loads, subsequent reuses)
  - Support 100 concurrent inference requests without blocking
  - ML models <100ms inference, DL models <500ms inference (per Feature 007 benchmarks)
**Constraints**:
  - Local development only (no containerization)
  - Models loaded from filesystem (backend/ml_models/ and backend/dl_models/)
  - No GPU acceleration required (CPU inference sufficient for graduation project)
  - Request size limit: 100KB max payload
**Scale/Scope**:
  - 4 models supported: RF, SVM, LSTM, 1D-CNN
  - Single default model for P1-MVP, dynamic selection for P2
  - Stateless inference (no session management for inference state)
  - Concurrent request support (thread-safe model inference)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/` structure
  - ✅ New Django app: `backend/inference/` for inference endpoint
  - ✅ Uses models from existing `backend/ml_models/` and `backend/dl_models/` directories
- [X] **Tech Stack Immutability**: No new frameworks/libraries outside constitutional stack
  - ✅ Django REST Framework (constitutional)
  - ✅ joblib (already required by scikit-learn in Feature 005)
  - ✅ TensorFlow/Keras (already required in Feature 006)
  - ✅ NumPy (already required for data processing)
  - ✅ No new framework introductions
- [X] **Database Strategy**: Uses Supabase PostgreSQL only (no local DB, no other systems)
  - ✅ Inference logging stored in PostgreSQL via Django ORM
  - ✅ No local database or alternative database systems
  - ✅ Models stored as files (not in database) per constitutional AI Model Serving rules
- [X] **Authentication**: Uses JWT via SimpleJWT with patient/doctor roles
  - ✅ All inference endpoints require JWT authentication
  - ✅ Both patient and doctor roles permitted (doctors for clinical use, patients for self-monitoring)
  - ✅ Uses existing authentication middleware
- [X] **Security-First**: All secrets in `.env` files, no hardcoded credentials
  - ✅ No new secrets required (reuses existing Django SECRET_KEY, DB credentials)
  - ✅ Model file paths configurable via Django settings (not hardcoded)
- [X] **Real-time Requirements**: Uses Django Channels WebSocket if real-time needed
  - ✅ N/A - This feature uses synchronous HTTP POST (not real-time streaming)
  - ✅ Inference is request-response, not continuous streaming
- [X] **MQTT Integration**: Uses MQTT subscription if glove data involved
  - ✅ N/A - This feature receives preprocessed data from API client
  - ✅ MQTT integration handled by Feature 002 (Real-Time Pipeline)
  - ✅ This endpoint works with any sensor data source (MQTT, manual upload, etc.)
- [X] **AI Model Serving**: Models served via Django backend (`.pkl` or `.h5`)
  - ✅ CORE FEATURE - Implements constitutional AI model serving requirement
  - ✅ Supports both `.pkl` (scikit-learn) and `.h5` (TensorFlow) formats
  - ✅ Models stored in `backend/ml_models/models/` and `backend/dl_models/models/`
  - ✅ Inference performed server-side (never in browser)
- [X] **API Standards**: REST + JSON, standard HTTP codes, snake_case naming
  - ✅ RESTful endpoint design
  - ✅ JSON request/response bodies
  - ✅ Standard HTTP codes: 200 (success), 400 (invalid input), 401 (unauthorized), 503 (model unavailable), 504 (timeout)
  - ✅ Error format: `{"error": "message"}`
  - ✅ snake_case naming in JSON responses
- [X] **Development Scope**: Local development only (no Docker/CI/CD/production)
  - ✅ Local Django development server only
  - ✅ No Docker, CI/CD, or production configurations
  - ✅ Models loaded from local filesystem

**Result**: ✅ **PASS** - All constitutional principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── inference/                # NEW Django app for ML/DL inference API
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py            # InferenceLog model for audit trail
│   ├── serializers.py       # InferenceRequestSerializer, InferenceResponseSerializer
│   ├── views.py             # InferenceAPIView (handles POST /api/inference/)
│   ├── urls.py              # URL routing: /api/inference/
│   ├── services.py          # Business logic:
│   │                        #   - ModelLoader: Load and cache .pkl/.h5 models
│   │                        #   - PreprocessingService: Auto-detect and preprocess inputs
│   │                        #   - InferenceService: Execute predictions
│   │                        #   - SeverityMapper: Map probabilities to 0-3 scale
│   ├── exceptions.py        # Custom exceptions: ModelNotFoundError, InferenceTimeoutError
│   └── validators.py        # Input validation: shape, format, size checks
├── ml_models/                # EXISTING - Feature 005 (RF, SVM models)
│   └── models/
│       ├── rf_model.pkl
│       ├── rf_model.json
│       ├── svm_model.pkl
│       └── svm_model.json
├── dl_models/                # EXISTING - Feature 006 (LSTM, 1D-CNN models)
│   └── models/
│       ├── lstm_model.h5
│       ├── lstm_model.json
│       ├── cnn_1d_model.h5
│       └── cnn_1d_model.json
├── ml_data/                  # EXISTING - Feature 004 (preprocessing utilities)
│   └── processed/           # Reference for expected data format
│       ├── test_features.npy     # ML format: (N, 18)
│       └── test_sequences.npy    # DL format: (N, 128, 6)
├── config/                   # MODIFIED - Django project settings
│   ├── settings.py          # Add inference app, configure MODEL_PATHS
│   └── urls.py              # Include inference.urls
├── tests/
│   ├── test_inference_api.py          # API endpoint tests (happy path, auth, errors)
│   ├── test_model_loader.py           # Model loading and caching tests
│   ├── test_preprocessing.py          # Input preprocessing tests
│   └── test_inference_service.py      # Inference logic tests
└── .env                      # No changes (reuses existing secrets)

frontend/                     # NOT MODIFIED - No frontend components for MVP
                              # Frontend will call API via standard fetch/axios

specs/008-ml-inference-api/   # NEW - This feature's documentation
├── spec.md                   # Feature specification (COMPLETE)
├── plan.md                   # This file (IN PROGRESS)
├── research.md               # Phase 0 research findings (TO BE GENERATED)
├── data-model.md             # Phase 1 data entities (TO BE GENERATED)
├── quickstart.md             # Phase 1 usage guide (TO BE GENERATED)
├── contracts/                # Phase 1 API contracts (TO BE GENERATED)
│   └── inference-api.yaml   # OpenAPI spec for /api/inference/
└── tasks.md                  # Phase 2 task breakdown (NOT created by /speckit.plan)
```

**Structure Decision**:
- **New Django app**: `backend/inference/` contains all inference-related code
- **No frontend changes**: MVP is backend-only; frontend integration uses standard API calls
- **Reuses existing models**: Loads models from Features 005 and 006 directories
- **Reuses preprocessing patterns**: References Feature 004 data format for validation
- **Inference logging**: `InferenceLog` model stores audit trail in PostgreSQL
- **API endpoint**: Single POST endpoint at `/api/inference/` (matches spec FR-001)
- **Model paths configurable**: Django settings specify model directory paths (no hardcoding)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - All constitutional principles satisfied. No justifications needed.

---

## Phase 0: Research Summary ✅

**Status**: Complete
**Output**: [research.md](./research.md)

### Key Technical Decisions

1. **Model Caching**: App-level singleton cache with lazy loading
   - Eliminates 500ms-2s load time on subsequent requests
   - Simple implementation without external dependencies

2. **Thread Safety**: Both scikit-learn and TensorFlow models are thread-safe for `.predict()`
   - No locking needed for concurrent inference
   - Models loaded once, reused for all requests

3. **Model Type Detection**: File extension (.pkl vs .h5) + metadata JSON
   - Reliable and simple
   - Enables automatic preprocessing selection

4. **Input Validation**: Multi-layer validation (DRF serializer + custom validators)
   - Fail fast for invalid schema
   - Warn on data quality issues

5. **Error Handling**: Hierarchical exceptions with specific HTTP codes
   - Clear error messages for clients
   - Proper 4xx vs 5xx distinction

6. **Performance**: Caching + vectorization + lazy preprocessing
   - Meets <2 second response time requirement
   - 95th percentile performance target achievable

---

## Phase 1: Design Summary ✅

**Status**: Complete

### Artifacts Generated

1. **Data Model** ([data-model.md](./data-model.md))
   - InferenceRequest: API input schema (DTO)
   - InferenceResponse: API output schema (DTO)
   - InferenceLog: Django model for audit trail (PostgreSQL)
   - Model Metadata: JSON file structure
   - Model Cache: In-memory caching strategy

2. **API Contracts** ([contracts/inference-api.yaml](./contracts/inference-api.yaml))
   - OpenAPI 3.0 specification
   - Single endpoint: POST /api/inference/
   - Query parameter: `?model=rf|svm|lstm|cnn_1d`
   - Request/response schemas with examples
   - Error response formats for all HTTP codes

3. **Quickstart Guide** ([quickstart.md](./quickstart.md))
   - Installation instructions
   - Usage examples for all scenarios (P1, P2, P3)
   - Frontend integration examples (React with fetch/axios)
   - Python client example
   - Testing scenarios and troubleshooting

### Key Design Decisions

- **Backend-only feature**: No frontend components for MVP
- **Single POST endpoint**: `/api/inference/` handles all inference requests
- **Model selection via query parameter**: Optional `?model=` parameter for P2
- **Automatic preprocessing**: Detects model type and applies correct preprocessing
- **Audit logging**: All requests logged to PostgreSQL for compliance
- **Constitutional compliance**: 100% alignment with TremoAI project principles

---

## Phase 2: Next Steps

Planning phase complete. Ready for task generation and implementation.

**To proceed**:

```bash
/speckit.tasks
```

This will generate `tasks.md` with dependency-ordered implementation tasks organized by user story (P1, P2, P3).

**Estimated Implementation Time**:
- Phase 1 (Setup): ~30 minutes
- Phase 2 (Foundational utilities): ~3 hours
- Phase 3 (User Story 1 - Basic Inference): ~4 hours
- Phase 4 (User Story 2 - Model Selection): ~2 hours
- Phase 5 (User Story 3 - Enhanced Metadata): ~2 hours
- Phase 6 (Testing & Polish): ~2 hours
- **Total**: ~13-15 hours

**Dependencies**:
- Feature 004 (ML/DL Data Preparation) - REQUIRED
- Feature 005 (ML Models Training) - REQUIRED for RF/SVM
- Feature 006 (DL Models Training) - REQUIRED for LSTM/CNN
- Feature 007 (Model Comparison) - Referenced for performance benchmarks

---

## Implementation Strategy

### MVP-First Approach (User Story 1 Only)

1. Set up Django app structure (~30 min)
2. Implement core utilities:
   - ModelLoader with caching (~1 hour)
   - PreprocessingService (~1 hour)
   - InferenceService (~1 hour)
3. Implement API endpoint (~2 hours)
4. Add validation and error handling (~1 hour)
5. Test basic inference flow (~1 hour)

**MVP Deliverable**: Functional inference endpoint with default model (~7 hours)

### Incremental Feature Addition

1. **After MVP**: Add model selection (P2) - ~2 hours
2. **After P2**: Add enhanced metadata (P3) - ~2 hours
3. **Polish**: Testing, documentation, optimization - ~2 hours

**Full Feature**: All user stories complete (~13 hours)

---

## Risk Mitigation

### Risk 1: Model Loading Too Slow

**Mitigation**: Caching strategy (research.md R1) ensures <5ms after first load

**Fallback**: Preload models on Django startup if needed

### Risk 2: Concurrent Requests Cause Issues

**Mitigation**: Thread-safe model inference (research.md R2) proven safe

**Monitoring**: Log inference times and queue lengths

### Risk 3: Feature 005/006 Models Not Available

**Mitigation**: Graceful error handling with 503 Service Unavailable

**User Guidance**: Error messages include instructions to complete training

### Risk 4: Performance Budget Exceeded

**Mitigation**: Performance optimization strategy (research.md R6) provides buffer

**Monitoring**: P3 metadata includes inference_time_ms for tracking

---

## Constitutional Re-Check ✅

Post-design validation against `.specify/memory/constitution.md`:

- [X] **Monorepo Architecture**: ✅ All code in `backend/inference/`
- [X] **Tech Stack Immutability**: ✅ No new frameworks introduced
- [X] **Database Strategy**: ✅ Supabase PostgreSQL for audit logs
- [X] **Authentication**: ✅ JWT required for all endpoints
- [X] **Security-First**: ✅ No new secrets, no hardcoded credentials
- [X] **Real-time Requirements**: ✅ N/A (synchronous HTTP, not WebSocket)
- [X] **MQTT Integration**: ✅ N/A (receives preprocessed data)
- [X] **AI Model Serving**: ✅ Core feature implementation
- [X] **API Standards**: ✅ REST + JSON with standard HTTP codes
- [X] **Development Scope**: ✅ Local development only

**Result**: ✅ **PASS** - Design maintains full constitutional compliance

---

## Approval & Sign-off

**Planning Status**: ✅ **COMPLETE**

**Artifacts Delivered**:
- ✅ research.md - All technical unknowns resolved
- ✅ data-model.md - Entities and schemas defined
- ✅ contracts/inference-api.yaml - API specification complete
- ✅ quickstart.md - Integration guide ready
- ✅ Agent context updated (CLAUDE.md)

**Ready for**:
- `/speckit.tasks` - Task breakdown generation
- `/speckit.implement` - Implementation execution (after tasks)

**Reviewers**: Dr. Reem (Supervisor)

**Date**: 2026-02-16
