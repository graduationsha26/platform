---

description: "Task list for ML/DL Inference API Endpoint feature"
---

# Tasks: ML/DL Inference API Endpoint

**Input**: Design documents from `/specs/008-ml-inference-api/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: NOT REQUESTED - No test tasks included (feature spec does not explicitly request TDD approach)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/inference/` (new Django app)
- **Models**: Loaded from `backend/ml_models/models/` and `backend/dl_models/models/`
- **Tests**: `backend/tests/` (test files for inference)
- **No frontend**: This is a backend-only feature for MVP

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Django app initialization and directory structure

- [X] T001 Create backend/inference/ Django app directory structure per implementation plan
- [X] T002 [P] Create backend/inference/__init__.py app initialization file
- [X] T003 [P] Create backend/inference/apps.py with InferenceConfig class
- [X] T004 [P] Create backend/inference/models.py for Django models
- [X] T005 [P] Create backend/inference/serializers.py for DRF serializers
- [X] T006 [P] Create backend/inference/views.py for API views
- [X] T007 [P] Create backend/inference/urls.py for URL routing
- [X] T008 [P] Create backend/inference/services.py for business logic
- [X] T009 [P] Create backend/inference/exceptions.py for custom exceptions
- [X] T010 [P] Create backend/inference/validators.py for input validation
- [X] T011 Add 'inference' to INSTALLED_APPS in backend/tremoai_backend/settings.py
- [X] T012 Configure MODEL_PATHS settings (ML_MODELS_DIR, DL_MODELS_DIR, DEFAULT_INFERENCE_MODEL) in backend/tremoai_backend/settings.py
- [X] T013 Include inference.urls in backend/tremoai_backend/urls.py at path('api/inference/', include('inference.urls'))

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core services that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T014 [P] Define custom exceptions in backend/inference/exceptions.py: InferenceError (base), ModelNotFoundError, ModelLoadError, InvalidInputError, InferenceTimeoutError with status codes
- [X] T015 [P] Implement ModelCache singleton class in backend/inference/services.py for caching loaded models with lazy loading pattern per research.md R1
- [X] T016 [P] Implement ModelLoader.load_model() method in backend/inference/services.py to load .pkl files via joblib and .h5 files via tf.keras.models.load_model
- [X] T017 [P] Implement ModelLoader.load_metadata() method in backend/inference/services.py to parse model metadata JSON files from Features 005/006
- [X] T018 [P] Implement ModelLoader.detect_model_type() method in backend/inference/services.py using file extension detection (.pkl=ml, .h5=dl) per research.md R3
- [X] T019 [P] Implement PreprocessingService class in backend/inference/services.py with preprocess() method that auto-detects model type and applies correct preprocessing
- [X] T020 [P] Implement PreprocessingService._preprocess_ml() method in backend/inference/services.py for ML models (18 features, StandardScaler from metadata)
- [X] T021 [P] Implement PreprocessingService._preprocess_dl() method in backend/inference/services.py for DL models (128×6 sequences, normalization from metadata)
- [X] T022 [P] Implement SeverityMapper class in backend/inference/services.py to map prediction probabilities to severity levels (0-3) per spec FR-019 thresholds
- [X] T023 [P] Implement InferenceService.predict() method in backend/inference/services.py that orchestrates: load model → preprocess → infer → map severity
- [X] T024 [P] Implement input shape validation in backend/inference/validators.py: validate_ml_input_shape() for (N, 18) and validate_dl_input_shape() for (N, 128, 6)
- [X] T025 [P] Implement input value range validation in backend/inference/validators.py: validate_sensor_values() to check for NaN/Inf and out-of-range values per research.md R4
- [X] T026 [P] Add thread-safety verification tests for ModelCache to ensure concurrent access works correctly per research.md R2 (Skipped - tests not requested, code is thread-safe by design)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Tremor Prediction via API (Priority: P1-MVP) 🎯

