# Implementation Plan: Hardware-First Stabilization & Binary Tremor Pivot

**Branch**: `053-hardware-first-stabilization` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/053-hardware-first-stabilization/spec.md`

## Summary

Restructure tremor suppression in a strict **Hardware First** order, across four sequenced phases:

1. **Hardware (US1)** — liberate the CMG: set the gimbal half-swing to its true full-range value (`SPAN = 900`, center 1500, clamps 600–2400), **raise** the flywheel run pulse to restore reaction-torque authority (it currently idles 80 µs above arm), and un-squash the PID→CMG path (lower torque full-scale, raise slew) so the PID can command snappy, full-range motion. Pure `config.h` + `cmg.cpp`/`pid_controller.cpp` work; no ML involved.
2. **Binary pivot + parity (US2)** — collapse the classifier from 3-class (Non-Tremor/Tremor/Voluntary) to **binary** (Non-Tremor=0 / Tremor=1) end-to-end: training, metadata, C export, on-device interpreter, backend inference, telemetry. The binary LightGBM head changes the inference math from **3-class softmax round-robin** to a **single raw score → sigmoid**. The "predicts Tremor when still" symptom is fixed by a **data-driven Python↔C++ parity debug** against the recorded still-glove capture (and a shaking counterpart), localizing the real axis/sign/scale/feature-order mismatch — not by relabeling (labels were already correct).
3. **Proportional engagement (US3)** — drive the existing smoothed `gate_authority()` target from the Tremor probability (continuous) with a low-confidence floor + the existing dwell/ramp anti-chatter, replacing the binary vote→on/off target.
4. **Unified retrain (US4)** — one `train.py` run → one `lgbm_tremor_model.pkl` → `export_to_c.py` → byte-identical firmware arrays, shared by backend and ESP32.

The feature is firmware- and ML-centric; the backend `inference` path and any telemetry consumers are updated only to track the 2-class shape. No new endpoints, no new frameworks.

## Technical Context

**Backend Stack**: Django 5.x + DRF + Channels (unchanged; only `inference` service/serializer touched for 2-class output)
**Frontend Stack**: React 18+ + Vite + Tailwind + Recharts (touched only if a component renders the now-removed `voluntary` probability)
**Database**: Supabase PostgreSQL (remote) — no schema change required by this feature
**Authentication**: JWT (SimpleJWT), doctor/admin — unchanged
**Testing**: pytest (backend + parity harness), PlatformIO `native`/g++/clang/MSVC for Layer-B C parity, on-bench manual validation for hardware
**Project Type**: monorepo (firmware/ + backend/ primary; frontend/ marginal)
**Real-time**: Django Channels WebSocket (unchanged); on-device closed-loop control at 200 Hz
**Integration**: Bidirectional MQTT — telemetry payload `pred_proba` drops to 2 entries
**AI/ML**: LightGBM `.pkl` in `backend/ml_models/`, transpiled to C for ESP32 (binary objective). Shared 66-feature pipeline `features_lgbm.py` ↔ `edge_features.cpp`.
**Performance Goals**: sensor-to-actuation latency < 70 ms (preserved); classification cadence ~10 Hz (unchanged); Python↔C decision agreement ≥ 99% with `max|Δproba| < 1e-3`; deterministic (byte-identical) C export.
**Constraints**: local development only; US1 + Layer-B parity require physical bench (CMG) and a host C++ compiler; flywheel/slew magnitudes are bench-tuned within brownout-safe limits.
**Scale/Scope**: single glove on the bench; high-frequency IMU telemetry; ~14 backend/firmware files in the binary-pivot blast radius (enumerated in Structure Decision).

### Key technical realities discovered (drive the design)

- **Binary LightGBM ≠ 3-class.** A binary objective emits **one** tree series (≈300 trees, not 900) with `num_class == 1` in `dump_model()`; the probability is `sigmoid(raw)` (with the model's base/init score), not a 3-way softmax. `export_to_c.py` hard-asserts `num_class == 3` and `classifier.cpp` does 3-class softmax+argmax — both must change. The `init_score` baking (LightGBM `boost_from_average`) must be handled for exact parity.
- **The still capture is ~33 Hz, not 100 Hz.** `stable_glove_data_20260620_215329.csv` timestamps step ~30–37 ms → it is the **MQTT telemetry stream (33 Hz)**, while the on-device classifier consumes the internal **100 Hz** stream (`EDGE_FS_HZ = 100`, no on-device resampling). Faithful parity needs a 100 Hz capture (or principled resampling); for the *still* case it is still valid for axis/sign/scale checks. A 100 Hz raw capture path is a dependency for full fidelity.
- **Unit scale is the #1 parity suspect.** The capture has accel in **m/s²** (aZ ≈ 9.8 at rest). Amplitude features (std, min/max, FFT peak amplitudes) are computed on the band-passed window; a g-vs-m/s² mismatch (×9.8) between the training data and the device stream would scale every amplitude feature and plausibly invert classification. The parity debug must verify units explicitly.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes land in `firmware/` and `backend/` (+ minor `frontend/`); no new repos.
- [x] **Tech Stack Immutability**: No new frameworks. LightGBM remains a permitted boosting `.pkl`. C export tooling already permitted (Feature 052 amendment).
- [x] **Database Strategy**: No DB system change; no new local DB.
- [x] **Authentication**: Unchanged (JWT/SimpleJWT, doctor/admin).
- [x] **Security-First**: No new secrets; existing `config.h`/`.env` patterns preserved.
- [x] **Real-time Requirements**: Channels WebSocket unchanged; control loop timing preserved.
- [x] **MQTT Integration**: Bidirectional MQTT retained; payload narrows to 2-class prediction.
- [x] **AI Model Serving**: Backend `inference` remains authoritative; on-device model is reproducibly transpiled from the backend `.pkl` with identical features/class mapping — squarely within the **On-Device (Edge) Inference Exception** (constitution v1.2.0).
- [x] **API Standards**: REST + JSON + snake_case unchanged; only the prediction object loses the `voluntary` key.
- [x] **Development Scope**: Local only — bench + `runserver`/`npm run dev`; no Docker/CI/CD.

**Result**: ✅ PASS — no violations, no Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/053-hardware-first-stabilization/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── binary-model-export-format.md
│   ├── parity-procedure.md
│   └── inference-response.md
└── checklists/
    └── requirements.md  # from /speckit.specify
```

