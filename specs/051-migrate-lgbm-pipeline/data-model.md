# Phase 1 Data Model: Migrate LGBM Tremor Classification Pipeline

**Feature**: 051-migrate-lgbm-pipeline | **Date**: 2026-06-20

This feature is a file-based ML pipeline plus an inference rewire. There are **no Django/
PostgreSQL models or migrations**. The "entities" below are data artifacts (files in memory
and on disk) and their schemas.

---

## Entity 1: Raw Recording (input)

One CSV file inside one of the three labeled group folders.

| Field | Type | Notes |
|-------|------|-------|
| `T` (Timestamp) | float (ms) | Monotonic per file; used to build the resample time base |
| `AX, AY, AZ` | float (m/s²) | Accelerometer, 3 axes |
| `GX, GY, GZ` | float (°/s) | Gyroscope, 3 axes |

- **Source folders** → label:
  - `Clean Dataset – Control Group` → `0` (Non-Tremor)
  - `Clean Dataset – Parkinson's Group` → `1` (Tremor)
  - `Clean Dataset – Voluntary Group` → `2` (Voluntary)
- **file_id** = filename stem (e.g. `ID01010100`), used as the GroupKFold grouping key.
- **Validation**: skip files that are empty, malformed, or shorter than one 67-sample window
  after resampling; log and continue (spec edge cases).

---

## Entity 2: Analysis Window (intermediate)

A 1-second slice of one resampled, band-pass-filtered recording.

| Property | Value |
|----------|-------|
| Sampling rate | 66.67 Hz (after resample) |
| Length | 67 samples (`int(round(66.67 * 1.0))`) |
| Stride | 67 (non-overlapping) for training |
| Axes | 6 (AX, AY, AZ, GX, GY, GZ) |
| Band | 0.5–20 Hz, 4th-order Butterworth, zero-phase |

State transitions (per recording): `raw → resampled(66.67Hz) → bandpassed → windowed`.

---

## Entity 3: Feature Vector (66 features, axis-major)

Produced by `extract_features_66()` for one Analysis Window. Order is fixed and shared by
training, inference service, and `test_AI_live.py`.

Per axis (× 6 axes = 66 total), in this order:

| # | Feature | Definition |
|---|---------|------------|
| 1 | `{axis}_mean` | mean |
| 2 | `{axis}_std` | standard deviation |
| 3 | `{axis}_median` | median |
| 4 | `{axis}_q1` | 25th percentile |
| 5 | `{axis}_q3` | 75th percentile |
| 6 | `{axis}_min` | minimum |
| 7 | `{axis}_max` | maximum |
| 8 | `{axis}_peak1_freq` | frequency (Hz) of strongest FFT bin in 0.5–20 Hz (DC-removed) |
| 9 | `{axis}_peak1_amp` | magnitude of that bin |
| 10 | `{axis}_peak2_freq` | frequency (Hz) of 2nd-strongest bin |
| 11 | `{axis}_peak2_amp` | magnitude of 2nd bin |

Axis order: `AX, AY, AZ, GX, GY, GZ`. Total = 11 × 6 = **66**.

---

## Entity 4: Combined Processed Dataset (`backend/ml_data/combined_processed_data.csv`)

The persisted artifact written **before** training (spec FR-003 / SC-001).

| Column group | Columns | Type |
|--------------|---------|------|
| Features | 66 feature columns (Entity 3 order) | float |
| `file_id` | originating recording stem | string |
| `label` | 0 / 1 / 2 | int |

- One row per Analysis Window across all three groups.
- `inf`/`-inf` → `NaN` → dropped before save.
- **Determinism**: same raw inputs → same row count and class distribution (spec
  acceptance scenario US1.2).

---

## Entity 5: Tremor Classification Model (`backend/ml_models/lgbm_tremor_model.pkl`)

A fitted `imblearn.Pipeline([SMOTE, LGBMClassifier])` serialized via joblib.

| Aspect | Value |
|--------|-------|
| Input | feature vector(s) of length 66 (no scaler) |
| Output | class in {0,1,2} via `predict`; 3 probabilities via `predict_proba` |
| Classes | 0=Non-Tremor, 1=Tremor, 2=Voluntary |
| Hyperparameters | pinned (from one-time search), `random_state=42` |

### Sidecar metadata (`backend/ml_models/lgbm_tremor_model.json`)

See [contracts/training-artifacts.md](./contracts/training-artifacts.md) for the full schema:
`model_type, classes, n_features, feature_names, pipeline{fs_hz,window_samples,bandpass_hz,scaler:null},
hyperparameters, metrics{...}, trained_at`.

---

## Entity 6: Live Rolling Buffer (runtime, `test_AI_live.py`)

| Property | Value |
|----------|-------|
| Structure | `collections.deque(maxlen=≈30)` |
| Native rate | ~30 Hz (firmware MQTT transmit rate) |
| Holds | 1 second of 6-axis samples |
| Transform per tick | resample → 67 samples @ 66.67 Hz → band-pass → 66 features |

---

## Entity 7: Live Evaluation Result Line (output, `test_AI_live.py`)

Exactly these fields, in order (spec FR-013 / SC-005):

| Field | Source |
|-------|--------|
| `Sample` | incrementing prediction index |
| `Prediction` | argmax class label (Non-Tremor / Tremor / Voluntary) |
| `Confidence` | max class probability (%) |
| `Precision` | model's overall validated precision (constant, from metadata) |
| `Non-Tremor %` | P(class 0) (%) |
| `Tremor %` | P(class 1) (%) |
| `Voluntary %` | P(class 2) (%) |

See [contracts/live-output-format.md](./contracts/live-output-format.md).

---

## Relationships

```
Raw Recording (N files × 3 groups)
   └─ resample → bandpass → window ──> Analysis Window (M windows)
                                          └─ extract_features_66 ──> Feature Vector (66)
                                                                       └─ + file_id + label
Combined Processed Dataset (CSV) ──train(SMOTE+LGBM, pinned)──> Tremor Classification Model (.pkl + .json)
                                                                   ├─ served by inference/services.py
                                                                   └─ loaded by test_AI_live.py
Live MQTT stream (~30Hz) ─> Live Rolling Buffer ─resample/bandpass/features─> Model ─> Live Result Line
```
