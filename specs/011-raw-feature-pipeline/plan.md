# Implementation Plan: Raw Feature Pipeline Refactoring

**Branch**: `011-raw-feature-pipeline` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-raw-feature-pipeline/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Refactor the ML/DL feature engineering and inference pipeline to eliminate calculated statistical features (RMS, Mean, Std, Skewness, Kurtosis) and use only the 6 raw sensor axes (aX, aY, aZ, gX, gY, gZ) that exist in Dataset.csv. This resolves the schema mismatch between training data and inference pipeline, reduces inference latency, and simplifies the data flow from MQTT ingestion through model prediction. The technical approach involves: (1) updating training scripts to extract only 6 features from Dataset.csv, (2) regenerating params.json normalization file with 6-feature statistics, (3) modifying model architectures to accept 6-dimensional input, (4) updating MQTT and database schemas to store/forward only raw sensor values, (5) removing feature calculation logic from inference pipeline.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels (no changes)
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts (no changes)
**Database**: Supabase PostgreSQL (remote) - BiometricReading model schema update
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor) (no changes)
**Testing**: pytest (backend - model validation and inference tests)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data (no changes)
**Integration**: MQTT subscription for glove sensor data - message parsing update
**AI/ML**:
  - scikit-learn models (Random Forest, SVM) in `backend/ml_models/*.pkl`
  - TensorFlow/Keras models (LSTM, CNN) in `backend/dl_models/*.h5`
  - Normalization parameters in `backend/ml_data/params.json`
  - Training scripts in `backend/apps/ml/train.py` and `backend/apps/dl/*.py`
  - Inference scripts in `backend/apps/ml/predict.py` and `backend/apps/dl/inference.py`
**Performance Goals**:
  - Inference latency: <70ms per prediction (strict requirement for real-time tremor suppression)
  - Model accuracy: F1 score ≥ 0.85 (within 5% of previous performance)
  - Training time: <30 minutes for ML models, <2 hours for DL models (on CPU)
**Constraints**:
  - Local development only (no Docker/CI/CD/production deployment)
  - Dataset.csv schema is fixed (6 columns: aX, aY, aZ, gX, gY, gZ)
  - Cannot add new feature calculation logic (explicitly removing, not adding)
  - Model retraining required (historical model files will be replaced)
  - MQTT message format from IoT device is fixed (6 sensor values per message)
**Scale/Scope**:
  - Training dataset: ~50,000 sensor readings in Dataset.csv
  - Inference volume: 10 predictions/second per patient (1 prediction every 100ms)
  - 4 model types to retrain: Random Forest, SVM, LSTM, CNN
  - 1 normalization file to regenerate: params.json (6 features × 2 statistics = 12 values)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature modifies existing `backend/` ML pipeline code (no new repos)
- [X] **Tech Stack Immutability**: Uses existing scikit-learn and TensorFlow (no new frameworks)
- [X] **Database Strategy**: Updates existing BiometricReading model on Supabase PostgreSQL (no new databases)
- [X] **Authentication**: No authentication changes (ML pipeline is backend-only)
- [X] **Security-First**: No new secrets (existing MQTT/DB credentials unchanged)
- [X] **Real-time Requirements**: Maintains WebSocket streaming (no changes to Channels setup)
- [X] **MQTT Integration**: Updates MQTT message parsing to extract 6 values (existing subscription intact)
- [X] **AI Model Serving**: Models remain served via Django backend (same .pkl/.h5 format)
- [X] **API Standards**: No API endpoint changes (inference endpoint signature unchanged)
- [X] **Development Scope**: Local development only (training and testing on local machine)

**Result**: ✅ PASS

**Justification**: This is a pure refactoring feature that simplifies existing ML pipeline code without introducing new technologies or violating constitutional principles. All changes are within the existing Django backend structure, use the established tech stack, and maintain the same API contracts.

## Project Structure

### Documentation (this feature)