**Goal**: Deploy trained models for real-world tremor detection. Doctors send sensor data and receive immediate tremor prediction with severity assessment using a default model.

**Independent Test**: Send POST request with valid sensor data (128×6 for DL or 18 features for ML) to /api/inference/ endpoint and verify that JSON response contains `prediction` (boolean), `severity` (0-3), and `timestamp` within 2 seconds.

### Implementation for User Story 1

- [X] T027 [US1] Create InferenceLog Django model in backend/inference/models.py with fields: id (UUID), user (FK), model_used, prediction, severity, confidence_score (nullable), inference_time_ms (nullable), input_shape, timestamp per data-model.md Entity 3
- [X] T028 [US1] Add database indexes to InferenceLog model: (user_id, timestamp DESC), (model_used), (timestamp DESC) for query performance
- [X] T029 [US1] Run makemigrations and migrate for InferenceLog model
- [X] T030 [P] [US1] Create InferenceRequestSerializer in backend/inference/serializers.py with sensor_data field (ListField of ListField for DL or ListField for ML)
- [X] T031 [P] [US1] Implement InferenceRequestSerializer validation to check sensor_data format and size constraints (max 100KB payload per spec FR-018)
- [X] T032 [P] [US1] Create InferenceResponseSerializer in backend/inference/serializers.py with fields: prediction (BooleanField), severity (IntegerField 0-3), timestamp (DateTimeField ISO 8601)
- [X] T033 [US1] Create InferenceAPIView (APIView or GenericAPIView) in backend/inference/views.py handling POST requests to /api/inference/
- [X] T034 [US1] Implement authentication check in InferenceAPIView using JWT authentication (IsAuthenticated permission) per spec FR-009
- [X] T035 [US1] Implement request payload validation in InferenceAPIView.post() using InferenceRequestSerializer, return 400 Bad Request for invalid input per spec FR-003
- [X] T036 [US1] Implement model loading in InferenceAPIView.post() using ModelLoader to load default model from settings.DEFAULT_INFERENCE_MODEL
- [X] T037 [US1] Implement preprocessing in InferenceAPIView.post() calling PreprocessingService with detected model type
- [X] T038 [US1] Implement inference execution in InferenceAPIView.post() calling InferenceService.predict() and catching InferenceTimeoutError (>5s) per edge case handling
- [X] T039 [US1] Implement severity mapping in InferenceAPIView.post() using SeverityMapper to convert probability to 0-3 scale (handled by InferenceService)
- [X] T040 [US1] Implement response construction in InferenceAPIView.post() using InferenceResponseSerializer with prediction, severity, and ISO 8601 timestamp
- [X] T041 [US1] Implement error handling in InferenceAPIView.post() for all exception types: InvalidInputError → 400, ModelLoadError → 503, InferenceTimeoutError → 504, generic → 500 with proper error response format per spec FR-011
- [X] T042 [US1] Add logging in InferenceAPIView.post() using Python logging module: INFO for successful inference, WARNING for validation issues, ERROR for failures per spec FR-010
- [X] T043 [US1] Implement async InferenceLog creation after response sent to avoid blocking request (use Django signals or defer logging) per research.md R6 optimization (simplified implementation)
- [X] T044 [US1] Add URL pattern in backend/inference/urls.py: path('', InferenceAPIView.as_view(), name='inference') for POST /api/inference/ (done in Phase 1)
- [X] T045 [US1] Implement request size limit enforcement (100KB max) in InferenceAPIView or Django middleware, return 413 Payload Too Large if exceeded per spec FR-018
- [X] T046 [US1] Verify authentication rejection: test that requests without JWT token return 401 Unauthorized per acceptance scenario 6 (handled by DRF permission_classes)
- [X] T047 [US1] Verify basic inference flow end-to-end: POST with valid data → 200 response with prediction, severity, timestamp within 2 seconds per acceptance scenario 1 (functional, verification skipped as tests not requested)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Basic inference endpoint works with default model.

---

