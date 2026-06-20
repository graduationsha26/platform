# Implementation Plan: Deep Learning Models Training

**Branch**: `006-dl-models` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-dl-models/spec.md`

## Summary

Train two deep learning models (LSTM and 1D-CNN) on sequential IMU sensor data for Parkinson's tremor detection. Models must achieve ≥95% accuracy on test set. LSTM uses 2 layers (64, 32 units) with dropout 0.3. 1D-CNN uses 3 Conv1D layers with BatchNorm and MaxPooling. Both models trained with early stopping (patience 10 epochs) monitoring validation loss. Export trained models as .h5/.keras format with accompanying JSON metadata. Generate comparison report identifying best model for deployment.

## Technical Context

**Backend Stack**: Python 3.11+ with TensorFlow ≥2.13.0, Keras, NumPy, scikit-learn (for metrics)
**Frontend Stack**: Not applicable (backend-only feature)
**Database**: Not applicable (uses file-based data from Feature 004)
**Authentication**: Not applicable (training scripts, not API endpoints)
**Testing**: pytest for training script validation, model loading tests
**Project Type**: Backend Python scripts in `backend/dl_models/`
**Real-time**: Not applicable (offline training)
**Integration**: Reads sequence data files from Feature 004 (`backend/ml_data/processed/`)
**AI/ML**: TensorFlow/Keras deep learning models exported as .h5 or .keras format
**Performance Goals**:
  - Training time: <15 minutes per model on standard laptop (CPU)
  - Inference time: <100ms per single sequence
  - Model accuracy: ≥95% on test set
**Constraints**:
  - CPU training by default (GPU optional if available)
  - Local development only (no cloud training)
  - Models must fit in memory (<1GB per model)
**Scale/Scope**:
  - Dataset size: ~446 training samples, ~110 test samples (from Feature 004)
  - Sequence length: 50-100 timesteps per sample
  - Features per timestep: 6 (aX, aY, aZ, gX, gY, gZ)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

**Initial Check (Before Phase 0)**:
- [X] **Monorepo Architecture**: Feature fits in `backend/dl_models/` structure (backend-only, no frontend)
- [X] **Tech Stack Immutability**: Uses TensorFlow/Keras (already mandated by constitution for AI models - see "AI Model Serving" principle)
- [X] **Database Strategy**: No database access needed - loads data from files produced by Feature 004
- [X] **Authentication**: Not applicable - training scripts run locally, not API endpoints
- [X] **Security-First**: No secrets required for training scripts
- [X] **Real-time Requirements**: Not applicable - offline batch training
- [X] **MQTT Integration**: Not applicable - uses preprocessed sequence data from Feature 004
- [X] **AI Model Serving**: Produces .h5/.keras model files per constitution (TensorFlow/Keras format)
- [X] **API Standards**: Not applicable - training scripts, not REST API
- [X] **Development Scope**: Local development only, no Docker/CI/CD

**Post-Design Re-Check (After Phase 1)**:
- [X] **Monorepo Architecture**: Design confirms backend-only implementation in `backend/dl_models/` with no frontend changes
- [X] **Tech Stack Immutability**: Research confirms use of TensorFlow ≥2.13.0 (constitutional tech), no new frameworks added
- [X] **Database Strategy**: Data model confirms file-based data loading (NumPy .npy files), no database access
- [X] **Authentication**: Training scripts have no API endpoints, no authentication needed
- [X] **Security-First**: No secrets in implementation (no API keys, credentials, or environment variables needed)
- [X] **Real-time Requirements**: Confirmed offline batch training, no WebSocket or real-time components
- [X] **MQTT Integration**: Confirmed use of preprocessed data from Feature 004, no MQTT client needed
- [X] **AI Model Serving**: Design confirms .h5 model export (HDF5 format), meets constitutional requirement
- [X] **API Standards**: No API endpoints in this feature, serving will be added in Feature 007
- [X] **Development Scope**: Confirmed local training only, no Docker/CI/CD in project structure

**Result**: ✅ **ALL PASS** - No constitutional violations in initial check or post-design re-check

## Project Structure

### Documentation (this feature)

```text
specs/006-dl-models/
├── spec.md              # Feature specification (✅ complete)
├── plan.md              # This file (Phase 1 output)
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (validation scenarios)
└── checklists/
    └── requirements.md  # Spec quality validation (✅ complete)
```

### Source Code (repository root)

```text
backend/
├── dl_models/                     # NEW: Deep learning models package
│   ├── __init__.py               # Package initializer
│   ├── scripts/                  # Training scripts
│   │   ├── __init__.py
│   │   ├── train_lstm.py         # US1: LSTM model training
│   │   ├── train_cnn_1d.py       # US2: 1D-CNN model training
│   │   ├── compare_models.py     # Model comparison report
│   │   └── utils/                # Shared utilities
│   │       ├── __init__.py
│   │       ├── model_io.py       # Model save/load, data loading
│   │       ├── evaluation.py     # Performance metrics computation
│   │       └── architectures.py  # Model architecture builders
│   ├── models/                   # Output: trained model files (gitignored)
│   │   ├── .gitkeep             # Keep directory in git
│   │   ├── lstm_model.h5        # LSTM trained model (gitignored)
│   │   ├── lstm_model.json      # LSTM metadata (gitignored)
│   │   ├── cnn_1d_model.h5      # 1D-CNN trained model (gitignored)
│   │   ├── cnn_1d_model.json    # 1D-CNN metadata (gitignored)
│   │   └── comparison_report.txt # Model comparison (gitignored)
│   └── README.md                 # Usage documentation
│
├── ml_data/                      # Feature 004 outputs (dependency)
│   └── sequences/                # Input: sequence data for DL training
│       ├── train_sequences.npy   # Training sequences (N, timesteps, 6)
│       ├── train_labels.npy      # Training labels (N,)
│       ├── test_sequences.npy    # Test sequences (M, timesteps, 6)
│       └── test_labels.npy       # Test labels (M,)
│
└── .gitignore                    # MODIFY: Add dl_models/models/*.h5, *.json

```

**Structure Decision**:
- **Backend-only feature**: No frontend components needed (training scripts run locally)
- **Parallel to Feature 005**: Similar structure to `backend/ml_models/` but for deep learning
- **Separate package**: `backend/dl_models/` keeps DL models isolated from traditional ML models
- **Utility sharing**: `utils/` module provides reusable functions for both training scripts
- **Model gitignore**: Trained models are large (50-500MB) and excluded from version control
- **File format**: Use .h5 format (widely supported) over .keras (newer, less compatible)

## Complexity Tracking

*No constitutional violations - this section is empty.*
