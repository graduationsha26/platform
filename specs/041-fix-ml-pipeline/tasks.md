# Tasks: Fix ML Pipeline Unit Mismatch

**Input**: Design documents from `/specs/041-fix-ml-pipeline/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md  
**Tests**: Not requested — no test tasks included  
**Stride Update**: Window=200, Stride=30 (per user request for higher overlap / responsiveness)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed — all directories and dependencies already exist.

*(No tasks — existing project structure and dependencies are sufficient)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Rewrite the shared feature extraction module that all three user stories depend on.

**CRITICAL**: US1, US2, and US3 all import from `feature_extractors.py`. This must be done first.

- [X] T001 Rewrite `backend/ml_data/utils/feature_extractors.py` to replace the current feature set (5 time-domain + 2 FFT per axis = 42) with the new 7-feature set per axis: mean, std, max, min, RMS, median, dominant_freq (via `np.fft`). Create a single `extract_window_features(window_2d: np.ndarray, axis_names: list[str], sampling_rate_hz: float) -> np.ndarray` function that accepts a 2D array of shape (window_size, 6), extracts all 7 features for each of the 6 axes, and returns a 1D array of 42 features in deterministic axis-major order: [mean_aX, std_aX, max_aX, min_aX, rms_aX, median_aX, dominant_freq_aX, mean_aY, ...]. Also create a `get_feature_names(axis_names: list[str]) -> list[str]` function returning the 42 feature name strings in the same order. Remove the old functions (`calculate_skewness`, `calculate_kurtosis`, `extract_features_single_axis`, `extract_features_all_axes`, `extract_features_batch`, `extract_fft_features_single_axis`, `extract_fft_features_all_axes`, `get_fft_feature_names`) that are no longer needed. Keep `calculate_rms`, `calculate_mean`, `calculate_std` as internal helpers if useful, but the public API is just `extract_window_features` and `get_feature_names`.

**Checkpoint**: Foundation ready — the shared feature extraction function is in place. All user stories can now proceed.

---

## Phase 3: User Story 1 — Data Aggregation, Normalization & Feature Extraction (Priority: P1) MVP

**Goal**: Read Excel files from `Data v2/Normal/` (label 0) and `Data v2/Parkinson/` (label 1), convert raw ADC values to physical units, apply sliding window (200/30), extract 42 features per window, and save X/y matrices.

**Independent Test**: Run `py backend/ml_data/scripts/5_aggregate_and_extract.py` and verify: (1) `X_features.npy` exists with shape (N, 42), (2) `y_labels.npy` exists with shape (N,) containing 0s and 1s, (3) no NaN/Inf values, (4) accelerometer feature values are in physical-unit ranges.

- [X] T002 [US1] Create `backend/ml_data/scripts/5_aggregate_and_extract.py`. The script must: (a) scan `Data v2/Normal/` for all `.xlsx` files and assign label 0, scan `Data v2/Parkinson/` for all `.xlsx` files and assign label 1; (b) for each file, read columns `AcX, AcY, AcZ, GyX, GyY, GyZ` using openpyxl/pandas; (c) convert raw ADC to physical units: accelerometer columns divided by 16384.0 then multiplied by 9.81 (→ m/s²), gyroscope columns divided by 131.0 (→ °/s); (d) skip files with fewer than 200 rows (log a warning); (e) apply sliding window with window_size=200 and stride=30; (f) for each window, call `extract_window_features()` from `ml_data.utils.feature_extractors`; (g) collect all feature vectors and labels; (h) save as `backend/ml_data/processed/X_features.npy` and `backend/ml_data/processed/y_labels.npy`; (i) print summary: total files processed, total windows extracted, feature matrix shape, label distribution.

- [X] T003 [US1] Run `5_aggregate_and_extract.py` and validate output: confirm X_features.npy shape is (N, 42), y_labels.npy shape is (N,), no NaN/Inf, and print sample statistics (mean/std of a few feature columns) to verify physical-unit ranges.

**Checkpoint**: Feature matrices are ready for model training. US1 is complete and independently verifiable.

---

## Phase 4: User Story 2 — Train Model & Export Metadata (Priority: P1)

**Goal**: Load X/y matrices, fit StandardScaler, train RandomForestClassifier with GridSearchCV, save model v2 + scaler v2 + metadata v2 JSON.

**Independent Test**: Verify `rf_model_v2.pkl`, `rf_model_v2_scaler.pkl`, and `rf_model_v2.json` exist in `backend/ml_models/models/`. Load them in a fresh Python session and confirm: model predicts on sample data, scaler transforms correctly, metadata JSON has 42 feature names and pipeline_params.

- [X] T004 [US2] Modify `backend/ml_models/scripts/train_random_forest.py` to: (a) change input loading from CSV to `.npy` files — load `backend/ml_data/processed/X_features.npy` and `backend/ml_data/processed/y_labels.npy`; (b) perform train/test split (80/20 stratified); (c) fit a `StandardScaler` on the training split and transform both train and test features; (d) train `RandomForestClassifier` with existing GridSearchCV setup; (e) save three artifacts to `backend/ml_models/models/`: `rf_model_v2.pkl` (trained model via joblib), `rf_model_v2_scaler.pkl` (fitted StandardScaler via joblib), `rf_model_v2.json` (metadata); (f) the metadata JSON must include: `version: 2`, `feature_names` (42-element list from `get_feature_names()`), `pipeline_params` object with `window_size: 200`, `stride: 30`, `mpu6050_accel_sensitivity: 16384.0`, `mpu6050_gyro_sensitivity: 131.0`, `accel_to_ms2: true`, `training_sampling_rate_hz: 250.0`, `fft_tremor_band_low_hz: 3.0`, `fft_tremor_band_high_hz: 12.0`, and `scaler_file: "rf_model_v2_scaler.pkl"`; (g) save metrics to `backend/ml_models/rf_model_metrics_v2.json`; (h) do NOT delete v1 files — keep them for reference; (i) remove the gravity filter embedding logic (no `filter_params` for v2); (j) update validate_data to accept the new feature count (still 42, but verify).

- [X] T005 [US2] Run `train_random_forest.py` and validate: confirm accuracy > 80%, verify all three v2 artifact files exist, load metadata and check `feature_names` has 42 entries, load scaler and verify it transforms a sample correctly.

**Checkpoint**: Trained model v2 artifacts are saved and validated. US2 is complete.

---

## Phase 5: User Story 3 — Synchronize Live Inference & Test Scripts (Priority: P1)

**Goal**: Update the PreprocessingService and live test script to use the new shared feature extraction, StandardScaler, and v2 model.

**Independent Test**: (1) Feed known synthetic data through PreprocessingService and verify 42-feature output. (2) Run `live_glove_test.py` with `--model` pointing to v2 and verify it loads model + scaler and processes MQTT data.

- [X] T006 [US3] Update `backend/inference/services.py` — `ModelLoader._get_model_path()`: change the `'rf'` mapping from `rf_model.pkl` to `rf_model_v2.pkl`. Update `_get_metadata_path()`: change `'rf'` mapping from `rf_model.json` to `rf_model_v2.json`.

- [X] T007 [US3] Update `backend/inference/services.py` — `ModelCache.get_model()`: after loading metadata, check if `scaler_file` key exists in metadata. If so, load the scaler `.pkl` from the same directory as the model and include it in the cached tuple. Change the cache return type to include the optional scaler: `(model_object, metadata_dict, scaler_or_None)`. Update all callers of `get_model()` in `InferenceService.predict()` to unpack the third element.

- [X] T008 [US3] Update `backend/inference/services.py` — `PreprocessingService._preprocess_ml()`: for v2 models (detected by checking if metadata contains `pipeline_params` or `scaler_file`), the method must: (a) expect input as a 2D array of shape (window_size, 6) — a full window of sensor readings, not a single 6-value row; (b) call `extract_window_features()` from `ml_data.utils.feature_extractors` to produce a 42-feature vector; (c) apply `scaler.transform()` using the loaded StandardScaler (passed as parameter or accessed from cache); (d) return the scaled feature vector ready for `model.predict()`. For v1 models (no `pipeline_params`), keep the existing behavior as a fallback. Also skip `_apply_gravity_filter()` when metadata has no `filter_params` (v2 models won't have it).

- [X] T009 [US3] Update `backend/live_glove_test.py`: (a) change default model path from `rf_model_v1.pkl` to `rf_model_v2.pkl`; (b) add `--scaler` CLI argument (default: `backend/ml_models/models/rf_model_v2_scaler.pkl`); (c) load the StandardScaler via joblib at startup alongside the model; (d) change `WINDOW_SIZE` from 100 to 200; (e) in `on_message()`, replace the separate `extract_features_all_axes` + `extract_fft_features_all_axes` calls with a single call to `extract_window_features()` from `ml_data.utils.feature_extractors`; (f) after feature extraction, apply `scaler.transform(feature_vector.reshape(1, -1))` before `model.predict()`; (g) update the docstring, comments, and log messages to reflect v2 model, 200-sample window, and ~6.7s warm-up at 30Hz; (h) update the assert to check for 42 features (still 42, but the composition changed).

**Checkpoint**: Live inference and Django API inference both use the same v2 pipeline. US3 is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T010 Verify end-to-end pipeline consistency: load `rf_model_v2.json` metadata and confirm `feature_names` matches the output of `get_feature_names(['aX','aY','aZ','gX','gY','gZ'])` from `feature_extractors.py`. This ensures training, inference, and live test all share the exact same feature order.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Empty — no setup needed
- **Phase 2 (Foundational)**: T001 — must complete before any user story
- **Phase 3 (US1)**: Depends on T001 — T002 → T003 (sequential)
- **Phase 4 (US2)**: Depends on T001 AND T003 (needs feature matrices from US1)
- **Phase 5 (US3)**: Depends on T001 AND T005 (needs trained v2 model from US2) — T006, T007 can run in parallel; T008 depends on T007; T009 depends on T001 only
- **Phase 6 (Polish)**: Depends on all user stories complete

### User Story Dependencies

```
T001 (feature_extractors.py rewrite)
  ├── T002 → T003 (US1: aggregate data)
  │     └── T004 → T005 (US2: train model)
  │           ├── T006 (US3: update model paths)
  │           ├── T007 (US3: scaler loading in cache)
  │           │     └── T008 (US3: preprocessing service)
  │           └── T009 (US3: live test script — only needs T001 + v2 model files)
  └── T010 (Polish: consistency check)
```

### Parallel Opportunities

- T006 and T007 can run in parallel (different methods in services.py)
- T009 can start as soon as T001 is done (doesn't depend on T006-T008), but the v2 model files from T005 must exist for runtime testing

---

## Implementation Strategy

### Sequential Delivery (recommended for solo developer)

1. T001: Rewrite feature_extractors.py (foundation)
2. T002 → T003: Create and run aggregation script (US1)
3. T004 → T005: Modify and run training script (US2)
4. T006 + T007: Update inference service paths and caching (US3)
5. T008: Update preprocessing service (US3)
6. T009: Update live test script (US3)
7. T010: Final consistency verification

### MVP First

Complete T001 → T002 → T003 → T004 → T005 → T009 for the fastest path to a working live test. The Django inference service (T006-T008) can be updated afterward.

---

## Notes

- Stride changed from 100 to 30 per user request — this produces ~5.7× more training windows and makes live inference more responsive
- v1 model files are preserved on disk for reference; only the active path mappings change
- The `gravity_filter.py` module is NOT deleted — it's still needed for v1 model backward compatibility in the inference service
- All 3 consumers (training script, inference service, live test) import from the single `extract_window_features()` function — guaranteeing consistency (FR-010)