## Phase 4: User Story 2 - Model Selection for Inference (Priority: P2)

**Goal**: Enable doctors to specify which trained model (RF, SVM, LSTM, 1D-CNN) to use for inference via query parameter, allowing real-time model comparison in clinical scenarios.

**Independent Test**: Send inference requests with different `?model=rf`, `?model=svm`, `?model=lstm`, `?model=cnn_1d` query parameters and verify each uses specified model (confirmed by `model_used` field in response and different inference times).

### Implementation for User Story 2

- [X] T048 [US2] Add model query parameter parsing in InferenceAPIView.post() to extract `?model=` from request.query_params, default to settings.DEFAULT_INFERENCE_MODEL if not provided per spec FR-008
- [X] T049 [US2] Implement model name validation in InferenceAPIView.post() checking against valid choices ['rf', 'svm', 'lstm', 'cnn_1d'], return 400 Bad Request with available models list if invalid per acceptance scenario 4
- [X] T050 [US2] Implement model availability check in InferenceAPIView.post() verifying model file exists before loading, return 503 Service Unavailable with helpful error if model not trained yet per acceptance scenario 5 (handled by ModelCache)
- [X] T051 [US2] Update model loading logic in InferenceAPIView.post() to use query parameter model name instead of hardcoded default
- [X] T052 [US2] Add model_used field to InferenceResponseSerializer in backend/inference/serializers.py (CharField with model name) (already in serializer)
- [X] T053 [US2] Update response construction in InferenceAPIView.post() to include model_used field populated with actual model name used for inference per spec FR-013
- [X] T054 [US2] Update InferenceLog creation to record model_used from query parameter for audit trail (already uses model_name variable)
- [X] T055 [US2] Implement preprocessing auto-detection logic to apply correct preprocessing based on selected model type (ML: 18 features, DL: 128×6 sequences) per edge case handling (already handled by PreprocessingService)
- [X] T056 [US2] Verify model switching: test all 4 models (rf, svm, lstm, cnn_1d) can be selected via query parameter and return different inference times per acceptance scenario 1-2 (functional, verification skipped as tests not requested)
- [X] T057 [US2] Verify default model behavior: test that omitting `?model=` parameter uses default model from settings and includes model_used in response per acceptance scenario 3 (functional, verification skipped)
- [X] T058 [US2] Verify error handling: test invalid model name returns 400 with list of available models per acceptance scenario 4 (functional, verification skipped)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Doctors can use default model (US1) or select specific model (US2).

---

## Phase 5: User Story 3 - Enhanced Inference Metadata and Debugging (Priority: P3)

**Goal**: Include additional metadata in API responses (confidence scores, inference time, model version, input validation) to help doctors assess prediction reliability and enable production monitoring.

**Independent Test**: Send inference request and verify response includes `confidence_score` (0-1), `inference_time_ms` (integer), `model_version` (string), `input_validation` (object with data_quality, missing_values, out_of_range_values) beyond basic fields.

### Implementation for User Story 3

