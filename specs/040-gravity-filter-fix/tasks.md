# Tasks: Gravity Filter Fix for ML Pipeline

**Input**: Design documents from `/specs/040-gravity-filter-fix/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested in spec — test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No new project structure needed. This feature adds one new module and modifies existing files.

- [X] T001 Verify scipy>=1.10.0 is available by checking `backend/requirements.txt` — no changes expected (already present)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared gravity filter module that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create the gravity filter module at `backend/ml_data/utils/gravity_filter.py` with the following functions:
  - `design_gravity_filter(cutoff_hz=0.5, fs=37.0, order=2)` — uses `scipy.signal.butter(..., output='sos')` to return SOS coefficients
  - `apply_gravity_filter(signal: np.ndarray, sos: np.ndarray, accel_columns=[0,1,2])` — applies `scipy.signal.sosfilt` with `sosfilt_zi` steady-state initial conditions (scaled by first sample per axis) to accelerometer columns only, leaves gyroscope columns unchanged. Returns filtered signal (same shape as input).
  - `apply_gravity_filter_streaming(chunk: np.ndarray, sos: np.ndarray, zi: np.ndarray, accel_columns=[0,1,2])` — processes one sample or chunk for live use via `sosfilt` with `zi` parameter, returns `(filtered_chunk, updated_zi)`. Only filters accelerometer columns.
  - `get_filter_params_dict(cutoff_hz, fs, order, sos)` — returns a JSON-serializable dict with keys: `type`, `subtype`, `order`, `cutoff_hz`, `sampling_rate_hz`, `sos_coefficients` (nested list), `applied_to_axes`, `skipped_axes`, `initial_conditions`
  - `init_streaming_state(sos: np.ndarray, first_values: np.ndarray, accel_columns=[0,1,2])` — computes `sosfilt_zi(sos)` and scales by first sample values for each accelerometer axis, returns initial `zi` array

**Checkpoint**: Foundation ready — gravity filter module is importable and all functions are implemented.

---

## Phase 3: User Story 1 — Gravity-Removed Training Data Pipeline (Priority: P1) MVP

**Goal**: Apply gravity high-pass filter to accelerometer data in the PSMAD training pipeline so that output features are computed from tremor dynamics only, not gravity.

**Independent Test**: Run the updated `4_psmad_pipeline.py`. Verify that the output `ready_for_training_features.csv` has near-zero `mean_aX`, `mean_aY`, `mean_aZ` for motionless recordings. Verify `filter_params.json` is saved to `backend/ml_data/processed/`.

### Implementation for User Story 1

- [X] T003 [US1] Modify `backend/ml_data/scripts/4_psmad_pipeline.py` to import and apply the gravity filter:
  - Import `design_gravity_filter`, `apply_gravity_filter`, `get_filter_params_dict` from `backend.ml_data.utils.gravity_filter`
  - After data loading and column renaming (after the PSMAD→ESP32 column rename), and after computing sampling rate from the Timestamp column, call `design_gravity_filter(cutoff_hz=0.5, fs=computed_sampling_rate, order=2)` to get SOS coefficients
  - Apply `apply_gravity_filter(signal_array, sos, accel_columns=[0,1,2])` to the full continuous signal BEFORE windowing (the signal array should be the 6-column numpy array of [aX, aY, aZ, gX, gY, gZ])
  - After filtering, save filter params via `get_filter_params_dict(...)` to `backend/ml_data/processed/filter_params.json` using `json.dump`
  - The rest of the pipeline (windowing, feature extraction, FFT) proceeds unchanged on the now-filtered data

- [X] T004 [US1] Modify `backend/ml_data/scripts/1_preprocess.py` to apply the gravity filter before normalization:
  - Import `design_gravity_filter`, `apply_gravity_filter` from `backend.ml_data.utils.gravity_filter`
  - After loading raw data and before the `normalize_data()` call, design the filter with `cutoff_hz=0.5, fs=37.0, order=2` and apply to the full training and test signal arrays (accelerometer columns only)
  - This ensures DL model sequences (produced downstream by `3_sequence_preparation.py`) are also gravity-filtered
  - Load `filter_params.json` if it exists (from PSMAD pipeline) to use the same sampling rate, or default to 37.0 Hz

**Checkpoint**: User Story 1 complete — running `4_psmad_pipeline.py` produces gravity-filtered `ready_for_training_features.csv` and `filter_params.json`. Running `1_preprocess.py` produces gravity-filtered normalized arrays for DL sequence preparation.

---

## Phase 4: User Story 2 — Retrained Models with Gravity-Filtered Data (Priority: P2)

**Goal**: Retrain all ML and DL models on gravity-filtered data. Each model's metadata JSON must include the `filter_params` section so the inference service can reproduce the filter.

**Independent Test**: After retraining, inspect each model's metadata JSON for the `filter_params` key. Compare F1-scores with previous models. Verify that a static hand orientation test case predicts severity 0.

### Implementation for User Story 2

- [X] T005 [P] [US2] Modify `backend/ml_models/scripts/train_random_forest.py` to embed filter params in metadata:
  - After loading training data, load `backend/ml_data/processed/filter_params.json`
  - When building the metadata dict for saving, add a top-level `"filter_params"` key with the contents of filter_params.json
  - No changes to the model training logic itself — the training data is already gravity-filtered from US1

- [X] T006 [P] [US2] Modify `backend/ml_models/scripts/train_svm.py` to embed filter params in metadata:
  - Same approach as T005: load `filter_params.json` and add `"filter_params"` key to the saved metadata dict

- [X] T007 [P] [US2] Modify `backend/dl_models/scripts/train_lstm.py` to embed filter params in metadata:
  - Same approach as T005: load `filter_params.json` and add `"filter_params"` key to the saved metadata dict

- [X] T008 [P] [US2] Modify `backend/dl_models/scripts/train_cnn_1d.py` to embed filter params in metadata:
  - Same approach as T005: load `filter_params.json` and add `"filter_params"` key to the saved metadata dict

**Checkpoint**: User Story 2 complete — all four training scripts save `filter_params` in model metadata. Models are ready to be retrained on gravity-filtered data (actual retraining is a run-time step, not a code change).

---

## Phase 5: User Story 3 — Synchronized Live Inference Filter (Priority: P3)

**Goal**: The `PreprocessingService` in `backend/inference/services.py` applies the exact same gravity filter (from model metadata) to live sensor data before normalization and prediction.

**Independent Test**: Send a known sensor payload through the inference API. Verify accelerometer values are filtered (near-zero for static input). Compare preprocessed output with training pipeline output for identical input — must match within 1e-6.

### Implementation for User Story 3

- [X] T009 [US3] Modify `PreprocessingService` in `backend/inference/services.py` to apply the gravity filter before existing preprocessing:
  - Import `apply_gravity_filter` and `apply_gravity_filter_streaming` from `backend.ml_data.utils.gravity_filter` (use appropriate relative/absolute import for Django app context)
  - In the `preprocess()` method, before routing to `_preprocess_ml` or `_preprocess_dl`:
    1. Check if `metadata` contains a `"filter_params"` key
    2. If present, extract `sos_coefficients` from `metadata["filter_params"]` and convert to numpy array
    3. For ML models (`_preprocess_ml`): the input is a 1D array of 6 values — reshape to (1, 6), apply `apply_gravity_filter(data, sos, accel_columns=[0,1,2])`, reshape back. Note: for single-sample ML input, stateful filtering may not be meaningful; apply the filter with steady-state initial conditions per call.
    4. For DL models (`_preprocess_dl`): the input is a (128, 6) sequence — apply `apply_gravity_filter(data, sos, accel_columns=[0,1,2])` directly to the full sequence with `sosfilt_zi` initialization
  - If `"filter_params"` is not present in metadata (old model without filter), skip filtering and log a warning
  - The existing normalization/scaling in `_preprocess_ml` and `_preprocess_dl` proceeds after filtering, unchanged

- [X] T010 [US3] Update `ModelLoader` or `ModelCache` in `backend/inference/services.py` to pre-parse filter params at model load time:
  - When a model's metadata is loaded, if `"filter_params"` exists, pre-convert `sos_coefficients` from nested list to numpy array and store it in the cached metadata for efficiency
  - This avoids repeated list-to-numpy conversion on every inference call

**Checkpoint**: User Story 3 complete — live inference applies the same gravity filter as training. Static hand orientation produces severity 0 predictions.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and cleanup

- [X] T011 [P] Add a `__init__.py` to `backend/ml_data/utils/` if it doesn't already exist, ensuring the gravity_filter module is importable as `backend.ml_data.utils.gravity_filter`
- [X] T012 Validate end-to-end by reviewing that `filter_params` keys in `data-model.md` match the actual dict structure produced by `get_filter_params_dict()` in `gravity_filter.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: No dependencies — creates the shared module
- **User Story 1 (Phase 3)**: Depends on Phase 2 (needs gravity_filter module)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (needs filtered training data and filter_params.json)
- **User Story 3 (Phase 5)**: Depends on Phase 2 (needs gravity_filter module) and Phase 4 (needs models with filter_params in metadata)
- **Polish (Phase 6)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only — MVP delivers gravity-filtered training data
- **User Story 2 (P2)**: Depends on US1 (needs gravity-filtered features and filter_params.json)
- **User Story 3 (P3)**: Depends on US2 (needs models with filter_params in metadata to load at inference time)

