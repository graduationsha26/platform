# Implementation Plan: Gravity Filter Fix for ML Pipeline

**Branch**: `040-gravity-filter-fix` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/040-gravity-filter-fix/spec.md`

## Summary

ML models are predicting tremor based on static hand orientation (gravity) rather than actual shaking. This plan implements a 2nd-order Butterworth high-pass filter (cutoff 0.5 Hz) applied to accelerometer channels only, inserted into the training data pipeline, model metadata, and live inference preprocessing. The filter uses causal (forward-only) application via second-order sections (SOS) in both training and live contexts to guarantee mathematical equivalence.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: N/A (no frontend changes in this feature)
**Database**: N/A (no database schema changes)
**Authentication**: N/A (no auth changes)
**Testing**: Manual validation via metrics comparison and signal analysis
**Project Type**: monorepo (backend/, frontend/, firmware/)
**Real-time**: Django Channels WebSocket for live tremor data (affected by filter sync)
**Integration**: Bidirectional MQTT (sensor data passes through filter before inference)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django `inference` app
**Performance Goals**: Inference latency remains under 5 seconds (existing constraint); filter adds <1ms overhead per window
**Constraints**: Local development only; scipy>=1.10.0 already in requirements.txt; sensor sampling rate ~37 Hz
**Scale/Scope**: All 4 models (RF, SVM, LSTM, CNN-1D) retrained; single shared filter implementation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes in `backend/` (ml_data, ml_models, dl_models, inference)
- [x] **Tech Stack Immutability**: Uses scipy (already in requirements.txt) and existing stack only
- [x] **Database Strategy**: No database changes
- [x] **Authentication**: No authentication changes
- [x] **Security-First**: No secrets involved; filter parameters stored in model metadata JSON
- [x] **Real-time Requirements**: Live filter integrated into existing Django Channels WebSocket pipeline via PreprocessingService
- [x] **MQTT Integration**: No MQTT protocol changes; filter applied after data arrives via existing MQTT handlers
- [x] **AI Model Serving**: Models continue to be served via Django `inference` app (.pkl and .h5)
- [x] **API Standards**: No API contract changes; inference endpoint behavior unchanged
- [x] **Development Scope**: Local development only, no Docker/CI/CD

**Result**: PASS - No constitutional violations.

## Project Structure

### Documentation (this feature)

```text
specs/040-gravity-filter-fix/
├── plan.md              # This file
├── research.md          # Phase 0: filter design research
├── data-model.md        # Phase 1: metadata schema extension
├── quickstart.md        # Phase 1: integration scenarios
└── contracts/           # Phase 1: N/A (no API changes)
```

### Source Code (repository root)

```text
backend/
├── ml_data/
│   ├── utils/
│   │   └── gravity_filter.py          # NEW: Shared gravity filter module
│   └── scripts/
│       └── 4_psmad_pipeline.py        # MODIFY: Apply gravity filter before windowing
├── ml_models/
│   ├── scripts/
│   │   ├── train_random_forest.py     # MODIFY: Save filter_params to metadata
│   │   └── train_svm.py              # MODIFY: Save filter_params to metadata
│   └── rf_model_metrics_v1.json       # REGENERATED: With filter_params section
│   └── svm_model_metrics_v1.json      # REGENERATED: With filter_params section
├── dl_models/
│   ├── scripts/
│   │   ├── train_lstm.py             # MODIFY: Save filter_params to metadata
│   │   └── train_cnn_1d.py           # MODIFY: Save filter_params to metadata
├── inference/
│   └── services.py                    # MODIFY: PreprocessingService applies gravity filter
└── requirements.txt                   # NO CHANGE: scipy already present
```

**Structure Decision**: This feature creates one new file (`gravity_filter.py`) and modifies existing files. The filter module is placed in `ml_data/utils/` because it's a data processing utility shared between training scripts and the inference service. No new Django apps, no frontend changes, no database migrations.

## Design Decisions

### D1: Causal Filter for Both Training and Live (Critical)

**Decision**: Use `scipy.signal.sosfilt` (causal, forward-only) for both training data and live inference, NOT `filtfilt` (zero-phase) for training.

**Rationale**: FR-008 requires mathematical equivalence between training and live outputs. `filtfilt` applies the filter forward and backward (zero-phase), which is impossible in real-time streaming. Using `sosfilt` for both guarantees identical outputs for identical inputs. At 0.5 Hz cutoff vs 3-12 Hz tremor band, the phase distortion from causal filtering is negligible (<5 degrees at 3 Hz for a 2nd-order Butterworth).

**Tradeoff**: Slightly more phase distortion in training data compared to zero-phase filtering, but this is acceptable because:
1. The cutoff (0.5 Hz) is far below the tremor band (3-12 Hz)
2. Feature extraction (RMS, mean, std, etc.) is phase-invariant
3. Perfect train-live equivalence prevents the #1 cause of ML deployment bugs

### D2: Filter Parameters in Model Metadata

**Decision**: Store filter parameters (`type`, `order`, `cutoff_hz`, `sampling_rate_hz`, `sos_coefficients`) in each model's JSON metadata file under a `filter_params` key.

**Rationale**: Each model must know exactly how its training data was filtered so the inference service can reproduce it. Storing SOS coefficients (not just design parameters) eliminates any floating-point differences from re-designing the filter at inference time.

### D3: Shared Filter Module

**Decision**: Create `backend/ml_data/utils/gravity_filter.py` as a single source of truth for filter design and application, imported by both training scripts and inference service.

**Rationale**: Avoids code duplication between 4+ training scripts and the inference service. Any filter change propagates automatically. The module provides both batch processing (training) and stateful streaming (live inference) APIs.

### D4: Filter Applied Before Normalization

**Decision**: Apply gravity filter to raw accelerometer data before StandardScaler normalization and before feature extraction.

**Rationale**: Gravity is a physical artifact that should be removed from the raw signal. Normalizing first would scale the gravity component into the features. The processing chain is: raw → gravity filter → normalize → extract features / feed to DL model.

### D5: Accelerometer-Only Filtering

**Decision**: Apply high-pass filter to columns [aX, aY, aZ] only. Leave [gX, gY, gZ] unchanged.

**Rationale**: Gyroscopes measure angular velocity, not acceleration. They have no gravity component. Filtering them would remove valid low-frequency rotational data.

## Implementation Flow

### Phase Order

```
Phase 1 (US1): Gravity Filter Module + Pipeline Integration
    ↓