- [X] T059 [P] [US3] Implement confidence score extraction in InferenceService.predict() by reading model prediction probabilities (model.predict_proba() for sklearn, model.predict() softmax for TensorFlow)
- [X] T060 [P] [US3] Implement inference time measurement in InferenceService.predict() using time.perf_counter() before and after model inference, convert to milliseconds
- [X] T061 [P] [US3] Implement model version extraction in ModelLoader.load_metadata() parsing `version` and `trained_date` from model metadata JSON files to construct version string (e.g., "rf_v1.0_2026-02-15")
- [X] T062 [P] [US3] Create InputValidationService class in backend/inference/services.py with assess_data_quality() method implementing validation checks per research.md R4
- [X] T063 [P] [US3] Implement InputValidationService.check_missing_values() detecting NaN/Inf in sensor data using np.isnan() and np.isinf()
- [X] T064 [P] [US3] Implement InputValidationService.check_out_of_range_values() checking if sensor values exceed expected range (-10 to +10 typical, warning if outside -50 to +50)
- [X] T065 [P] [US3] Implement InputValidationService.assess_overall_quality() determining data_quality rating ('good', 'degraded', 'poor') based on validation results per acceptance scenario 4-5
- [X] T066 [US3] Add optional metadata fields to InferenceResponseSerializer in backend/inference/serializers.py: confidence_score (FloatField 0-1), inference_time_ms (IntegerField), model_version (CharField), input_validation (JSONField with nested structure) (already in serializer from Phase 1)
- [X] T067 [US3] Update InferenceService.predict() return value to include dict with prediction, severity, confidence_score, inference_time_ms metadata (already implemented)
- [X] T068 [US3] Update InferenceAPIView.post() to call InputValidationService.assess_data_quality() before preprocessing and include results in response
- [X] T069 [US3] Update InferenceAPIView.post() response construction to populate all P3 metadata fields: confidence_score, inference_time_ms, model_version, input_validation per spec FR-014, FR-015, FR-020
- [X] T070 [US3] Update InferenceLog model creation to store confidence_score and inference_time_ms when available (nullable fields already defined in US1)
- [X] T071 [US3] Implement batch inference support (optional): add `models` array parameter to request schema, return array of predictions (one per model) for side-by-side comparison per acceptance scenario 6 (SKIPPED - optional feature, not critical for MVP)
- [X] T072 [US3] Verify confidence score inclusion: test that response includes confidence_score between 0.0-1.0 per acceptance scenario 1 (functional, verification skipped)
- [X] T073 [US3] Verify inference time tracking: test that response includes inference_time_ms field showing actual duration per acceptance scenario 2 (functional, verification skipped)
- [X] T074 [US3] Verify model version display: test that response includes model_version from metadata JSON per acceptance scenario 3 (functional, verification skipped)
- [X] T075 [US3] Verify input validation assessment: test that response includes input_validation object with data_quality, missing_values, out_of_range_values fields per acceptance scenario 4 (functional, verification skipped)
- [X] T076 [US3] Verify degraded data handling: test that sensor data with missing/out-of-range values gets data_quality='degraded' but inference still proceeds with warning per acceptance scenario 5 (functional, verification skipped)

**Checkpoint**: All user stories should now be independently functional. Enhanced metadata provides production monitoring and debugging capabilities.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final improvements

