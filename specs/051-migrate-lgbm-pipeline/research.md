# Phase 0 Research: Migrate LGBM Tremor Classification Pipeline

**Feature**: 051-migrate-lgbm-pipeline | **Date**: 2026-06-20

This document resolves all technical unknowns before code is generated. Per the user's
explicit instruction, the ESP32 firmware was read FIRST to establish the live sampling
rate as ground truth.

---

## 1. ESP32 sampling rate (ground truth from firmware) — RESOLVED

**Decision**: The live stream rate consumed by `test_AI_live.py` is the **MQTT-transmitted
rate ≈ 30 Hz**, NOT the 100 Hz the user suspected. Each 1-second window (~30 samples) is
up-sampled to the model's 66.67 Hz / 67-sample shape before filtering and feature extraction.

**Evidence** (read from firmware source):
- `firmware/include/config.h`:
  - `#define IMU_SAMPLE_RATE_HZ 100` and `IMU_SAMPLE_PERIOD_MS 10` → the IMU + Kalman filter run at **100 Hz internally**.
  - `#define MQTT_PUBLISH_RATE_HZ 33` with the comment *"IMU runs at 100 Hz; MQTT publishes at a lower rate … Default 33 Hz → 1 publish every ~30 ms"*.
- `firmware/src/task_scheduler.cpp`:
  - `SensorTask` runs at 100 Hz (`pdMS_TO_TICKS(IMU_SAMPLE_PERIOD_MS)` = 10 ms).
  - `MqttTask` publishes with `const TickType_t xPeriod = pdMS_TO_TICKS(33);` and the comment *"33ms period ≈ 30Hz publish rate"* → **actual transmitted rate ≈ 30.3 Hz**.
- `firmware/src/mqtt_publisher.cpp`: `publish_reading()` sends one JSON message per `MqttTask` tick → confirms one telemetry sample per ~33 ms.

**Rationale**: `test_AI_live.py` receives data over MQTT, so the rate that matters is the
*transmitted* rate (~30 Hz), not the internal IMU rate (100 Hz). The notebook model was
trained on data resampled to 66.67 Hz, so the live buffer must be resampled up from ~30 Hz
to 66.67 Hz to match the model's expected window shape and FFT frequency resolution.

**Implementation constants** (user-approved 2026-06-20):
- `LIVE_STREAM_RATE_HZ = 1000.0 / 33.0` (≈ **30.3 Hz** — the exact MqttTask 33 ms publish period; user chose exact over rounded 30.0).
- `MODEL_FS_HZ = 66.67`, `WINDOW_SECONDS = 1.0`, `MODEL_WINDOW_SAMPLES = round(66.67) = 67`.
- Live native window = `round(LIVE_STREAM_RATE_HZ * WINDOW_SECONDS) ≈ 30` samples → resampled to 67.

**Aliasing note**: Up-sampling 30 Hz → 66.67 Hz cannot create frequency content above the
original Nyquist (15 Hz). The clinically relevant Parkinsonian tremor band is ~3–12 Hz
(firmware PID comment cites "4–8 Hz oscillation"), which is well below 15 Hz, so the
tremor-discriminating features survive. The notebook's 0.5–20 Hz band-pass simply has an
empty 15–20 Hz region for live data — harmless. **The band-pass MUST be applied AFTER
resampling to 66.67 Hz** (Nyquist 33.3 Hz), never on the raw 30 Hz signal (where a 20 Hz
cutoff exceeds the 15 Hz Nyquist and is invalid).

