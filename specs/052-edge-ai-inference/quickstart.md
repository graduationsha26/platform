# Quickstart: On-Device Edge AI Tremor Classification

End-to-end path from retrained model to a smoothly-gated, on-device classifier, with the
parity gates that must be green before firmware integration. Run from the repository root.

## Prerequisites

- Feature 051 environment (Python 3.14, `lightgbm`, `imbalanced-learn`, `scikit-learn`,
  `scipy`, `numpy`, `pandas`, `joblib`).
- The three dataset folders at repo root (Control / Parkinson's / Voluntary).
- PlatformIO CLE/IDE for the firmware build; an ESP32dev board for on-device steps.

## Step 1 — Retrain at native 100 Hz (gated on approval)

```bash
python backend/ml_models/train.py        # now FS=100Hz, WINDOW=128, causal band-pass
```
Produces `backend/ml_data/combined_processed_data.csv`, `lgbm_tremor_model.pkl`, `.json`.
**Gate**: the retrained model's CV macro precision must stay comparable to the 66.67 Hz
reference (~0.88). If it drops materially, switch the reference filter back to `filtfilt`
(fallback) and re-evaluate before continuing.

## Step 2 — Export the model to C

```bash
python backend/ml_models/export_to_c.py
# writes firmware/src/tremor_model.cpp + firmware/include/tremor_model.h
```
Re-running on the same `.pkl` must produce byte-identical output (SC-008).

## Step 3 — Host parity harness (MUST be green before firmware integration)

```bash
pytest backend/tests/test_edge_parity.py -v
```
Validates, on held-out windows:
- **Feature parity (SC-006)**: each of the 66 C-computed features matches the Python
  reference within the defined tolerance.
- **Prediction parity (SC-005)**: C interpreter `argmax` matches the Python model on
  ≥95% of windows; raw per-class scores match within tolerance.
- **Mapping (SC-001)**: a known tremor window → class 1; a known resting window → class 0.

> The harness compiles the generated `tremor_model.cpp` + `edge_features.cpp` on the host
> (native PlatformIO env or a small C harness) and feeds the same windows the Python path uses.

## Step 4 — Build & flash firmware

```bash
pio run -e esp32dev                       # confirm flash/RAM within headroom (SC-007)
pio run -e esp32dev -t upload
pio device monitor
```
Check the build report: flash and RAM stay within the defined headroom budget.

## Step 5 — On-device validation

1. **Warm-up (FR-011)**: on boot, before 128 samples are buffered, the device reports
   "not ready" / withholds a class — it does not emit a garbage decision.
2. **Real-time cadence (SC-002)**: with the device worn, the monitor shows a refreshed
   decision at ≥10 Hz (≤100 ms apart).
3. **Offline (SC-004)**: disconnect WiFi/broker; tremor-like motion still produces a
   "Tremor" decision and engages suppression — no backend needed.
4. **Labeling (SC-001)**: induce tremor-like motion → class 1 + suppression engages;
   hold still → class 0 + suppression disengages; move intentionally → class 2 +
   suppression stays disengaged (device stops fighting voluntary motion).
5. **Gate smoothness (SC-009)**: at a class boundary (motion that flickers between classes),
   observe the actuators do NOT toggle every cycle — the gate requires a sustained class
   change (vote/hysteresis) before engaging/disengaging.
6. **Control deadline (SC-003/SC-007)**: confirm the existing sensor→actuation latency
   warning (<70 ms) does not fire while ClassificationTask runs on Core 0.

## Step 6 — Backend record path unchanged (FR-012)

Confirm the backend `inference` path still classifies streamed telemetry and persists
records (it remains authoritative). The device class is supplementary (local suppression).

## Rollback

The suppression gate can be disabled (config flag) to revert to the previous unconditional
always-on suppression without removing the classifier, de-risking on-device bring-up.