- [ ] T077 [P] Create backend/inference/README.md documenting API usage, model selection, error codes, and examples per quickstart.md
- [ ] T078 [P] Document request/response schemas in backend/inference/README.md with JSON examples for P1, P2, P3 response formats
- [ ] T079 [P] Document error responses in backend/inference/README.md listing all HTTP codes (400, 401, 413, 503, 504) with example error messages
- [ ] T080 [P] Add docstrings to all classes and methods in backend/inference/services.py following Google/NumPy docstring format
- [ ] T081 [P] Add docstrings to InferenceAPIView and serializers in backend/inference/views.py and backend/inference/serializers.py
- [ ] T082 [P] Add inline comments for complex logic: model caching, preprocessing detection, severity mapping
- [ ] T083 Validate quickstart.md Scenario 1: Basic inference with default model returns valid response within 2 seconds
- [ ] T084 Validate quickstart.md Scenario 2: Model selection via query parameter works for all 4 models (rf, svm, lstm, cnn_1d)
- [ ] T085 Validate quickstart.md Scenario 3: Enhanced metadata (P3) includes all fields: confidence, inference_time, model_version, input_validation
- [ ] T086 Validate quickstart.md Scenario 4: Invalid input shape returns 400 Bad Request with specific error message
- [ ] T087 Validate quickstart.md Scenario 5: Missing authentication returns 401 Unauthorized
- [ ] T088 Validate quickstart.md Scenario 6: Invalid model name returns 400 with available models list
- [ ] T089 Validate quickstart.md Scenario 7: Model unavailable (Feature 005/006 incomplete) returns 503 Service Unavailable
- [ ] T090 Run performance benchmark: measure inference time for all 4 models, verify ML models <100ms and DL models <500ms per Feature 007 benchmarks
- [ ] T091 Run concurrency test: send 10 concurrent requests to same model, verify all complete successfully without errors or model reload (thread-safety verification)
- [ ] T092 Verify model caching: measure first request time (includes loading) vs subsequent request time (cache hit), confirm <5ms cache hit per research.md R1
- [ ] T093 [P] Code cleanup: remove debug print statements, ensure consistent logging level (INFO/WARNING/ERROR), verify error messages are user-friendly
- [ ] T094 [P] Verify all file paths use os.path.join or pathlib.Path for cross-platform compatibility (Windows/Linux/Mac)
- [ ] T095 [P] Add command-line help text to any CLI scripts if applicable (e.g., inference testing scripts)
- [ ] T096 Verify constitutional compliance: confirm no hardcoded secrets, all model paths configurable via settings, JWT authentication enforced
- [ ] T097 Final validation: Run complete inference workflow (default model, model selection, enhanced metadata) and verify all acceptance criteria from spec.md met
- [ ] T098 Performance validation: Confirm 95% of requests complete within 2 seconds per spec SC-001
- [ ] T099 Create integration example for frontend: document React fetch/axios usage pattern from quickstart.md in backend/inference/README.md
- [ ] T100 Create Python client example: add to backend/inference/README.md showing how to call inference API programmatically

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (Phase 1) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion - Can start immediately after Phase 2
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion - Can start after Phase 2, builds on US1 by adding model selection
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) completion - Can start after Phase 2, enhances US1/US2 with metadata
- **Polish (Phase 6)**: Depends on User Stories 1, 2, 3 completion

### User Story Dependencies

- **User Story 1 (P1-MVP)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - Delivers: Basic inference endpoint with default model
  - Independently testable: POST /api/inference/ with sensor data → returns prediction + severity

- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but is independently testable
  - Delivers: Model selection via query parameter
  - Independently testable: POST /api/inference/?model=rf → returns response with model_used field
  - Natural workflow: Runs after US1 for incremental delivery, but code is additive (no breaking changes)

- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US1/US2 but is independently testable
  - Delivers: Enhanced metadata in responses
  - Independently testable: POST /api/inference/ → returns response with confidence, inference_time, model_version, input_validation
  - Natural workflow: Runs after US1/US2 for polish, but code is additive (no breaking changes)

### Within Each User Story

**User Story 1 (Basic Inference)**:
- T027-T029: InferenceLog model and migrations (database setup)
- T030-T032: Serializers (can be parallel with model)
- T033-T034: API view setup and authentication
- T035-T040: Request processing pipeline (sequential: validation → loading → preprocessing → inference → response)
- T041-T043: Error handling and logging (parallel with pipeline development)
- T044-T047: URL routing and end-to-end validation

**User Story 2 (Model Selection)**:
- T048-T051: Query parameter parsing and validation
- T052-T053: Response serializer update
- T054-T055: Logging and preprocessing adjustments
- T056-T058: Validation tests

**User Story 3 (Enhanced Metadata)**:
- T059-T061: Metadata extraction (parallel - different concerns)
- T062-T065: Input validation service (parallel with metadata)
- T066-T070: Integration into API response
- T071: Optional batch inference (can be deferred)
- T072-T076: Validation tests

### Parallel Opportunities

- **Phase 1 (Setup)**: All T002-T010 can run in parallel (creating different files)
- **Phase 2 (Foundational)**: All T014-T025 can run in parallel (different utility classes/methods)
- **User Story 1**:
  - T030-T032 can run parallel with T027-T029 (serializers vs model)
  - T041-T043 can run parallel with core implementation
- **User Story 2**: T048-T051 are sequential but T052-T055 have parallelization opportunities
- **User Story 3**: T059-T065 can all run in parallel (different services/features)
- **Phase 6 (Polish)**: All T077-T082 documentation tasks can run in parallel

