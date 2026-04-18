# Data Model: ML Pipeline Optimization & Confidence Scoring

**Feature**: 043-ml-pipeline-optimize  
**Date**: 2026-04-18

---

## Overview

This feature involves no Django ORM model changes and no database schema changes. The entities below are runtime/file-system data structures — not database tables.

---

## Entity 1: Feature Window

A fixed-length slice of 6-axis sensor readings used as the classifier input unit.

| Attribute | Value (v2) | Value (v3) | Notes |
|-----------|-----------|-----------|-------|
| `window_size` | 200 samples | **100 samples** | Halved for lower latency |
| `stride` | 30 samples | **15 samples** | Halved proportionally |
| `axes` | aX, aY, aZ, gX, gY, gZ | unchanged | 6 axes |
| `sampling_rate_hz` | 250 Hz | unchanged | |
| `feature_count` | 42 | unchanged | 7 stats × 6 axes |
| `feature_types` | mean, std, max, min, rms, median, dominant_freq | unchanged | |

**State transition**: Raw MQTT sensor JSON → physical-unit array (WINDOW_SIZE × 6) → 42-feature vector → scaled (StandardScaler) → classifier input.

---

## Entity 2: Model Artifact Set (v3)

A versioned group of files produced by one training run. All three files must be present and consistent.

| File | Path | Description |
|------|------|-------------|
| `rf_model_v3.pkl` | `backend/ml_models/models/` | Trained RandomForestClassifier (scikit-learn) |
| `rf_model_v3_scaler.pkl` | `backend/ml_models/models/` | StandardScaler fitted on v3 training features |
| `rf_model_v3.json` | `backend/ml_models/models/` | Metadata: window_size=100, stride=15, feature list, performance metrics |
| `rf_model_metrics_v3.json` | `backend/ml_models/models/` | Extended per-fold CV metrics |

**Validation rules**:
- `rf_model_v3.json` must contain `pipeline_params.window_size = 100` and `pipeline_params.stride = 15`
- `rf_model_v3.json` must reference `scaler_file = rf_model_v3_scaler.pkl`
- All four files committed to git (`.gitignore` rules relaxed per FR-009)

**Prior versions retained**: `rf_model_v1.*` and `rf_model_v2.*` remain in `backend/ml_models/models/` as a fallback. No deletion required.

---

## Entity 3: Live Prediction Line

A single line of terminal output produced per inference cycle in the live test script.

| Field | Format | Example |
|-------|--------|---------|
| `timestamp` | `[HH:MM:SS.mmm]` | `[17:57:19.659]` |
| `state_indicator` | emoji | `✅` (NORMAL) or `⚠️` (TREMOR) |
| `state_label` | string + class index | `NORMAL (0)` or `TREMOR (1)` |
| `confidence` | float, 1 decimal, percent | `Confidence: 95.5%` |

**Full format**: `[HH:MM:SS.mmm] ✅ NORMAL (0) | Confidence: XX.X%`

**Derivation**:
- `timestamp`: wall clock at prediction time, millisecond precision
- `state_indicator` + `state_label`: derived from `argmax(predict_proba())`
- `confidence`: `max(predict_proba()) * 100`, rounded to 1 decimal

**Invariants**:
- Class 0 always maps to NORMAL + ✅
- Class 1 always maps to TREMOR + ⚠️
- Every prediction line includes all four fields — no field is ever omitted, even for low-confidence predictions

---

## Inference Service Configuration (runtime)

The inference service `backend/inference/services.py` uses two in-memory dictionaries that map model aliases to file paths. After this feature, the `'rf'` alias points to v3:

| Key | Before | After |
|-----|--------|-------|
| `model_map['rf']` | `rf_model_v2.pkl` | `rf_model_v3.pkl` |
| `metadata_map['rf']` | `rf_model_v2.json` | `rf_model_v3.json` |

Scaler path is not in the map — it is read from `metadata['scaler_file']` at load time. No additional change required.
