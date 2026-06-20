---
description: "Task list for 051-migrate-lgbm-pipeline"
---

# Tasks: Migrate LGBM Tremor Classification Pipeline to Backend

**Input**: Design documents from `/specs/051-migrate-lgbm-pipeline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: NOT requested in the spec — no test tasks are generated. Validation is via the
`quickstart.md` acceptance checks and the live output format.

**Organization**: Grouped by user story. US1 and US2 are both P1 (US1 is the natural MVP —
the persisted dataset — and is a hard prerequisite for US2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3
- All paths are absolute-from-repo-root and exact.

## Path Conventions

- ML pipeline: `backend/ml_models/`, `backend/ml_data/`
- Inference serving: `backend/inference/`
- Settings: `backend/tremoai_backend/settings.py`
- Live validator: `backend/test_AI_live.py`
- Firmware (read-only ground truth): `firmware/include/config.h`, `firmware/src/task_scheduler.cpp`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and artifact-tracking hygiene before any pipeline code.

- [x] T001 Ensure ML dependencies are declared in `backend/requirements.txt`: add `lightgbm`, `imbalanced-learn` (NEW); confirm `scipy`, `paho-mqtt`, `scikit-learn`, `numpy`, `pandas`, `joblib` present. Install into the backend environment.
- [x] T002 [P] Add `.gitignore` entries (repo root or `backend/.gitignore`) for the new artifacts: `backend/ml_models/lgbm_tremor_model.pkl` and `backend/ml_data/combined_processed_data.csv` (constitution: models excluded from git). Confirm `backend/ml_data/` exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared feature pipeline that BOTH training (US1/US2) and live evaluation (US3) import — guarantees identical 66-feature extraction.

**⚠️ CRITICAL**: No user story work can begin until this is complete.

- [x] T003 Create `backend/ml_models/features_lgbm.py` implementing exact `LGBM.ipynb` parity: constants `FS=66.67`, `WINDOW_SIZE=int(round(FS*1.0))=67`, `LOWCUT=0.5`, `HIGHCUT=20.0`, `SIGNAL_COLS=["AX","AY","AZ","GX","GY","GZ"]`; functions `bandpass(x)` (4th-order Butterworth `filtfilt`), `resample_df(df)` (timestamp-based `interp1d` to 66.67 Hz, for training), `resample_window(arr, n=67)` (vectorized `scipy.signal.resample`, for live), `fft_top2(x)` (DC-removed `rfft`, mask 0.5–20 Hz, top-2 freq+amp), `extract_features_66(window_2d)` → `(66,)` in the data-model.md order, and `get_feature_names_66()` → 66 names. No scaler.

**Checkpoint**: Feature module importable and produces a length-66 vector in the documented order.

---

## Phase 3: User Story 1 - Reproducible, audit-ready training dataset (Priority: P1) 🎯 MVP

**Goal**: Produce `backend/ml_data/combined_processed_data.csv` — labeled 66-feature windows from all three groups — written BEFORE any model training.

**Independent Test**: Run the data-prep portion of `train.py`; confirm the CSV exists with 66 feature columns + `file_id` + `label`, contains all three labels, and a re-run yields the same row count and class distribution. No model needed.

- [x] T004 [US1] In `backend/ml_models/train.py`, implement group loading: locate the three folders at repo root (`Clean Dataset – Control Group` → label 0, `Clean Dataset – Parkinson's Group` → label 1, `Clean Dataset – Voluntary Group` → label 2), iterate `.csv` files, map columns to `["T","AX","AY","AZ","GX","GY","GZ"]`, capture `file_id` = filename stem.
- [x] T005 [US1] In `backend/ml_models/train.py`, implement per-recording preprocessing using `features_lgbm`: `resample_df` → 66.67 Hz, `bandpass` each signal column, slice non-overlapping 67-sample windows, `extract_features_66` per window, attach `file_id` + `label`; accumulate rows into a DataFrame.
- [x] T006 [US1] In `backend/ml_models/train.py`, combine all groups, `replace([inf,-inf], nan).dropna().reset_index(drop=True)`, then **write `backend/ml_data/combined_processed_data.csv` BEFORE any training code runs** (columns: 66 features + `file_id` + `label`).
- [x] T007 [US1] In `backend/ml_models/train.py`, add edge-case handling + summary logging: skip empty/malformed/too-short recordings (log and continue), and print dataset shape, class distribution, and unique `file_id` count for determinism verification.

**Checkpoint**: `combined_processed_data.csv` is produced and inspectable independent of training (SC-001).

---

## Phase 4: User Story 2 - Single trusted classification model + live-path replacement (Priority: P1)

**Goal**: Train one pinned-config LightGBM model from the CSV, save it directly in `backend/ml_models/`, delete all superseded artifacts, and rewire the backend inference path to use it (3-class, no scaler).

**Independent Test**: After US1's CSV exists, run training; confirm exactly one model artifact + metadata in `backend/ml_models/`, the `models/` subdir and all rf/svm files are gone, and `POST /api/inference/?model=lgbm` returns a 3-class result with no scaler error.

