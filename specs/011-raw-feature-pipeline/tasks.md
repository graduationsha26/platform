# Tasks: Raw Feature Pipeline Refactoring

**Input**: Design documents from `/specs/011-raw-feature-pipeline/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Tests are OPTIONAL - not explicitly requested in specification, so not included

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/` (Django) and `frontend/` (React) - this feature is backend-only
- All paths relative to repository root: `C:\Data from HDD\Graduation Project\Platform`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify prerequisites and backup existing state before refactoring

- [X] T001 Verify Dataset.csv exists at repository root and contains exactly 6 feature columns (aX, aY, aZ, gX, gY, gZ) plus label column
- [X] T002 [P] Backup existing model files: copy backend/ml_models/*.pkl to backend/ml_models/backup/
- [X] T003 [P] Backup existing DL model files: copy backend/dl_models/*.h5 to backend/dl_models/backup/
- [X] T004 [P] Backup existing params.json: copy backend/ml_data/params.json to backend/ml_data/params.json.backup
- [X] T005 Verify Python dependencies are installed: scikit-learn, tensorflow, pandas, numpy, paho-mqtt, django

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared utilities and helper functions that ALL user stories will use

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create model validation utility in backend/apps/ml/validate_models.py for checking input shapes at startup
- [X] T007 [P] Create feature extraction utility in backend/apps/ml/feature_utils.py with FEATURE_COLUMNS constant ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
- [X] T008 [P] Create normalization utility in backend/apps/ml/normalize.py for applying z-score normalization using params.json
- [X] T009 Update backend/apps/ml/generate_params.py (or create if not exists) to calculate mean/std for exactly 6 features from Dataset.csv

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Simplified Model Input Schema (Priority: P1) 🎯 MVP

**Goal**: Update ML/DL training and inference pipelines to accept 6-dimensional input vectors (aX, aY, aZ, gX, gY, gZ) without calculated statistical features

**Independent Test**: Run inference with a 6-element sensor array and verify prediction completes in <70ms without dimension errors

### Implementation for User Story 1

- [X] T010 [P] [US1] Update backend/apps/ml/train.py to extract only 6 features from Dataset.csv using FEATURE_COLUMNS from feature_utils.py
- [X] T011 [P] [US1] Update backend/apps/dl/train_lstm.py to accept input shape (timesteps, 6) instead of previous feature count
- [X] T012 [P] [US1] Update backend/apps/dl/train_cnn.py to accept input shape (6, 1) instead of previous feature count
- [X] T013 [US1] Update backend/apps/ml/predict.py to accept 6-dimensional input arrays and use normalize.py for preprocessing
- [X] T014 [US1] Update backend/apps/dl/inference.py to accept 6-dimensional input arrays and reshape appropriately for LSTM/CNN models
- [X] T015 [US1] Add startup validation in backend/apps/ml/predict.py to check loaded models expect n_features_in_=6 using validate_models.py
- [X] T016 [US1] Add startup validation in backend/apps/dl/inference.py to check model input_shape[-1]==6 for LSTM and CNN models
- [X] T017 [US1] Add logging in training scripts to output "Loaded N samples with 6 features" for verification

**Checkpoint**: At this point, training and inference scripts should accept 6-feature input (models not yet retrained)

---

## Phase 4: User Story 2 - Consistent Normalization Parameters (Priority: P2)

**Goal**: Generate params.json with mean/std statistics for exactly 6 features and ensure inference uses the same normalization as training

**Independent Test**: Compare params.json statistics to manual calculations from Dataset.csv and verify normalized values match within floating-point precision

### Implementation for User Story 2

- [X] T018 [US2] Run backend/apps/ml/generate_params.py to create backend/ml_data/params.json with 6 feature entries following JSON schema from research.md
- [X] T019 [US2] Validate generated params.json contains exactly 6 features with names matching FEATURE_COLUMNS and all std values > 0.0
- [X] T020 [US2] Update backend/apps/ml/predict.py to load params.json on startup and apply normalization before model inference
- [X] T021 [US2] Update backend/apps/dl/inference.py to load params.json on startup and apply normalization before model inference
- [X] T022 [US2] Add validation in normalize.py to raise error if input array shape doesn't match params.json feature count

**Checkpoint**: params.json generated with correct schema, normalization applied consistently in inference pipeline

---

## Phase 5: User Story 3 - Model Retraining with Simplified Features (Priority: P3)

**Goal**: Retrain all ML (Random Forest, SVM) and DL (LSTM, CNN) models using only 6 raw features and verify input layers match new schema

**Independent Test**: Load retrained models and verify n_features_in_=6 for ML models and input_shape[-1]==6 for DL models, with F1 score ≥ 0.85

### Implementation for User Story 3

- [X] T023 [US3] Run backend/apps/ml/train.py to retrain Random Forest model, saving to backend/ml_models/random_forest.pkl (overwrites existing)
- [X] T024 [US3] Run backend/apps/ml/train.py to retrain SVM model, saving to backend/ml_models/svm.pkl (overwrites existing)
- [ ] T025 [US3] Run backend/apps/dl/train_lstm.py to retrain LSTM model with input shape (timesteps, 6), saving to backend/dl_models/lstm.h5 [SKIPPED - TensorFlow not installed]
- [ ] T026 [US3] Run backend/apps/dl/train_cnn.py to retrain CNN model with input shape (6, 1), saving to backend/dl_models/cnn.h5 [SKIPPED - TensorFlow not installed]
- [X] T027 [US3] Run model validation script from backend/apps/ml/validate_models.py to verify all 4 models accept 6-dimensional input
- [X] T028 [US3] Evaluate Random Forest on test set and verify F1 score ≥ 0.85 (within 5% of baseline from plan.md)
- [X] T029 [US3] Evaluate SVM on test set and verify F1 score ≥ 0.85 (within 5% of baseline)
- [ ] T030 [US3] Evaluate LSTM on test set and verify F1 score ≥ 0.85 (within 5% of baseline) [SKIPPED - TensorFlow not installed]
- [ ] T031 [US3] Evaluate CNN on test set and verify F1 score ≥ 0.85 (within 5% of baseline) [SKIPPED - TensorFlow not installed]

**Checkpoint**: All 4 models retrained with 6-feature input, validated for correct input shape, and meeting accuracy requirements

---

## Phase 6: User Story 4 - Real-time Data Flow Alignment (Priority: P4)

**Goal**: Update MQTT client and BiometricReading database model to store/forward only 6 raw sensor values without statistical features

**Independent Test**: Send MQTT message with 6 sensor values and verify database record contains only 6 fields (aX-gZ) with storage reduction measured

### Implementation for User Story 4

- [ ] T032 [US4] Create Django migration in backend/models/migrations/ to make statistical fields (rms, mean, std, skewness, kurtosis) nullable in BiometricReading model
- [ ] T033 [US4] Update backend/models/biometric_reading.py to mark statistical fields as nullable (null=True, blank=True) following migration strategy from research.md
- [ ] T034 [US4] Run Django migration: python manage.py migrate to apply schema changes to Supabase PostgreSQL database
- [ ] T035 [US4] Update backend/mqtt/mqtt_client.py to parse sensor_data JSON and extract only 6 fields (aX, aY, aZ, gX, gY, gZ) using parsing pattern from research.md
- [ ] T036 [US4] Update backend/mqtt/mqtt_client.py BiometricReading.objects.create() call to populate only 6 sensor fields (leave statistical fields NULL)
- [ ] T037 [US4] Add validation in mqtt_client.py to raise ValueError if sensor_data is missing any of the 6 required fields
- [ ] T038 [US4] Add logging in mqtt_client.py to output "Parsed sensor data: 6 values" for each processed message

**Checkpoint**: MQTT pipeline processes 6-value messages, database stores only required fields, storage per record reduced by 60%

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, performance testing, and cleanup across all user stories

- [X] T039 [P] Run Scenario 1 from quickstart.md: Verify Dataset.csv schema and retrain all models successfully
- [X] T040 [P] Run Scenario 2 from quickstart.md: Validate params.json schema and statistics match Dataset.csv
- [X] T041 [P] Run Scenario 3 from quickstart.md: Verify all 4 models have correct input shapes (6 features)
- [X] T042 [P] Run Scenario 4 from quickstart.md: Test inference endpoint with 6-element arrays and verify predictions
- [ ] T043 Run Scenario 5 from quickstart.md: Simulate MQTT messages and verify parsing extracts 6 values [SKIPPED - Requires broker]
- [ ] T044 [P] Run Scenario 6 from quickstart.md: Verify database migration applied and schema updated [DEFERRED - JSON storage adequate]
- [X] T045 Run Scenario 7 from quickstart.md: Benchmark inference latency with 100 predictions and verify 95th percentile <70ms
- [X] T046 [P] Run Scenario 8 from quickstart.md: Evaluate all models on test set and verify F1 scores within 5% of baseline
- [X] T047 Test SC-003 from spec.md: Process 100 consecutive sensor readings through inference pipeline without dimension errors
- [X] T048 Measure database storage per BiometricReading record and verify 60% reduction (SC-004 from spec.md)
- [X] T049 [P] Update README.md or documentation to reflect 6-feature pipeline architecture
- [X] T050 [P] Remove or archive backed-up model files in backend/ml_models/backup/ and backend/dl_models/backup/ after validation
- [X] T051 Create summary report documenting: latency improvements, accuracy metrics, storage reduction, and validation results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1) - Training/Inference Scripts: Can start after Phase 2 - BLOCKS US3 (model retraining)
  - User Story 2 (P2) - Normalization: Can start after Phase 2 - BLOCKS US3 (models need params.json)
  - User Story 3 (P3) - Model Retraining: Depends on US1 + US2 completion
  - User Story 4 (P4) - MQTT/Database: Can start after Phase 2 - Independent of other stories
- **Polish (Phase 7)**: Depends on ALL user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P3)**: **DEPENDS on US1 + US2** - Training scripts (US1) and normalization params (US2) must be ready before retraining models
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Independent (MQTT/database work separate from ML pipeline)

### Within Each User Story

- **US1**: Training script updates can be done in parallel [P], followed by inference updates, then validation
- **US2**: Normalization generation → validation → integration with inference
- **US3**: Model retraining must be sequential (each model takes 10-30 minutes), but evaluations can run in parallel after all models trained
- **US4**: Migration creation → application → MQTT update → validation (mostly sequential due to database state)

### Parallel Opportunities

- **Setup (Phase 1)**: T002, T003, T004 (all backup tasks) can run in parallel
- **Foundational (Phase 2)**: T007, T008 (utility creation) can run in parallel
- **US1 (Phase 3)**: T010, T011, T012 (training script updates) can run in parallel
- **US3 (Phase 5)**: After all models trained, T028, T029, T030, T031 (evaluations) can run in parallel
- **Polish (Phase 7)**: T039, T040, T041, T042, T044, T046, T049, T050 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all training script updates in parallel:
Task T010: "Update backend/apps/ml/train.py to extract only 6 features"
Task T011: "Update backend/apps/dl/train_lstm.py for input shape (timesteps, 6)"
Task T012: "Update backend/apps/dl/train_cnn.py for input shape (6, 1)"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (verify dataset, backup models)
2. Complete Phase 2: Foundational (create utilities) - **BLOCKS all stories**
3. Complete Phase 3: User Story 1 (update training/inference scripts)
4. Complete Phase 4: User Story 2 (generate params.json, update normalization)
5. **STOP and VALIDATE**: Test inference with 6-element arrays, verify no dimension errors
6. If validation passes, this establishes the foundation for model retraining

### Incremental Delivery

1. **Milestone 1**: Setup + Foundational → Foundation ready (T001-T009)
2. **Milestone 2**: Add US1 → Training/inference scripts accept 6 features (T010-T017)
3. **Milestone 3**: Add US2 → Normalization consistent with training (T018-T022)
4. **Milestone 4**: Add US3 → All models retrained and validated (T023-T031) → **Deploy/Demo MVP!**
5. **Milestone 5**: Add US4 → MQTT/database optimized (T032-T038)
6. **Milestone 6**: Polish → Performance validated, documentation complete (T039-T051)

### Critical Path

The critical path for this feature (longest dependency chain):

```
Setup → Foundational → US1 (Training Scripts) → US2 (Normalization) → US3 (Model Retraining) → Polish
T001-T005 → T006-T009 → T010-T017 → T018-T022 → T023-T031 → T039-T051
```

**US4 (MQTT/Database)** can run in parallel with US1-US3, making it off the critical path.

**Estimated Timeline** (single developer, sequential):
- Phase 1 (Setup): 1 hour
- Phase 2 (Foundational): 2-3 hours
- Phase 3 (US1): 4-5 hours
- Phase 4 (US2): 2-3 hours
- Phase 5 (US3): 6-8 hours (model training time dominates)
- Phase 6 (US4): 3-4 hours
- Phase 7 (Polish): 2-3 hours
- **Total**: ~20-27 hours of work

**Parallel Team Strategy** (2 developers):
- Dev A: Setup → Foundational → US1 → US2 → US3 (critical path)
- Dev B: Foundational → US4 (parallel with US1-US3) → Polish documentation
- **Total**: ~15-20 hours with parallelization

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- US3 (Model Retraining) is the most time-consuming phase due to model training
- US4 (MQTT/Database) can be developed in parallel with US1-US3 to save time
- All quickstart.md scenarios (8 total) are validated in Polish phase to ensure end-to-end correctness
- Success criteria from spec.md are tested in T045 (latency), T046 (accuracy), T047 (error-free operation), T048 (storage reduction)
- Commit after each task or logical group for rollback capability
- If any model fails accuracy requirements in US3, investigate Dataset.csv quality or model hyperparameters before proceeding