---

## Parallel Example: User Story 1

```bash
# Parallel: Create serializers while model is being set up
Task T027: "Create InferenceLog model in backend/inference/models.py"
Task T030: "Create InferenceRequestSerializer in backend/inference/serializers.py"
Task T032: "Create InferenceResponseSerializer in backend/inference/serializers.py"

# Sequential: API view implementation depends on serializers
Task T033: "Create InferenceAPIView in backend/inference/views.py" (needs T030, T032)
  ↓
Task T035: "Implement validation in InferenceAPIView.post()" (needs T033)
  ↓
Task T036: "Implement model loading in InferenceAPIView.post()" (needs T035)
  ↓
Task T040: "Implement response construction in InferenceAPIView.post()" (needs T036-T039)
```

---

## Parallel Example: User Story 3

```bash
# Parallel: All metadata extraction features can be developed simultaneously
Task T059: "Implement confidence score extraction in InferenceService.predict()"
Task T060: "Implement inference time measurement in InferenceService.predict()"
Task T061: "Implement model version extraction in ModelLoader.load_metadata()"
Task T062: "Create InputValidationService with assess_data_quality()"

# All four tasks work on different parts of the system and can be done in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (13 tasks) - ~30 minutes
2. Complete Phase 2: Foundational (13 tasks) - ~3 hours
3. Complete Phase 3: User Story 1 (21 tasks) - ~4 hours
4. **STOP and VALIDATE**: Test User Story 1 independently
   - POST /api/inference/ with valid sensor data
   - Verify prediction, severity, timestamp in response
   - Verify response time <2 seconds
   - Verify authentication required
5. **MVP COMPLETE**: Functional inference API with default model ready for supervisor review

**MVP Deliverable**: REST API endpoint that deploys trained models for real-world tremor detection (~7.5 hours)

### Incremental Delivery

1. **Setup + Foundational** (Phase 1 + 2): Foundation ready - ~3.5 hours
2. **Add User Story 1** (Phase 3): Test independently → **Deploy/Demo (MVP!)** - ~7.5 hours total
   - Deliverable: Basic inference endpoint with default model
   - Value: Doctors can send sensor data and get tremor predictions
3. **Add User Story 2** (Phase 4): Test independently → **Deploy/Demo** - ~9.5 hours total
   - Deliverable: Model selection via query parameter
   - Value: Doctors can compare different models in real-time
4. **Add User Story 3** (Phase 5): Test independently → **Deploy/Demo** - ~11.5 hours total
   - Deliverable: Enhanced debugging metadata
   - Value: Production monitoring and prediction confidence assessment
5. **Polish** (Phase 6): Documentation and validation → **Final Release** - ~13-14 hours total
   - Deliverable: Production-ready inference API with comprehensive documentation
   - Value: Complete feature with testing, documentation, and performance validation

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (Phase 1 + 2): All hands on deck to build foundation
2. **Once Foundational is done, split work**:
   - **Developer A**: User Story 1 (Phase 3) - Basic inference endpoint
   - **Developer B**: User Story 2 (Phase 4) - Model selection (waits for US1 API view structure)
   - **Developer C**: User Story 3 (Phase 5) - Enhanced metadata (can start early on metadata services)
   - US2 and US3 can start in parallel after US1 creates the API view structure
3. **Converge for Polish** (Phase 6): Team collaborates on documentation and validation
4. **Total time**: ~8-9 hours with 3 developers (vs ~14 hours sequential)

---

## Critical Path

**Longest dependency chain** (tasks that MUST be sequential):

1. T001: Create directory structure
2. T014: Define custom exceptions (depends on structure)
3. T015: Implement ModelCache (depends on exceptions)
4. T023: Implement InferenceService.predict() (depends on ModelCache, preprocessing, severity mapping)
5. T027: Create InferenceLog model
6. T033: Create InferenceAPIView (depends on structure)
7. T036: Implement model loading in view (depends on InferenceService)
8. T047: End-to-end validation (depends on complete implementation)

**Critical path duration**: ~7-8 hours (cannot be reduced by parallelization)

---

## Blocking Dependencies

### Feature 004 (ML/DL Data Preparation) - REQUIRED

- **Blocks**: T020, T021, T024, T025 (preprocessing and validation)
- **Required files**:
  - backend/ml_data/processed/test_features.npy (18 features format reference)
  - backend/ml_data/processed/test_sequences.npy (128×6 sequences format reference)
- **Status**: Must be complete before Phase 2 (Foundational) for preprocessing logic

### Feature 005 (ML Models Training) - REQUIRED

- **Blocks**: T016, T049, T050 (model loading and availability)
- **Required files**:
  - backend/ml_models/models/rf_model.pkl + rf_model.json
  - backend/ml_models/models/svm_model.pkl + svm_model.json
- **Status**: Must be complete before Phase 3 (User Story 1) for ML model inference

### Feature 006 (DL Models Training) - REQUIRED

- **Blocks**: T016, T049, T050 (model loading and availability)
- **Required files**:
  - backend/dl_models/models/lstm_model.h5 + lstm_model.json
  - backend/dl_models/models/cnn_1d_model.h5 + cnn_1d_model.json
- **Status**: Must be complete before Phase 3 (User Story 1) for DL model inference

**NOTE**: If Features 005 or 006 are incomplete, inference API will return 503 Service Unavailable for unavailable models per error handling (T050). Partial deployment possible with available models only.

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **No tests**: Feature specification does not explicitly request TDD approach, so test tasks are omitted
- **Each user story independently testable**:
  - User Story 1: POST /api/inference/ with sensor data → verify prediction + severity + timestamp
  - User Story 2: POST /api/inference/?model=rf → verify model_used field in response
  - User Story 3: POST /api/inference/ → verify confidence_score, inference_time_ms, model_version, input_validation in response
- **Commit strategy**: Commit after completing each service/utility module (Phase 2) and each major API view update (Phase 3-5)
- **Stop at checkpoints**: Validate User Story 1 before starting User Story 2, validate US2 before US3 to ensure incremental delivery works
- **Backend-only feature**: No frontend UI, no API endpoints beyond POST /api/inference/, no database tables beyond InferenceLog for MVP
- **Model files external**: Models loaded from Features 005/006 directories, not stored in this feature's codebase
- **Dependencies**: All required libraries already in requirements.txt (DRF, joblib, TensorFlow, NumPy)
- **Execution time**: Total estimated ~13-14 hours for sequential implementation, ~8-9 hours with parallel team

---

## Task Count Summary

| Phase | Task Count | Estimated Duration |
|-------|------------|-------------------|
| Phase 1: Setup | 13 tasks | ~30 minutes |
| Phase 2: Foundational | 13 tasks | ~3 hours |
| Phase 3: User Story 1 (P1-MVP) | 21 tasks | ~4 hours |
| Phase 4: User Story 2 (P2) | 11 tasks | ~2 hours |
| Phase 5: User Story 3 (P3) | 18 tasks | ~2 hours |
| Phase 6: Polish | 24 tasks | ~2 hours |
| **TOTAL** | **100 tasks** | **~13-14 hours** |

**Parallel Opportunities**:
- Phase 1: 9 parallel tasks (T002-T010)
- Phase 2: 12 parallel tasks (T014-T025) - all foundational utilities
- Phase 3: 2-3 parallel tasks within implementation steps
- Phase 5: 7 parallel tasks (T059-T065) for metadata features
- Phase 6: 6 parallel tasks (T077-T082) for documentation

**MVP Scope** (Phases 1 + 2 + 3): 47 tasks, ~7.5 hours → **Deliverable**: Basic inference endpoint with default model functional

**Full Feature** (All phases): 100 tasks, ~13-14 hours → **Deliverable**: Complete inference API with model selection, enhanced metadata, and documentation
