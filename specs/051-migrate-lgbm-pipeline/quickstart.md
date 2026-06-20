# Quickstart: LGBM Tremor Pipeline

**Feature**: 051-migrate-lgbm-pipeline

End-to-end: confirm sampling rate → train → validate → serve → live test. All commands run
from the repo root unless noted. Local development only.

## 0. Prerequisites

- Python env with: `lightgbm`, `imbalanced-learn`, `scikit-learn`, `scipy`, `numpy`, `pandas`,
  `joblib`, `paho-mqtt`.
- The three dataset folders present at repo root:
  - `Clean Dataset – Control Group/`
  - `Clean Dataset – Parkinson's Group/`
  - `Clean Dataset – Voluntary Group/`
- (Live test) Mosquitto broker reachable and an ESP32 publishing to `tremo/sensors/+`.
  Broker host/creds supplied via `.env` or CLI args (never hardcoded).

## 1. (Confirmed) Firmware sampling rate

Already verified in Phase 0: IMU = 100 Hz internal, **MQTT transmit ≈ 30 Hz** (the live rate).
Re-confirm if firmware changes:

- `firmware/include/config.h` → `IMU_SAMPLE_RATE_HZ`, `MQTT_PUBLISH_RATE_HZ`
- `firmware/src/task_scheduler.cpp` → `MqttTask` period

## 2. Train (writes CSV first, then the model)

```bash
python backend/ml_models/train.py
```

Produces, in order:
1. `backend/ml_data/combined_processed_data.csv`  ← written BEFORE training
2. `backend/ml_models/lgbm_tremor_model.pkl`
3. `backend/ml_models/lgbm_tremor_model.json`

Verify:
- The CSV exists and has 66 feature columns + `file_id` + `label`, with all three labels present.
- The metadata `metrics` are consistent with the notebook (no unexplained regression — SC-002).

> Hyperparameters are pinned (no search at run time). The values were discovered once with
> the notebook's `RandomizedSearchCV` and hardcoded in `train.py` (research.md §3).

## 3. Confirm cleanup (SC-004)

```bash
ls backend/ml_models/
```

Expect ONLY: `__init__.py`, `README.md`, `train.py`, `features_lgbm.py`,
`lgbm_tremor_model.pkl`, `lgbm_tremor_model.json`.
The `models/`, `scripts/`, `backup/` subdirs and all `rf_*`/`svm_*` files MUST be gone.
`backend/live_glove_test.py` MUST be gone.

## 4. Serve via the REST inference endpoint

Start backend, then POST one analysis window (66.67 Hz, ~67 samples, 6 axes):

```bash
python backend/manage.py runserver
# POST /api/inference/?model=lgbm  (JWT required)
# body: { "sensor_data": [[aX,aY,aZ,gX,gY,gZ], ... 67 rows ...] }
```

Expect a 3-class response (see `contracts/inference-api.yaml`): `prediction` 0/1/2,
`predicted_class`, and per-class `probabilities`.

## 5. Live test against the glove

```bash
python backend/test_AI_live.py --broker <host> --port 1883 --topic "tremo/sensors/+"
```

Expect, after ~1 s warm-up, one line every ~100 ms:

```
Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %
1, Tremor, 92.4, 88.1, 4.2, 92.4, 3.4
...
```

## Acceptance checks (map to spec)

| Check | Spec |
|-------|------|
| CSV exists before model, all 3 labels, deterministic re-run | US1, SC-001 |
| Single model artifact; `models/` subdir gone; no rf/svm leftovers | US2, SC-004 |
| Metadata metrics ≈ notebook results | SC-002 |
| `/api/inference/` returns 3-class output; no scaler errors | FR-008/009, SC-006 |
| Live lines have all 7 fields in order, every ~100 ms | US3, SC-003, SC-005 |
| Malformed MQTT / warm-up handled without crash or partial line | US3.3, edge cases |