```text
specs/011-raw-feature-pipeline/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: Best practices for ML feature engineering
├── data-model.md        # Phase 1 output: Sensor Reading and Normalization Params entities
├── quickstart.md        # Phase 1 output: Training and inference test scenarios
├── contracts/           # Phase 1 output: N/A (no API changes, internal refactoring)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created)
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── ml/
│   │   ├── train.py            # MODIFY: Update to extract 6 features from Dataset.csv
│   │   ├── predict.py          # MODIFY: Update to accept 6-dimensional input
│   │   └── generate_params.py  # MODIFY: Generate params.json with 6 features
│   └── dl/
│       ├── train_lstm.py       # MODIFY: Update LSTM input shape to (timesteps, 6)
│       ├── train_cnn.py        # MODIFY: Update CNN input shape to (6, 1)
│       └── inference.py        # MODIFY: Update to accept 6-dimensional input
├── models/
│   └── biometric_reading.py   # MODIFY: BiometricReading model (remove statistical fields)
├── mqtt/
│   └── mqtt_client.py          # MODIFY: Parse only 6 sensor values from messages
├── ml_models/                  # REGENERATE: New .pkl files with 6-feature models
│   ├── random_forest.pkl       # REGENERATE
│   └── svm.pkl                 # REGENERATE
├── dl_models/                  # REGENERATE: New .h5 files with 6-feature models
│   ├── lstm.h5                 # REGENERATE
│   └── cnn.h5                  # REGENERATE
├── ml_data/
│   └── params.json             # REGENERATE: Normalization params for 6 features
└── tests/
    ├── test_ml_pipeline.py     # NEW: Validate 6-feature input/output
    └── test_model_shape.py     # NEW: Verify model input dimensions

Dataset.csv                     # EXISTING: 6-column training data (read-only)

frontend/                       # NO CHANGES: Frontend unaffected by backend ML refactoring
```

**Structure Decision**:
- **Backend-only feature**: All changes confined to `backend/` directory (no frontend modifications)
- **Model retraining**: Existing `.pkl` and `.h5` files will be overwritten with new 6-feature models
- **Database migration**: BiometricReading model schema change requires Django migration
- **MQTT update**: Modify message parser to extract 6 sensor values (no broker/subscription changes)
- **No API changes**: Inference endpoint maintains same signature (accepts array, returns prediction)
- **Testing focus**: Add tests to validate model input shapes and pipeline correctness

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitutional violations. Feature passes all constitution checks.

## Phase 0: Research & Technical Decisions

*GATE: Resolve all NEEDS CLARIFICATION items before Phase 1*

### Research Tasks

The following unknowns require research to inform implementation decisions:

1. **Model Input Shape Validation Best Practices**
   - Question: What's the best way to validate that retrained models expect exactly 6 input features before allowing inference?
   - Research: Model introspection techniques for scikit-learn and TensorFlow/Keras
   - Output: Code pattern for startup validation to detect dimension mismatches

2. **Normalization Parameter File Format**
   - Question: What's the optimal structure for params.json to store mean/std for 6 features?
   - Research: Standard formats for ML preprocessing parameters (JSON, YAML, pickle)
   - Output: JSON schema with validation rules

3. **Django Model Migration Strategy for Schema Changes**
   - Question: How to safely migrate BiometricReading model to remove statistical fields without data loss?
   - Research: Django migration best practices for removing fields with existing data
   - Output: Migration strategy (data retention vs. field removal)

4. **Feature Extraction from Pandas DataFrame**
   - Question: Most efficient way to extract only 6 columns from Dataset.csv in training scripts?
   - Research: Pandas column selection methods and performance implications
   - Output: Code pattern for column extraction with validation

5. **MQTT Message Parsing for Raw Sensor Data**
   - Question: How to reliably extract 6 numeric sensor values from MQTT JSON messages?
   - Research: JSON parsing patterns and error handling for malformed messages
   - Output: Robust message parser with validation

### Research Output

See `research.md` for consolidated findings on:
- Model input shape validation techniques
- Normalization parameter file design
- Django migration strategies
- Pandas DataFrame column operations
- MQTT message parsing patterns

## Phase 1: Design & Architecture

*Prerequisites: research.md complete*

### Data Model (Entity Definitions)

