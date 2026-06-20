# Implementation Plan: Migrate LGBM Tremor Classification Pipeline to Backend

**Branch**: `051-migrate-lgbm-pipeline` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/051-migrate-lgbm-pipeline/spec.md`

## Summary

Migrate the validated 3-class LightGBM tremor-classification pipeline from `LGBM.ipynb` into the Django backend as a reproducible, file-based ML pipeline, then rewire the backend's live inference path to use it.

The work has four parts:

1. **Data prep + training** (`backend/ml_models/train.py`): load the three labeled recording groups, resample each recording to 66.67 Hz, band-pass filter (0.5–20 Hz), window into 1-second non-overlapping windows (67 samples), extract the notebook's 66 features (11 per axis × 6 axes), combine + label, **persist `backend/ml_data/combined_processed_data.csv` BEFORE training**, then train a single SMOTE+LightGBM model with **pinned hyperparameters** (discovered by running the notebook's `RandomizedSearchCV` once during development, then hardcoded) and save `backend/ml_models/lgbm_tremor_model.pkl` plus a metadata JSON.
2. **Cleanup** (`backend/ml_models/`): delete the `models/` subdirectory and all superseded RF/SVM artifacts, scripts, and metrics, leaving a single supported pipeline.
3. **Consumer rewire**: update `backend/inference/services.py`, `backend/inference/views.py`, `backend/tremoai_backend/settings.py`, and delete the superseded `backend/live_glove_test.py` so the live inference path loads the new model, uses the 66-feature pipeline, and returns the 3-class output (no scaler).
4. **Live validation** (`backend/test_AI_live.py`): subscribe to the ESP32 MQTT stream, maintain a 1-second sliding buffer, resample each window to the model's 66.67 Hz shape, extract the same 66 features, and emit a prediction every 100 ms in the exact format `Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %`.

**Key firmware finding (resolves FR-011)**: The ESP32 IMU samples internally at 100 Hz, but the **MQTT-transmitted rate — what the live test actually receives — is ~30 Hz** (`MQTT_PUBLISH_RATE_HZ = 33` in `firmware/include/config.h`, throttled to a 33 ms publish period ≈ 30.3 Hz in `firmware/src/task_scheduler.cpp`). The live stream rate is therefore set to the transmitted rate (~30 Hz), and each 1-second window (~30 samples) is **up-sampled to 66.67 Hz (~67 samples)** before filtering and feature extraction. See [research.md](./research.md) §1.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels (inference path only; training is an offline script)
**Language/Runtime**: Python 3.x
**ML Libraries**: LightGBM (`lightgbm.LGBMClassifier`), imbalanced-learn (`SMOTE`, `imblearn.pipeline.Pipeline`), scikit-learn (CV/metrics, one-time search), SciPy (`butter`/`filtfilt`/`resample`, `interp1d`), NumPy, pandas, joblib — **NEW: LightGBM + imbalanced-learn** (see Constitution Check)
**Database**: Supabase PostgreSQL (remote) — unchanged; this feature adds no DB models/migrations. Training data is a file artifact (CSV), not DB-stored.
**Authentication**: JWT (SimpleJWT), roles doctor/admin — unchanged; inference endpoint keeps `IsDoctorOrAdmin`
**Testing**: pytest (backend) — optional, only if requested
**Project Type**: monorepo (backend/, frontend/, firmware/)
**Real-time / Integration**: MQTT inbound from ESP32 (`paho-mqtt`), topic `tremo/sensors/+`, JSON payload `{device_id, timestamp, aX, aY, aZ, gX, gY, gZ, battery_level}`; accel in m/s², gyro in °/s
**Performance Goals**: Live evaluation emits a prediction every ~100 ms; per-prediction pipeline (resample → filter → 66-feature extraction → classify) MUST complete within that 100 ms step. Output drives real-time hardware stabilization → fully vectorized, no Python per-sample loops.
**Constraints**: Local development only. Pinned hyperparameters (no run-time search). No feature scaler (notebook's LightGBM uses none). Combined CSV written before any model training.
**Scale/Scope**: 3 recording groups (Control/Parkinson's/Voluntary), hundreds of CSV recordings, ~thousands of 1-second windows; single model artifact; one live stream at a time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All work in `backend/` and reads from `firmware/`; fits structure.
- [ ] **Tech Stack Immutability**: ⚠️ Adds **LightGBM** and **imbalanced-learn (SMOTE)** — not in the constitutional ML stack (scikit-learn / TensorFlow-Keras). See Complexity Tracking.
- [x] **Database Strategy**: Supabase PostgreSQL only; no new DB systems. Training CSV is an offline file artifact (no local DB introduced).
- [x] **Authentication**: Inference endpoint retains JWT + `IsDoctorOrAdmin`.
- [x] **Security-First**: MQTT broker creds via `.env` (firmware/backend already do this); no new hardcoded secrets. The existing `live_glove_test.py` hardcodes creds and is being **deleted**; `test_AI_live.py` MUST read broker creds from env/args.
- [x] **Real-time Requirements**: Existing Channels WebSocket path unchanged.
- [x] **MQTT Integration**: `test_AI_live.py` consumes the existing bidirectional MQTT telemetry topic — consistent.
- [ ] **AI Model Serving**: ⚠️ Constitution says classical models live in `backend/ml_models/models/` and inference is routed **exclusively** through `backend/inference/`. This feature (per explicit user directive) stores the model **directly in `backend/ml_models/`** and **deletes the `models/` subdirectory**, and adds a standalone MQTT validation script (`test_AI_live.py`) outside the REST inference app. See Complexity Tracking.
- [x] **API Standards**: Inference endpoint stays REST+JSON, snake_case, standard codes, `{ "error": "message" }`.
- [x] **Development Scope**: Local only; no Docker/CI/CD.

**Result**: ⚠️ VIOLATIONS REQUIRE JUSTIFICATION (see Complexity Tracking) — all are direct consequences of explicit user directives in the spec/clarifications; none introduce production/deployment complexity.

## Project Structure

### Documentation (this feature)

```text
specs/051-migrate-lgbm-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── inference-api.yaml          # Updated /api/inference/ contract (3-class)
│   ├── live-output-format.md       # test_AI_live.py 7-field line contract
│   ├── mqtt-sensor-payload.md      # Inbound ESP32 telemetry contract
│   └── training-artifacts.md       # CSV schema + model + metadata contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
backend/
├── ml_models/
│   ├── __init__.py                  # KEEP
│   ├── README.md                    # UPDATE (describe new single pipeline)
│   ├── train.py                     # NEW — data prep + CSV export + train + save
│   ├── features_lgbm.py             # NEW — shared 66-feature extractor (train + live)
│   ├── lgbm_tremor_model.pkl        # NEW — single model artifact (.gitignored)
│   ├── lgbm_tremor_model.json       # NEW — metadata (params, classes, precision, feature names)
│   ├── models/                      # DELETE entire subdir (rf_model_v1/v2/v3, svm_model_v1, scalers, jsons)
│   ├── scripts/                     # DELETE (train_random_forest.py, train_svm.py, compare_models.py, utils/)
│   ├── backup/                      # DELETE (empty)
│   ├── rf_model_metrics_v1/v2/v3.json   # DELETE
│   └── svm_model_metrics_v1.json    # DELETE
├── ml_data/
│   └── combined_processed_data.csv  # NEW — written BEFORE training (66 features + file_id + label)
├── inference/
│   ├── services.py                  # REWIRE — load lgbm_tremor_model.pkl, 66-feat, 3-class, no scaler
│   ├── views.py                     # REWIRE — valid model name(s), 3-class response
│   └── serializers.py               # REVIEW — response fields for 3-class output
├── tremoai_backend/
│   └── settings.py                  # UPDATE — ML_MODELS_DIR, DEFAULT_INFERENCE_MODEL
├── test_AI_live.py                  # NEW — live MQTT sliding-window evaluation (canonical)
└── live_glove_test.py               # DELETE — superseded by test_AI_live.py