**Alternatives considered**:
- *Assume 100 Hz (user's suspicion)*: rejected — contradicts the firmware; the model would
  receive a window ~3.3× too long in real time and FFT bins at the wrong frequencies.
- *Retrain the model at 30 Hz to avoid resampling*: rejected — spec SC-002 requires parity
  with the validated notebook result, which is fixed at 66.67 Hz.

> **Spec impact**: FR-011's "suspected ~100 Hz" is now CONFIRMED as ~30 Hz transmitted.
> The spec is updated to record the confirmed value. This is flagged to the user because it
> overturns the stated assumption.

---

## 2. Preprocessing & feature extraction (exact notebook parity) — RESOLVED

**Decision**: Reproduce the notebook's pipeline exactly in a shared module
`backend/ml_models/features_lgbm.py`, imported by both `train.py` and `test_AI_live.py`.

**Pipeline (from `LGBM.ipynb`)**:
1. **Column mapping**: raw CSV columns → `["T","AX","AY","AZ","GX","GY","GZ"]`; signal columns `["AX","AY","AZ","GX","GY","GZ"]`.
2. **Resample** to `FS = 66.67 Hz`: build time vector from `T` (ms → s), `np.arange(0, t[-1], 1/FS)`, linear `scipy.interpolate.interp1d` per axis (`fill_value="extrapolate"`).
3. **Band-pass** each axis: 4th-order Butterworth, `[0.5, 20] Hz`, zero-phase `filtfilt`.
4. **Window**: `WINDOW_SIZE = int(round(FS * 1.0)) = 67` samples, non-overlapping (`range(0, len-WINDOW+1, WINDOW)`).
5. **66 features per window** (11 per axis × 6 axes, axis-major), per `extract_features()`:
   `mean, std, median, q1 (25th pct), q3 (75th pct), min, max, peak1_freq, peak1_amp, peak2_freq, peak2_amp`.
   - Peaks via `fft_top2`: DC-removed (`x - mean(x)`), `rfft`, mask to `[0.5, 20] Hz`, take top-2 magnitude bins (freq + amplitude of each).
6. **Combine** the three groups, `replace([inf,-inf], nan).dropna()`.
7. **Columns**: 66 feature columns + `file_id` + `label`.

**Critical distinction**: This is the notebook's **66-feature** scheme. It is **different**
from the existing `backend/ml_data/utils/feature_extractors.py` (`extract_window_features`,
**42 features**, raw-signal, no band-pass). The migration introduces a NEW feature module;
it does not reuse the 42-feature one. The old extractor stays only as long as other
out-of-scope code needs it.

**Live-path feature parity**: `test_AI_live.py` applies steps 2–5 to each sliding buffer —
resample the ~30 Hz buffer to 67 samples at 66.67 Hz, band-pass, extract the same 66
features in the same order. The live resample uses `scipy.signal.resample` (fast, FFT-based,
vectorized) to a fixed 67-sample length, rather than `interp1d` on timestamps, because the
live buffer is a fixed-size rolling array.

**No scaler**: The notebook's LightGBM pipeline has `StandardScaler` commented out. Neither
training nor live evaluation applies a scaler. (The old RF v2 path used one; that logic is
removed during the consumer rewire.)

**Label scheme** (from notebook): `0 = Non-Tremor (Control)`, `1 = Tremor (Parkinson's)`,
`2 = Voluntary`.

**Rationale**: Spec FR-004 / SC-002 require feature parity with the research to preserve
validated performance.

---

## 3. Pinned hyperparameters (no run-time search) — RESOLVED

**Decision**: Run the notebook's `RandomizedSearchCV` **once during development** to discover
the best-performing LightGBM hyperparameters, then **hardcode** those exact values in
`train.py`. The production training run does NOT perform any search.

**Procedure**:
1. One-time (dev only): reproduce the notebook search — `imblearn.Pipeline([SMOTE, LGBMClassifier])`,
   `RandomizedSearchCV(n_iter=15, scoring='f1_macro', cv=GroupKFold(4) on file_id, random_state=42)`
   over grid `n_estimators∈{100,200,300}`, `learning_rate∈{0.01,0.05,0.1}`,
   `num_leaves∈{15,31,63}`, `max_depth∈{-1,5,10}`.
2. Capture `search.best_params_`, record them in `research.md` (this section) and in the
   model metadata JSON, and hardcode them into `train.py` as a literal dict.
3. Production `train.py` builds `Pipeline([SMOTE(random_state=42), LGBMClassifier(**PINNED_PARAMS, random_state=42, verbose=-1)])`
   and fits directly — no search.

**Discovered best params** (search run 2026-06-20, user-approved):
```json
{ "n_estimators": 300, "learning_rate": 0.05, "num_leaves": 63, "max_depth": -1 }
```
- Best CV `f1_macro` = **0.8788** (GroupKFold(4) on file_id, n_iter=15, random_state=42).
- Dataset assembled by the search: **10,655 windows × 66 features**, 117 files,
  classes {0: 3775, 1: 3688, 2: 3192}.
- Out-of-fold window-level: macro precision **0.8825**, recall 0.8764, f1 0.8783, accuracy 0.8756.
  Per class — Non-Tremor P0.84/R0.92, Tremor P0.85/R0.81, Voluntary P0.96/R0.90.
- These are PINNED into `backend/ml_models/train.py` as `PINNED_PARAMS`. Determinism via
  `random_state=42` everywhere. (Raw output: `specs/051-migrate-lgbm-pipeline/search_result.json`.)

**Validation parity**: Report the held-out `GroupKFold(4)` window-level and file-level
macro-precision/recall/F1 from the pinned model and compare to the notebook's numbers
(SC-002). Store window-level macro precision in metadata as the "Precision" reported by
`test_AI_live.py`.

**Rationale**: Spec FR-005 + clarifications — fast, reproducible, deterministic training.

**Alternatives considered**: LightGBM library defaults (rejected — may not match validated
result); keep search in production (rejected — slow, non-deterministic, explicitly forbidden).

---

## 4. Model artifact, metadata & serving format — RESOLVED

**Decision**: Save the fitted `imblearn.Pipeline` (SMOTE is fit-time only, pass-through at
predict) via `joblib` to `backend/ml_models/lgbm_tremor_model.pkl`, plus a sidecar
`backend/ml_models/lgbm_tremor_model.json` metadata file.

**Metadata schema** (drives both serving and `test_AI_live.py`):
```json
{
  "model_type": "lightgbm",
  "classes": {"0": "Non-Tremor", "1": "Tremor", "2": "Voluntary"},
  "n_features": 66,
  "feature_names": ["AX_mean", "AX_std", ...],
  "pipeline": {"fs_hz": 66.67, "window_samples": 67, "bandpass_hz": [0.5, 20.0], "scaler": null},
  "hyperparameters": { "...": "pinned best_params_" },
  "metrics": {"window_macro_precision": 0.0, "window_macro_recall": 0.0, "window_macro_f1": 0.0,
              "file_macro_precision": 0.0, "accuracy": 0.0},
  "trained_at": "<stamped at run time>"
}
```

**Rationale**: A `.pkl` keeps serving compatible with the existing `joblib.load` loader.
The metadata supplies the class map, feature order, pipeline constants, and the overall
**precision** that `test_AI_live.py` prints on every line (spec Precision-field assumption).

**Note on existing loader**: `inference/services.py` currently also requires a `*_model.json`
metadata file per model and (for v2) a scaler. The rewire removes the scaler requirement and
points the loader at the new metadata.

---

## 5. Live sliding-window architecture & latency — RESOLVED

**Decision**: `test_AI_live.py` uses `paho-mqtt` to subscribe to `tremo/sensors/+`, maintains
a `collections.deque(maxlen=N)` rolling buffer holding 1 second of samples at the native
~30 Hz rate, and emits a prediction every **100 ms** (≈ every 3rd message at 30 Hz), not on
every message and not once per full second.

**Per-tick pipeline (fully vectorized)**:
1. Snapshot deque → `np.ndarray (≈30, 6)`.
2. `scipy.signal.resample(buf, 67, axis=0)` → `(67, 6)` at 66.67 Hz.
3. Band-pass (`filtfilt`, vectorized across axes) → `(67, 6)`.
4. `extract_features_66(window)` → `(66,)` (NumPy reductions + `rfft`; no per-sample loops).
5. `model.predict_proba(x.reshape(1,-1))[0]` → 3 class probabilities.
6. Print one formatted line.

**Cadence mechanism**: throttle on wall-clock (`esp_timer`-style guard using a monotonic
counter of messages, or a 100 ms time gate) inside the MQTT `on_message` callback. Warm-up:
until the buffer holds a full second of samples, print a "warming up" notice instead of a
result line (edge case in spec).

**Latency budget**: The 66-feature extraction over a 67×6 window plus a single LightGBM
`predict_proba` is sub-millisecond on CPU; the 100 ms cadence is comfortably met. Keep all
array ops vectorized (FR-012).

**Output format** (exact, spec FR-013):
`Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %`
- `Sample`: incrementing prediction index.
- `Prediction`: class label string (Non-Tremor / Tremor / Voluntary).
- `Confidence`: max class probability (%).
- `Precision`: model's overall validated precision from metadata (constant per run).
- `Non-Tremor % / Tremor % / Voluntary %`: per-class probabilities (%).

**Rationale**: Spec FR-010/012/013 + clarifications.

---

## 6. Consumer rewiring surface — RESOLVED

**Decision**: Rewire exactly the consumers that load the to-be-removed `ml_models` RF/SVM
model; delete the superseded live script; leave the separate `realtime` path untouched
(documented).

**In scope (must change)**:
| File | Current behavior | Change |
|------|------------------|--------|
| `backend/tremoai_backend/settings.py` | `ML_MODELS_DIR = BASE_DIR/'ml_models'/'models'`; `DEFAULT_INFERENCE_MODEL='rf'` | Point `ML_MODELS_DIR` at `BASE_DIR/'ml_models'`; set default model id to the new model (e.g. `'lgbm'`). |
| `backend/inference/services.py` | `ModelLoader` maps `rf→rf_model_v3.pkl` etc. (in `models/`); v2 path extracts 42 feats + requires scaler; `predict()` returns binary + severity 0–3 | Map new id `lgbm → lgbm_tremor_model.pkl` + its `.json`; preprocessing uses the 66-feature pipeline (resample not needed for offline windows already at model rate — accept `(window,6)`), no scaler; `predict()` returns 3-class label + per-class probabilities. Remove RF/SVM/v1/v2/gravity/scaler branches that referenced removed artifacts. |
| `backend/inference/views.py` | `valid_models=['rf','svm','lstm','cnn_1d']`; response `prediction(bool)+severity(0-3)` | Accept the new model id; return 3-class prediction + probabilities (see contracts/inference-api.yaml). Keep auth + error format. |
| `backend/inference/serializers.py` | response fields | Adjust to 3-class output (prediction label + probabilities). |
| `backend/live_glove_test.py` | old RF v3 sliding-window MQTT script; loads `ml_models/models/rf_model_v3.pkl` + scaler; **hardcodes broker creds** | **DELETE** — superseded by `test_AI_live.py`. |

**Out of scope (documented, unchanged)**:
- `backend/realtime/ml_service.py`: loads `backend/models/tremor_classifier.pkl` (a *different*
  directory, file absent) with a *different* feature contract (aggregated `tremor_intensity`
  stats). It does not reference any removed `ml_models/` artifact, so per the spec's
  deletion-scope assumption it is left as-is. Unifying the WebSocket severity path onto the
  LGBM model is a recommended follow-up (would require feeding it raw 6-axis windows).
- `backend/apps/ml/`, `backend/apps/dl/`, `backend/dl_models/`, `backend/model_comparison/`:
  separate experiments outside `backend/ml_models/`; out of scope per spec.

**DL models**: `inference/services.py` also references `lstm`/`cnn_1d` in `DL_MODELS_DIR`
(unchanged dir). Those map entries may remain or be trimmed; trimming is optional and does
not affect the LGBM path. Default left explicit: keep them loadable, just no longer the default.

**Rationale**: Spec FR-008/FR-009 + the "clean inference pipeline" clarification, balanced
against the spec's deletion-scope assumption (only `backend/ml_models/` contents are deleted).

---

## 7. Files to delete in `backend/ml_models/` — RESOLVED

**Decision** (FR-007): delete everything superseded, keep only the new single pipeline.

- DELETE: `models/` (entire subdir: `rf_model_v1/v2/v3.pkl` + `.json` + scalers, `svm_model_v1.pkl` + `.json`, `comparison_report.txt`, `.gitkeep`), `scripts/` (`train_random_forest.py`, `train_svm.py`, `compare_models.py`, `utils/`), `backup/` (empty), `rf_model_metrics_v1.json`, `rf_model_metrics_v2.json`, `rf_model_metrics_v3.json`, `svm_model_metrics_v1.json`.
- KEEP: `__init__.py`, `README.md` (update content).
- ADD: `train.py`, `features_lgbm.py`, `lgbm_tremor_model.pkl`, `lgbm_tremor_model.json`.

**Rationale**: Spec FR-007 + SC-004 (single clearly-identifiable supported pipeline).

---

## 8. Dependencies — RESOLVED

**Decision**: Ensure `lightgbm`, `imbalanced-learn`, `scipy`, `paho-mqtt` are available in the
backend environment. `scikit-learn`, `numpy`, `pandas`, `joblib` already present.

- LightGBM, imbalanced-learn: NEW (flagged in Constitution Check / Complexity Tracking).
- scipy: already used by `ml_data/utils` (gravity filter) — present.
- paho-mqtt: already used by `live_glove_test.py` — present.

Add to `backend/requirements.txt` (or equivalent). One-time dev-only extras for the search
(`scikit-learn` already covers `RandomizedSearchCV`/`GroupKFold`).

**Rationale**: Spec constraints; minimize new surface.

---

## Open items carried to implementation

1. **Pinned hyperparameter values** (§3): produced by the one-time search at `/speckit.implement`
   time, then hardcoded + recorded in metadata. (Does not block `/speckit.tasks`.)
2. **Validated metric values** (§4): filled into metadata after the pinned model is trained;
   compared to notebook for SC-002.