- [x] T008 [US2] One-time hyperparameter discovery (dev only): run `RandomizedSearchCV` over the notebook grid (`n_estimators∈{100,200,300}`, `learning_rate∈{0.01,0.05,0.1}`, `num_leaves∈{15,31,63}`, `max_depth∈{-1,5,10}`) on `imblearn.Pipeline([SMOTE(random_state=42), LGBMClassifier(random_state=42, verbose=-1)])` with `GroupKFold(4)` on `file_id`, `scoring='f1_macro'`, `n_iter=15`, `random_state=42`. Record `best_params_` in `research.md` §3 and as a `PINNED_PARAMS` dict to hardcode. (Prerequisite for T009.)
- [x] T009 [US2] In `backend/ml_models/train.py`, AFTER the CSV is written, build `imblearn.Pipeline([SMOTE(random_state=42), LGBMClassifier(**PINNED_PARAMS, random_state=42, verbose=-1)])` (no search at run time), fit on the full feature matrix `X` / labels `y`, and save to `backend/ml_models/lgbm_tremor_model.pkl` via `joblib`.
- [x] T010 [US2] In `backend/ml_models/train.py`, compute `GroupKFold(4)` window-level and file-level macro precision/recall/F1 + accuracy, and write `backend/ml_models/lgbm_tremor_model.json` per `contracts/training-artifacts.md` (`model_type, classes, n_features=66, feature_names, pipeline{fs_hz,window_seconds,window_samples=67,bandpass_hz=[0.5,20],bandpass_order=4,scaler:null}, hyperparameters, smote, metrics, trained_at`). Verify metrics are consistent with the notebook (SC-002).
- [x] T011 [P] [US2] Delete superseded contents of `backend/ml_models/`: the entire `models/` subdirectory, `scripts/` (`train_random_forest.py`, `train_svm.py`, `compare_models.py`, `utils/`), `backup/`, and `rf_model_metrics_v1.json`, `rf_model_metrics_v2.json`, `rf_model_metrics_v3.json`, `svm_model_metrics_v1.json`. Keep `__init__.py` and `README.md`.
- [x] T012 [P] [US2] In `backend/tremoai_backend/settings.py`, change `ML_MODELS_DIR` to `BASE_DIR / 'ml_models'` (drop the `/ 'models'` segment) and set `DEFAULT_INFERENCE_MODEL` default to `'lgbm'`.
- [x] T013 [US2] In `backend/inference/services.py`, rewire `ModelLoader._get_model_path`/`_get_metadata_path` to map `lgbm → lgbm_tremor_model.pkl` / `lgbm_tremor_model.json`; rewrite `PreprocessingService` to extract the 66 features via `features_lgbm.extract_features_66` (accept a `(window,6)` window already at model rate) with NO scaler; rewrite `InferenceService.predict` to return 3-class output (`predict` index + `predict_proba` 3 probabilities). Remove rf/svm/v1/v2/gravity-filter/scaler branches that referenced removed artifacts.
- [x] T014 [US2] In `backend/inference/views.py`, update `valid_models` to include `'lgbm'` (and drop `'rf'`/`'svm'`), and build the 3-class response (`prediction` index, `predicted_class`, `probabilities{non_tremor,tremor,voluntary}`) per `contracts/inference-api.yaml`; preserve `IsDoctorOrAdmin` auth and the `{ "error": ... }` format.
- [x] T015 [P] [US2] In `backend/inference/serializers.py`, update the response serializer fields to the 3-class shape (prediction index, predicted_class, probabilities, optional confidence_score/model_version/inference_time_ms).
- [x] T016 [P] [US2] Delete `backend/live_glove_test.py` (superseded by `test_AI_live.py`; it loads removed `rf_model_v3.pkl`/scaler and hardcodes broker credentials).
- [x] T017 [P] [US2] Update `backend/ml_models/README.md` to document the single LGBM pipeline (train.py, features_lgbm.py, artifact names, 66 features, no scaler, 3 classes).

**Checkpoint**: One model + metadata in `backend/ml_models/`; legacy gone (SC-004); `/api/inference/?model=lgbm` returns 3-class output (SC-006).

---

## Phase 5: User Story 3 - Live validation against real sensor data (Priority: P2)

**Goal**: `backend/test_AI_live.py` streams from MQTT, resamples ~30 Hz → 66.67 Hz, extracts the same 66 features, and emits a prediction every ~100 ms in the exact 7-field format.

**Independent Test**: With the trained model present, run `test_AI_live.py` against the broker; after ~1 s warm-up, confirm one correctly formatted 7-field line every ~100 ms, and that malformed/missing data prints a notice rather than crashing.

