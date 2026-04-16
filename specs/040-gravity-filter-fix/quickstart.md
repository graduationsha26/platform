# Quickstart: Gravity Filter Fix for ML Pipeline

**Feature**: 040-gravity-filter-fix | **Date**: 2026-04-13

## Overview

This document describes how to run the updated pipeline end-to-end after the gravity filter is implemented. No API changes are needed — the fix is internal to the data processing and inference services.

## Prerequisites

- Python 3.14+ with dependencies from `backend/requirements.txt` installed
- scipy >= 1.10.0 (already in requirements.txt)
- PSMAD dataset available at expected paths
- Existing model training infrastructure functional

## Scenario 1: Run Updated Training Pipeline

### Step 1: Generate Gravity-Filtered Features

```bash
cd backend
python -m ml_data.scripts.4_psmad_pipeline
```

**What happens**:
- Loads PSMAD dataset
- Computes sampling rate from timestamps (~37 Hz)
- Designs 2nd-order Butterworth highpass filter at 0.5 Hz cutoff
- Applies filter to accelerometer columns (aX, aY, aZ) only
- Saves `filter_params.json` to `ml_data/processed/`
- Windows data and extracts features (42 features: 30 time-domain + 12 FFT)
- Outputs `ready_for_training_features.csv` with gravity-filtered features

**Verify**: Check `ml_data/processed/filter_params.json` exists and contains SOS coefficients.

### Step 2: Retrain ML Models

```bash
cd backend
python -m ml_models.scripts.train_random_forest
python -m ml_models.scripts.train_svm
```

**What happens**:
- Loads gravity-filtered features from `ready_for_training_features.csv`
- Trains model with hyperparameter search
- Saves model `.pkl` and metadata `.json` (now including `filter_params`)

**Verify**: Check model metadata JSON contains `filter_params` key.

### Step 3: Retrain DL Models

```bash
cd backend
python -m dl_models.scripts.train_lstm
python -m dl_models.scripts.train_cnn_1d
```

**What happens**:
- Note: DL models require sequence data. The sequence preparation script (`3_sequence_preparation.py`) must run on gravity-filtered preprocessed data first.
- Trains LSTM/CNN-1D on gravity-filtered sequences
- Saves model `.h5` and metadata `.json` (now including `filter_params`)

**Verify**: Check model metadata JSON contains `filter_params` key.

## Scenario 2: Live Inference with Gravity Filter

### No Action Required

The inference service automatically picks up gravity filter parameters from the loaded model's metadata JSON. When a model with `filter_params` is loaded:

1. `PreprocessingService` extracts SOS coefficients from metadata
2. Applies the same highpass filter to incoming accelerometer data
3. Proceeds with existing normalization and prediction pipeline

### Verify Equivalence

To verify training-live filter equivalence:

1. Take a sample window from the training dataset (before feature extraction)
2. Run it through the training pipeline filter
3. Send the same raw data through the inference API
4. Compare the preprocessed values — they should match within 1e-6

## Scenario 3: Validate Gravity Removal

### Quick Sanity Check

After running the updated pipeline:

1. **Motionless hand test**: A recording of a static hand should produce near-zero mean on filtered accelerometer axes (previously ~1g on the gravity-aligned axis)
2. **Orientation invariance**: Recordings of the same tremor intensity at different hand angles should produce similar feature values (previously varied with orientation)
3. **Tremor preservation**: Filtered tremor recordings should retain oscillatory patterns in the 3-12 Hz band

## File Artifacts Produced

| Step | File | Location |
|------|------|----------|
| Pipeline | filter_params.json | `backend/ml_data/processed/` |
| Pipeline | ready_for_training_features.csv | `backend/ml_data/processed/` |
| RF Train | rf_model_v1.pkl | `backend/ml_models/models/` |
| RF Train | rf_model_metrics_v1.json | `backend/ml_models/` |
| SVM Train | svm_model_v1.pkl | `backend/ml_models/models/` |
| SVM Train | svm_model_metrics_v1.json | `backend/ml_models/` |
| LSTM Train | lstm_model.h5 | `backend/dl_models/models/` |
| LSTM Train | lstm_model.json | `backend/dl_models/` |
| CNN Train | cnn_1d_model.h5 | `backend/dl_models/models/` |
| CNN Train | cnn_1d_model.json | `backend/dl_models/` |