See `data-model.md` for:

**Key Entities**:

1. **SensorReading** (conceptual - represents raw MQTT data)
   - Fields: aX (float), aY (float), aZ (float), gX (float), gY (float), gZ (float), timestamp (datetime)
   - Relationships: Parsed from MQTT messages, stored in BiometricReading model
   - Validation: All 6 fields must be numeric, timestamp must be present
   - State: Immutable once received from IoT device

2. **NormalizationParameters** (file-based - params.json)
   - Fields: feature_name (string), mean (float), std (float) × 6 features
   - Relationships: Generated from Dataset.csv training data, used by inference pipeline
   - Validation: Must contain exactly 6 features matching Dataset.csv columns
   - Storage: JSON file at `backend/ml_data/params.json`

3. **BiometricReading** (Django model - database entity)
   - Fields: patient_id (FK), timestamp (datetime), aX-gZ (6 floats)
   - **Removed fields**: RMS, Mean, Std, Skewness, Kurtosis (no longer stored)
   - Relationships: Belongs to Patient, created from MQTT messages
   - State transitions: Created → Stored → Used for inference

4. **TrainedModel** (file-based - .pkl/.h5)
   - Metadata: model_type (RF/SVM/LSTM/CNN), input_shape (6 features), trained_date (datetime)
   - Validation: Input layer must expect 6-dimensional vectors
   - Storage: `backend/ml_models/*.pkl` or `backend/dl_models/*.h5`

### API Contracts

**No new API endpoints** - This is an internal refactoring feature. Existing inference endpoint signature remains unchanged:

```
POST /api/ml/predict/
Body: {"sensor_data": [aX, aY, aZ, gX, gY, gZ]}
Response: {"tremor_severity": float, "confidence": float}
```

**Internal contract changes**:
- Training scripts expect Dataset.csv with 6 columns (aX, aY, aZ, gX, gY, gZ)
- Inference pipeline expects 6-element array as input
- MQTT messages must contain 6 numeric sensor values
- params.json must contain exactly 6 feature entries

### Integration Scenarios

See `quickstart.md` for:

1. **Training Workflow**: How to retrain all models with 6-feature Dataset.csv
2. **Normalization Generation**: How to regenerate params.json with correct statistics
3. **Model Validation**: How to verify model input shapes match 6 features
4. **Inference Testing**: How to test inference pipeline with 6-element sensor arrays
5. **MQTT Simulation**: How to send test messages with 6 sensor values
6. **Database Migration**: How to apply BiometricReading schema changes
7. **Performance Validation**: How to measure inference latency (<70ms requirement)
8. **Accuracy Verification**: How to validate model performance (F1 ≥ 0.85 requirement)

### Technology Choices

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Feature Selection | Use only raw Dataset.csv columns (6 features) | Eliminates schema mismatch, reduces latency, simplifies pipeline | Keep statistical features (rejected: not in training data) |
| Normalization Storage | JSON file (params.json) with mean/std per feature | Human-readable, easy to regenerate, version-controllable | Pickle file (less readable), database storage (overkill) |
| Model Validation | Introspection at startup to check input shapes | Fail-fast approach prevents silent errors, no runtime overhead | Runtime validation per prediction (too slow) |
| Migration Strategy | Django migration to remove unused fields | Django standard, reversible, preserves existing data temporarily | Manual SQL (error-prone), new table (unnecessary) |
| Training Approach | Sequential retraining (ML → DL) | Simpler debugging, lower memory usage | Parallel training (faster but complex) |
| Testing Strategy | Pytest with model shape assertions | Automated validation, fast feedback | Manual testing (error-prone) |

## Phase 2: Task Planning Strategy

*This phase is handled by `/speckit.tasks` command (NOT part of `/speckit.plan`)*

The tasks will be organized by user story:

1. **Setup Phase**: Install dependencies, verify Dataset.csv, backup existing models
2. **User Story 1 (P1)**: Update training scripts, regenerate normalization params, validate input shapes
3. **User Story 2 (P2)**: Retrain ML models (RF, SVM) with 6 features, verify accuracy
4. **User Story 3 (P3)**: Retrain DL models (LSTM, CNN) with 6 features, verify accuracy
5. **User Story 4 (P4)**: Update MQTT parser, migrate BiometricReading model, update inference pipeline
6. **Polish Phase**: Performance validation (<70ms latency), accuracy testing (F1 ≥ 0.85), integration tests

Expected task count: ~30-35 tasks
- Setup: ~5 tasks
- US1 (Schema Fix): ~8 tasks
- US2 (ML Retraining): ~6 tasks
- US3 (DL Retraining): ~6 tasks
- US4 (Data Flow): ~7 tasks
- Polish: ~5 tasks

## Dependencies

### Internal Dependencies

- **Dataset.csv**: Training data file must exist with 6 columns (aX, aY, aZ, gX, gY, gZ)
- **Existing ML/DL infrastructure**: Training scripts, model architectures, inference pipeline
- **MQTT subscription**: Active MQTT client must be running to test message parsing
- **BiometricReading model**: Existing Django model that stores sensor data

### External Dependencies

- **IoT Device**: Wearable glove must send MQTT messages with 6 sensor values
- **Supabase PostgreSQL**: Database must be accessible for model migration
- **Python libraries**: scikit-learn, tensorflow/keras, pandas, numpy (already installed)
- **Django**: Version 5.x with Django REST Framework and Channels (already installed)

### Validation Dependencies

- **pytest**: For automated model validation and shape testing
- **Performance profiler**: To measure inference latency (<70ms requirement)
- **Test dataset**: Holdout data for model accuracy validation (F1 ≥ 0.85)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Retrained models perform worse than originals | Medium | High | Validate on test set before deployment, rollback if F1 < 0.80 |
| Inference latency exceeds 70ms after refactoring | Low | High | Profile inference pipeline, ensure feature removal reduces compute time |
| Dataset.csv missing or has wrong schema | Low | High | Add validation script to verify column names and data types before training |
| MQTT messages have unexpected format | Medium | Medium | Implement robust parsing with error handling and logging |
| Django migration causes data loss | Low | High | Test migration on local copy first, backup production data |
| Model files too large for git (>100MB) | High | Low | Already gitignored, use external storage or download links |
| Normalization params calculated incorrectly | Medium | High | Add unit tests to verify mean/std calculations against manual computation |
| Model input shape mismatch not caught until runtime | Medium | Medium | Implement startup validation to check model dimensions |

## Success Metrics (from spec.md)

- **SC-001**: Inference latency (sensor reading to prediction) remains under 70ms for 95% of requests
- **SC-002**: Model validation accuracy (F1 score) is within 5% of previous performance (target: F1 ≥ 0.85 for tremor detection)
- **SC-003**: System processes 100 consecutive sensor readings without dimension mismatch errors
- **SC-004**: Database storage per biometric reading is reduced by at least 60% (from 15+ fields to 6 fields)
- **SC-005**: Training script completes successfully with 6-feature input and produces valid model files
- **SC-006**: Normalization parameters file (params.json) contains exactly 6 entries (one per feature axis)
- **SC-007**: All four model types (RF, SVM, LSTM, CNN) accept 6-dimensional input without errors
- **SC-008**: System startup validation detects and rejects models with incorrect input dimensions
- **SC-009**: Zero prediction errors due to feature dimension mismatch in 24 hours of continuous operation
- **SC-010**: MQTT message processing extracts exactly 6 sensor values from each message

## Next Steps

1. ✅ **Phase 0 Complete**: Generate `research.md` with technical decisions (NEXT)
2. ⏭️ **Phase 1 Pending**: Generate `data-model.md`, `quickstart.md`
3. ⏭️ **Run `/speckit.tasks`**: Generate task breakdown for implementation
4. ⏭️ **Run `/speckit.implement`**: Execute tasks systematically

---

**Plan Status**: ⏳ Ready for research phase (Phase 0)
**Constitution Compliance**: ✅ All checks passed
**Research Status**: ⏳ Pending (next step)
**Design Status**: ⏳ Pending (after research)