firmware/                            # READ ONLY (sampling-rate ground truth) — no changes
├── include/config.h                 # IMU 100 Hz; MQTT publish 33 → ~30 Hz transmitted
└── src/task_scheduler.cpp           # MqttTask 33 ms period ≈ 30 Hz
```

**Structure Decision**: Backend-only change plus a read of `firmware/` for the sampling-rate ground truth. The training pipeline and the live validator share one feature module (`backend/ml_models/features_lgbm.py`) to guarantee identical 66-feature extraction across training, the Django inference service, and `test_AI_live.py`. No frontend or firmware changes.

### Out-of-scope consumers (documented, not modified)

- `backend/realtime/ml_service.py` loads from a **different** directory (`backend/models/tremor_classifier.pkl`, which is absent) using a **different** feature contract (aggregated `tremor_intensity` stats, not raw 6-axis windows). It does not reference any `ml_models/` artifact being removed, so it is left untouched by this migration. Unifying it is a follow-up. See research.md §6.
- `backend/apps/ml/`, `backend/apps/dl/`, `backend/dl_models/`, `backend/model_comparison/` are separate experiments outside `backend/ml_models/`; per the spec's deletion-scope assumption they are out of scope.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Add **LightGBM** + **imbalanced-learn (SMOTE)** (outside constitutional scikit-learn/TF stack) | The entire feature is the migration of the validated *LightGBM* research pipeline; SMOTE is part of that validated pipeline's class-imbalance handling. Model is still serialized as `.pkl` via joblib (serving-compatible with the existing `.pkl` loader). | Re-implementing as a scikit-learn `GradientBoostingClassifier` would diverge from the validated research results (spec SC-002 requires parity) — defeats the migration's purpose. Recommend a constitution amendment to add LightGBM to the approved ML libraries. |
| Store model **directly in `backend/ml_models/`** and **delete `backend/ml_models/models/`** (constitution specifies `ml_models/models/`) | Explicit user directive (clarifications 2026-06-20): single descriptively-named artifact directly in `ml_models/`, old `models/` subdir deleted for a clean single-pipeline layout. | Keeping `models/` retains the legacy nesting the user explicitly asked to remove. `ML_MODELS_DIR` setting is updated accordingly so serving still resolves the path. |
| Standalone MQTT validator `backend/test_AI_live.py` outside the `inference` REST app | Explicit user directive; matches the existing `live_glove_test.py` precedent; it is a developer validation tool driving hardware-stabilization checks, not a production API surface. | Routing live validation through the REST endpoint adds auth/HTTP overhead incompatible with the 100 ms vectorized low-latency requirement (FR-012). The production REST inference path (`inference/`) is still rewired to the new model separately. |

> All three deviations stem from explicit, recorded user decisions and stay within local-development scope. No production/CI/CD/Docker complexity is introduced. Recommend ratifying the LightGBM addition and the `ml_models/` layout in a future constitution amendment.
