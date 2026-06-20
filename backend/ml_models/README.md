# ML Model Pipeline — LightGBM Tremor Classifier (Feature 051)

Single, supported machine-learning pipeline for the TremoAI platform. It trains one
**3-class LightGBM** model that distinguishes **Non-Tremor (0)**, **Tremor (1)**, and
**Voluntary movement (2)** from glove IMU data.

> Feature 051 replaced the previous Random Forest / SVM experiments. The old
> `models/`, `scripts/`, and `backup/` subdirectories and all `rf_*`/`svm_*` artifacts were
> removed in favor of this single pipeline.

## Directory contents

```
backend/ml_models/
├── train.py                  # Data prep + CSV export + train + metadata (one reproducible run)
├── features_lgbm.py          # Shared 66-feature pipeline (training + inference + live)
├── lgbm_tremor_model.pkl     # Trained imblearn Pipeline(SMOTE + LightGBM)
├── lgbm_tremor_model.json    # Metadata: classes, feature names, pipeline consts, metrics
├── __init__.py
└── README.md                 # This file
```

## Pipeline

`resample → 100 Hz  →  0.5–20 Hz band-pass (4th-order Butterworth, causal SOS)  →  1.28-second
windows (128 samples)  →  66 features (11 per axis × 6 axes)`  →  SMOTE + LightGBM (no scaler).

> **Feature 052 (Edge AI)** realigned the pipeline to the device's native **100 Hz** with
> **128-sample** windows and a **causal** band-pass so the model can be transpiled to the ESP32.
> Accuracy is unchanged (macro precision ≈ 0.88). See `## Feature 052 — On-Device Edge AI` below.

- **Feature order** (axis-major, per axis): `mean, std, median, q1, q3, min, max,
  peak1_freq, peak1_amp, peak2_freq, peak2_amp`. Axes: `AX, AY, AZ, GX, GY, GZ`.
- **Hyperparameters are PINNED** (no run-time search): `{n_estimators: 300, learning_rate:
  0.05, num_leaves: 63, max_depth: -1}`, discovered once via `RandomizedSearchCV`
  (GroupKFold(4) on `file_id`, `f1_macro`, `random_state=42`).
- **Validated performance** (out-of-fold, GroupKFold=4): macro precision ≈ **0.88**,
  accuracy ≈ **0.88**.

## Quick start

```bash
# From repository root. Requires the three dataset folders at repo root:
#   Clean Dataset – Control Group / Parkinson's Group / Voluntary Group
python backend/ml_models/train.py
```

Produces, in order:
1. `backend/ml_data/combined_processed_data.csv`  (written BEFORE training; 66 features + file_id + label)
2. `backend/ml_models/lgbm_tremor_model.pkl`
3. `backend/ml_models/lgbm_tremor_model.json`

## Serving & live test

- **REST**: `POST /api/inference/?model=lgbm` (JWT) — see
  `specs/051-migrate-lgbm-pipeline/contracts/inference-api.yaml`. Send a `(window, 6)` window;
  returns class index + `predicted_class` + per-class `probabilities`.
- **Live**: `python backend/test_AI_live.py --broker <host>` — subscribes to MQTT
  (`tremo/sensors/+`), resamples the ~30.3 Hz stream up to 66.67 Hz, and prints
  `Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %` every ~100 ms.

## Reproducibility

`random_state=42` throughout (SMOTE + LightGBM). Same raw inputs → same dataset and model.

## Dependencies

`lightgbm`, `imbalanced-learn`, `scikit-learn`, `scipy`, `numpy`, `pandas`, `joblib`
(declared in `backend/requirements.txt`).

## Feature 052 — On-Device Edge AI

The trained model is **transpiled to C++** and runs **on the ESP32 glove firmware** for
real-time, network-independent tremor suppression. The backend remains authoritative for stored
records.

- **`export_to_c.py`** — `python backend/ml_models/export_to_c.py` reads `lgbm_tremor_model.pkl`
  and generates `firmware/include/tremor_model.h` + `firmware/src/tremor_model.cpp` (flat-array
  tree interpreter data + the matching band-pass SOS). Re-run after every retrain. The generated
  files are deterministic (byte-identical) and must not be hand-edited.
- **Parity gate** — `pytest backend/tests/test_edge_parity.py`. Layer A (model parity, no
  compiler) proves the flat-array interpreter reproduces the Python model (validated: **100%**
  decision agreement). Layer B (C DSP feature parity, SC-006) needs a host C++ compiler
  (g++/clang/MSVC or PlatformIO `native`) — it builds `parity_shim.cpp` and is skipped otherwise.
- **`monitor_edge_live.py`** — `python backend/monitor_edge_live.py --broker <host>` subscribes to
  MQTT and prints the **ESP32's own** decisions in the 7-field format
  (`Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %`). It does no
  inference itself (unlike `test_AI_live.py`).
- **Firmware** — `firmware/src/edge_features.cpp` (portable DSP, parity-exact), `classifier.cpp`
  (interpreter), `suppression_gate.cpp` (smoothed Tremor gate), and a Core-0 `ClassificationTask`
  in `task_scheduler.cpp`. Builds at Flash 75.7% / RAM 15.7% (partition `partitions_edge.csv`).
- **Backup** — the prior 66.67 Hz model is preserved in `backend/ml_models/backup_66hz_model/`.

## Notes / follow-ups

- The live `Precision` value is the model's overall validated window-level macro precision
  (constant per run), read from the metadata — not a per-sample value.
- **Out of scope (follow-up)**: `backend/realtime/ml_service.py` still loads
  `backend/models/tremor_classifier.pkl` with a different (aggregated `tremor_intensity`)
  feature contract and was intentionally left untouched by this migration. Unifying the
  WebSocket severity path onto this LightGBM model (feeding it raw 6-axis windows) is a
  recommended future task.
- **Constitution note**: this feature adds LightGBM + imbalanced-learn (outside the original
  scikit-learn/TF stack) and stores the model directly in `backend/ml_models/` (the
  constitution references `ml_models/models/`). Both were explicit project decisions for
  Feature 051; consider ratifying them via a constitution amendment.
```