Phase 2 (US2): Model Retraining (depends on filtered data from Phase 1)
    ↓
Phase 3 (US3): Live Inference Sync (depends on filter params from Phase 2)
```

### Phase 1: Data Pipeline (US1)

1. **Create `gravity_filter.py`** with:
   - `design_gravity_filter(cutoff_hz, fs, order)` → returns SOS coefficients and filter params dict
   - `apply_gravity_filter(signal, sos, accel_columns=[0,1,2])` → filters accelerometer columns using `sosfilt` with steady-state initial conditions
   - `apply_gravity_filter_streaming(sample, sos, zi)` → processes one sample/chunk for live use, returns (filtered_sample, updated_zi)
   - `get_filter_params_dict(cutoff_hz, fs, order, sos)` → serializable dict for metadata

2. **Modify `4_psmad_pipeline.py`**:
   - After data loading and column renaming, before windowing
   - Design filter with `cutoff_hz=0.5, fs=computed_sampling_rate, order=2`
   - Apply filter to full signal (all accelerometer columns)
   - Save filter params to `backend/ml_data/processed/filter_params.json`
   - Filtered data flows into existing windowing → feature extraction pipeline

### Phase 2: Model Retraining (US2)

3. **Modify training scripts** (all 4):
   - Load filter params from `backend/ml_data/processed/filter_params.json`
   - Include `filter_params` in saved model metadata JSON
   - Retrain on gravity-filtered features/sequences
   - Compare metrics with previous models

4. **Retrain all models**:
   - RF and SVM: from `ready_for_training_features.csv` (now gravity-filtered)
   - LSTM and CNN-1D: from sequences (now gravity-filtered via `1_preprocess.py` or `3_sequence_preparation.py` using filtered input)

### Phase 3: Live Inference Sync (US3)

5. **Modify `PreprocessingService` in `services.py`**:
   - Import `gravity_filter` module
   - On model load, extract `filter_params` from metadata
   - Reconstruct SOS coefficients from metadata
   - Apply gravity filter to accelerometer channels before existing normalization
   - For ML models: filter the 6-value input, then normalize
   - For DL models: filter the 128×6 sequence, then normalize

## Complexity Tracking

> No constitutional violations. No complexity tracking needed.