### Source Code (repository root)

```text
firmware/
├── include/
│   ├── config.h               # US1: SPAN=900, MIN/MAX 600/2400, flywheel run pulse↑,
│   │                          #      CMG_TORQUE_FULL_SCALE↓, CMG_TORQUE_SLEW_PER_S↑
│   ├── classifier.h           # US2: TremorClass → 2 classes; Decision.proba[2]; asserts
│   ├── tremor_model.h         # US2: regenerated — NUM_CLASS/raw-outputs reflect binary
│   └── edge_config.h          # US3: gate floor/scale params (proportional engagement)
├── src/
│   ├── cmg.cpp                # US1: torque→pulse mapping (full-range), optional refactor
│   ├── pid_controller.cpp     # US1: optional error→torque refactor (stable)
│   ├── classifier.cpp         # US2: sigmoid binary head (replaces 3-class softmax/argmax)
│   ├── tremor_model.cpp       # US2: regenerated arrays (binary)
│   └── suppression_gate.cpp   # US3: authority target from proba[TREMOR] + floor/ramp
└── (task_scheduler.cpp        # reads gate_authority(); telemetry pred_proba → 2 entries)

backend/
├── ml_models/
│   ├── train.py               # US2/US4: drop Voluntary group, binary objective, classes {0,1}
│   ├── export_to_c.py         # US2: accept num_class==1, init/base score, binary header/cpp
│   ├── parity_harness.py      # US2: binary sigmoid path + raw-capture parity mode
│   ├── features_lgbm.py       # (unchanged unless parity proves a feature-level defect)
│   └── lgbm_tremor_model.pkl/.json   # US4: regenerated artifacts (binary)
├── inference/
│   ├── services.py            # US2: CLASS_NAMES {0,1}; probs dict drops 'voluntary'; (n,2)
│   ├── serializers.py         # US2: response schema 2-class
│   └── views.py               # US2: any 3-class assumptions
├── realtime/ml_service.py     # US2: 3-class assumptions (if any)
├── apps/ml/predict.py         # US2: 3-class assumptions (if any)
├── monitor_edge_live.py       # US2: live edge validator — 2-class print + raw-capture aid
└── test_AI_live.py            # US2: 2-class output

frontend/
└── src/ (tremor monitor component)  # US2/FR-019: render 2-class; drop 'voluntary' gracefully

# New raw-capture reference data (provided / to-be-provided):
stable_glove_data_20260620_215329.csv     # provided: still-glove, ~33 Hz telemetry
<shaking_capture>.csv                      # dependency: Tremor reference
```

**Structure Decision**: Monorepo, firmware-primary + backend-secondary. US1 is firmware-config-only (`config.h`, `cmg.cpp`, `pid_controller.cpp`). US2/US4 span the ML pipeline (`train.py`, `export_to_c.py`, generated `tremor_model.*`, `classifier.*`, `parity_harness.py`) and the backend/telemetry consumers that assume 3 classes. US3 is localized to `suppression_gate.cpp` + `edge_config.h`. The frontend touch is limited to gracefully rendering a 2-class prediction.

## Complexity Tracking

> No constitution violations. Table intentionally empty.