**Note**: These stories are intentionally sequential (not parallel) because each builds on the output of the previous one. This is a pipeline fix, not independent features.

### Within Each User Story

- T003 before T004 (PSMAD pipeline first, establishes filter_params.json; preprocess uses same params)
- T005, T006, T007, T008 all parallel (different training scripts, different files)
- T009 before T010 (filter logic before optimization)

### Parallel Opportunities

```
Phase 2: T002 (single task, no parallelism)
Phase 3: T003 → T004 (sequential within US1)
Phase 4: T005 ║ T006 ║ T007 ║ T008 (all four training script modifications in parallel)
Phase 5: T009 → T010 (sequential within US3)
Phase 6: T011 ║ T012 (parallel cleanup tasks)
```

---

## Parallel Example: User Story 2

```bash
# Launch all training script modifications together:
Task T005: "Modify train_random_forest.py to embed filter_params"
Task T006: "Modify train_svm.py to embed filter_params"
Task T007: "Modify train_lstm.py to embed filter_params"
Task T008: "Modify train_cnn_1d.py to embed filter_params"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify scipy)
2. Complete Phase 2: Create `gravity_filter.py` module
3. Complete Phase 3: Apply filter in `4_psmad_pipeline.py` and `1_preprocess.py`
4. **STOP and VALIDATE**: Run pipeline, check that mean accelerometer features are near-zero for static recordings, verify `filter_params.json` exists
5. This alone proves the gravity removal works on training data

### Incremental Delivery

1. Setup + Foundational → gravity_filter.py module ready
2. Add User Story 1 → Gravity-filtered training data pipeline validated (MVP)
3. Add User Story 2 → Models retrained with filter_params in metadata
4. Add User Story 3 → Live inference applies matching filter → Full fix deployed
5. Polish → Cleanup and validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature is intentionally sequential (pipeline fix) — stories build on each other
- Actual model retraining (running the scripts) happens at run-time after code changes in US2
- No tests requested in spec — validation is manual via metrics comparison and signal inspection
- The `__init__.py` check in T011 is critical for Django imports to work correctly
