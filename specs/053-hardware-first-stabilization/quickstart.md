# Quickstart: Hardware-First Stabilization & Binary Tremor Pivot

How to validate each phase locally. Phases are gated — finish and verify one before the next
(FR-020). Implementation is gated on the user's go-ahead + confirmation of parity data.

## Prerequisites
- Assembled CMG on the bench (flywheel ESC + MG90s gimbal + MPU6500), powered from a supply that
  can show brownout.
- ESP32 toolchain (PlatformIO) for `firmware/`.
- Python env with the `backend/ml_models` deps (lightgbm, imbalanced-learn, scikit-learn, scipy,
  joblib, pandas, numpy).
- A host C++ compiler (g++/clang++/MSVC or PlatformIO `native`) for Layer-B parity (optional but
  recommended).

---

## Phase 1 — Hardware (US1)
1. Edit `firmware/include/config.h`: `CMG_GIMBAL_SPAN_US=900`, `CMG_GIMBAL_MIN_US=600`,
   `CMG_GIMBAL_MAX_US=2400`; raise `CMG_ESC_RUN_PULSE_US` (start 1200); lower
   `CMG_TORQUE_FULL_SCALE` (start ~80); raise `CMG_TORQUE_SLEW_PER_S` (start ~150).
2. Flash; watch the boot log for the CMG arm/run line and confirm no brownout/reset loop.
3. **Gimbal sweep** (bench): command a synthetic torque sweep −1→+1; confirm the pulse moves
   linearly across 600…2400 µs, hitting each clamp only at ±1.0. ✅ SC-001.
4. **Flywheel soak**: run 10 min continuously; zero brownouts/watchdog resets/ESC re-arms. ✅ SC-002.
5. **Disturbance test**: induce a tremor-like wobble on the target axis; confirm a visibly
   stronger/faster corrective swing than baseline, no stop-banging. ✅ SC-003.
6. Back off any value that causes binding/brownout to the highest stable setting.

## Phase 2 — Binary pivot + parity (US2)
1. **Parity first (no retrain yet)** — run the raw-capture parity (Layer C) on the still capture:
   compare Python vs C++ from raw → features → score; bisect per `contracts/parity-procedure.md`.
   Check units (g vs m/s²), axis order/sign, then rate (33 vs 100 Hz), filter, features.
2. Apply the localized fix; confirm still-glove windows classify Non-Tremor on-device. ✅ SC-004.
3. Convert to binary: `train.py` (drop Voluntary group, `objective="binary"`, classes {0,1});
   `export_to_c.py` (accept `num_class==1`, emit init/base score, sigmoid header);
   `classifier.h/.cpp` (2-class enum, sigmoid head); backend `inference` + telemetry + frontend
   to 2-class (`contracts/inference-response.md`).
4. Run `python backend/ml_models/parity_harness.py`: Layer A agreement ≥99%, `max|Δproba|<1e-3`. ✅ SC-005.
5. Grep for `Voluntary`/`voluntary`/`proba[2]`/`NUM_CLASS == 3` → zero hits. ✅ SC-006.

## Phase 3 — Proportional engagement (US3)
1. Add `GATE_P_LO`/`GATE_P_HI` to `edge_config.h`; update `suppression_gate.cpp` to map
   `proba[TREMOR]` → authority target with floor/ceiling, keeping ramp + dwell.
2. Feed a synthetic ramped probability (0→1→0); confirm authority follows smoothly and
   monotonically, neutral below the floor, full above the ceiling, no per-cycle chatter. ✅ SC-007.
3. Confirm warm-up/invalid → neutral (safe). FR-015.

## Phase 4 — Unified retrain (US4)
1. `python backend/ml_models/train.py` (ONE run) → `lgbm_tremor_model.pkl` + `.json` (binary).
2. `python backend/ml_models/export_to_c.py` → regenerates `tremor_model.h/.cpp` (2-class).
3. Re-run export; confirm byte-identical output (`git diff` clean). ✅ SC-008.
4. Cross-check: backend `predict` and on-device classifier agree on identical windows. ✅ SC-009.
5. Flash firmware; smoke-test end-to-end (still → Non-Tremor + neutral authority; shaking → Tremor
   + scaled suppression).

---

## Rollback
- Hardware: revert `config.h` constants (git).
- Suppression: set `EDGE_GATE_ENABLED=false` (legacy always-on) without recompiling logic.
- Model: restore the previous `.pkl` + regenerate the C arrays.