- [x] T018 [US3] Create `backend/test_AI_live.py`: argparse for `--broker`/`--port`/`--topic` (default `tremo/sensors/+`) and broker credentials from CLI/env (NEVER hardcoded); set `LIVE_STREAM_RATE_HZ = 30.0` with an inline comment citing `firmware/include/config.h` `MQTT_PUBLISH_RATE_HZ`/`task_scheduler.cpp` MqttTask period as the confirmed ground truth; create a `paho-mqtt` VERSION2 client; load `lgbm_tremor_model.pkl` + `lgbm_tremor_model.json` (read class map + `metrics.window_macro_precision`).
- [x] T019 [US3] In `backend/test_AI_live.py`, implement the rolling buffer: `collections.deque(maxlen=round(LIVE_STREAM_RATE_HZ*1.0))` (~30); `on_message` parses the 6 axes in order `[aX,aY,aZ,gX,gY,gZ]` per `contracts/mqtt-sensor-payload.md`, appends to the buffer, and warns+continues on JSON/key errors; print a "warming up" notice until the buffer holds a full second.
- [x] T020 [US3] In `backend/test_AI_live.py`, implement the vectorized per-tick pipeline emitting every ~100 ms: snapshot buffer → `resample_window` to 67 samples @ 66.67 Hz → `bandpass` (AFTER resampling) → `extract_features_66` → `model.predict_proba(x.reshape(1,-1))[0]`; no Python per-sample loops (FR-012).
- [x] T021 [US3] In `backend/test_AI_live.py`, implement output per `contracts/live-output-format.md`: print the header once, then each line `Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %` (Prediction = argmax class label; Confidence = max prob %; Precision = constant from metadata; three per-class probabilities %); on a failed window print a "could not classify" notice instead of a partial line (US3.3).

**Checkpoint**: Live evaluation produces correctly formatted lines at ~100 ms cadence (SC-003, SC-005).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T022 [P] Run `quickstart.md` end-to-end and confirm every acceptance check passes (CSV-before-model, cleanup, 3-class API, live format, warm-up/malformed handling).
- [x] T023 [P] Document the out-of-scope follow-up in `backend/ml_models/README.md`: `backend/realtime/ml_service.py` still loads `backend/models/tremor_classifier.pkl` with a different feature contract and is intentionally untouched; note it as a future unification task.
- [x] T024 [P] Add a note recommending a constitution amendment to ratify LightGBM/imbalanced-learn and the `ml_models/` (root) model layout (per plan.md Complexity Tracking).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2 / T003)**: Depends on Setup. BLOCKS US1, US2, US3 (all import `features_lgbm`).
- **US1 (Phase 3)**: Depends on Foundational. Produces the CSV.
- **US2 (Phase 4)**: Depends on US1 (training needs the dataset/features). T008 → T009 → T010 sequential (same script, search before pin before train before metadata). T011/T012/T016/T017 are independent deletes/edits ([P]). T013 → T014 (services contract before view); T015 [P].
- **US3 (Phase 5)**: Depends on Foundational (features) + a trained model from US2 (T009/T010) to run end-to-end. Tasks T018→T019→T020→T021 are sequential (same file).
- **Polish (Phase 6)**: After the desired stories are complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational — the MVP.
- **US2 (P1)**: Requires US1's dataset. Delivers the model + live-path replacement.
- **US3 (P2)**: Requires the trained model (US2) to validate; the script itself can be written after Foundational, but its independent test needs the model.

### Parallel Opportunities

- T002 (Setup) runs alongside T001.
- Within US2: `T011`, `T012`, `T016`, `T017` can run in parallel; `T015` parallel with `T013`.
- Polish T022/T023/T024 are all [P].

---

## Parallel Example: User Story 2

```bash
# After T009/T010 produce the model + metadata, run these in parallel:
Task: "Delete superseded backend/ml_models/ contents (T011)"
Task: "Update ML_MODELS_DIR + DEFAULT_INFERENCE_MODEL in settings.py (T012)"
Task: "Delete backend/live_glove_test.py (T016)"
Task: "Update backend/ml_models/README.md (T017)"
Task: "Update inference/serializers.py response shape (T015)"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → 2. Phase 2 Foundational (T003) → 3. Phase 3 US1 → produce + validate the CSV. STOP and confirm SC-001.

### Incremental Delivery

1. Setup + Foundational → feature module ready.
2. US1 → CSV (MVP, SC-001).
3. US2 → trained model, legacy removed, inference rewired (SC-002, SC-004, SC-006).
4. US3 → live validation in the exact format (SC-003, SC-005).

---

## Notes

- One deferred value: the pinned hyperparameters (T008) are discovered once, then hardcoded in T009 — does not block any other task ordering.
- `train.py` spans US1 (data prep + CSV, T004–T007) and US2 (training + metadata, T009–T010); the CSV write (T006) MUST precede all training code.
- `features_lgbm.py` is the single source of truth for the 66-feature contract — both `train.py` and `test_AI_live.py` import it.
- No feature scaler anywhere (notebook parity).
- Keep MQTT broker credentials out of source (env/args) — the deleted `live_glove_test.py` violated this.
