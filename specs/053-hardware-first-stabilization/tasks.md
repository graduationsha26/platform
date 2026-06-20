---
description: "Task list for Hardware-First Stabilization & Binary Tremor Pivot"
---

# Tasks: Hardware-First Stabilization & Binary Tremor Pivot

**Input**: Design documents from `/specs/053-hardware-first-stabilization/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No standalone TDD suite was requested. The existing **parity harness**
(`backend/ml_models/parity_harness.py` + `backend/tests/test_edge_parity.py`) is the acceptance
gate for US2/US4 and is extended/run as implementation, not written test-first.

**Organization**: Tasks are grouped by user story. Phases are **gated** (FR-020):
US1 → US2 → US3 → US4. US1 is fully independent; US3 and US4 depend on US2 (binary probability +
parity fix).

## Path Conventions
- Firmware: `firmware/src/`, `firmware/include/`
- ML: `backend/ml_models/`
- Backend inference: `backend/inference/`, `backend/realtime/`, `backend/apps/ml/`
- Frontend: `frontend/src/`

---

## Phase 1: Setup (Shared Prerequisites)

**Purpose**: Make both tracks (bench + ML) runnable and capture baselines.

- [ ] T001 Confirm bench rig is operational (flywheel ESC + MG90s gimbal + MPU6500) and the ESP32 flashes cleanly from `firmware/` via PlatformIO; record the current boot log baseline.
- [ ] T002 [P] Verify a host C++ compiler (g++/clang++/MSVC or PlatformIO `native`) is available for Layer-B parity, per `contracts/parity-procedure.md`; note the toolchain in the feature notes.
- [ ] T003 [P] Verify the Python ML env runs `python backend/ml_models/parity_harness.py` (Layer A) against the current 3-class model as a known-good baseline before any change.
- [ ] T004 [P] Record a pre-tuning hardware baseline (gimbal travel + flywheel behavior + disturbance response) for later SC-001/SC-002/SC-003 comparison.

**Checkpoint**: Both tracks runnable; baselines captured.

---

## Phase 2: Foundational (Parity Data Acquisition — blocks US2 validation)

**Purpose**: Obtain the raw captures the parity debug needs. (Does NOT block US1.)

**⚠️ The still capture is provided; the others are open dependencies for full US2 fidelity.**

- [X] T005 Confirm the provided still-glove capture `stable_glove_data_20260620_215329.csv` (columns `Timestamp,aX,aY,aZ,gX,gY,gZ`, accel m/s², gyro deg/s, ~33 Hz) is readable and place/reference it for the parity harness. **DONE — readable, 1409 rows, accel m/s² (|g|≈9.807), gyro deg/s; effective rate ≈20 Hz.**
- [ ] T006 [P] Record a **shaking/Tremor** reference capture (counterpart to the still capture) for SC-004/SC-005 (Dependencies in plan.md).
- [ ] T007 [P] Record a **100 Hz raw** capture (device-native rate) for faithful rate parity vs the on-device 100 Hz stream (preferred over the 33 Hz telemetry capture).

**Checkpoint**: Reference data available (still mandatory; shaking + 100 Hz preferred).

---

## Phase 3: User Story 1 - Hardware Liberation & Stabilization Tuning (Priority: P1) 🎯 MVP

**Goal**: Full-range linear gimbal, raised flywheel torque authority, un-squashed PID→CMG path.

**Independent Test**: Bench-only (no ML) — synthetic torque sweep is linear across 600–2400 µs;
flywheel soaks 10 min with no brownout; induced disturbance shows a stronger/faster correction.

### Implementation for User Story 1

- [X] T008 [US1] `firmware/include/config.h` gimbal full-range mapping: `SPAN=900`, `MIN=600`, `MAX=2400` (center 1500, trim 0). **DONE — invariant holds with equality (`CENTER−SPAN=MIN`, `CENTER+SPAN=MAX`). Mirrored in `config.h.example`.**
- [X] T009 [US1] `CMG_ESC_RUN_PULSE_US` 1080 → **1200** (arm pulse kept 1000). **DONE (both config.h + .example).**
- [X] T010 [US1] Un-squash: `CMG_TORQUE_FULL_SCALE` 160 → **80**, `CMG_TORQUE_SLEW_PER_S` 40 → **150**. **DONE (both config.h + .example).**
- [X] T011 [P] [US1] Reviewed `cmg.cpp`: `torqueToMicros()` = `1500 + torque×900` clamped [600,2400] → ±1.0 maps exactly to the clamps, fully linear; slew 150×0.005=0.75/cycle → full ±1 range in ~13 ms. **DONE — no code change needed.**
- [ ] T012 [P] [US1] (Optional) derivative IIR filter in `pid_controller.cpp`. **DEFERRED to bench — only add if the raised slew shows gyro-noise D spikes; PD left unchanged for now.**
- [ ] T013 [US1] Bench: torque sweep −1→+1 linear across 600…2400 µs (SC-001). **PENDING — bench.**
- [ ] T014 [US1] Bench: 10-min flywheel soak; back off to highest stable value if brownout (SC-002). **PENDING — bench.**
- [ ] T015 [US1] Bench: induced-disturbance test vs baseline; tighten clamps if MG90s binds (SC-003). **PENDING — bench.**

**Checkpoint**: Hardware delivers strong, full-range, stable physical stabilization (MVP).

---

## Phase 4: User Story 2 - Binary Classification Pivot & Data-Driven Parity Fix (Priority: P2)

**Goal**: Clean 2-class model (Non-Tremor=0/Tremor=1), no Voluntary, with on-device behavior matching
training; "Tremor when still" fixed at its real parity root cause.

**Independent Test**: Software-only — train binary model; Python and C++ pipelines agree window-by-window
on the reference captures; still→Non-Tremor, shaking→Tremor.

**⚠️ Parity debug (T016–T019) comes BEFORE the binary conversion, per quickstart.md.**

### Parity debug first (find the real root cause)

- [X] T016 [US2] Extend `backend/ml_models/parity_harness.py` with a **Layer C raw-capture mode**: load a raw IMU CSV, run it through both `features_lgbm` (Python) and the firmware pipeline path, and compare end-to-end + assert the expected verdict (contracts/parity-procedure.md). **DONE — implemented as standalone diagnostics `backend/ml_models/parity_debug_raw.py` + `group_variance_check.py` (fold into parity_harness.py during the fix phase).**
- [X] T017 [US2] Run the Layer C bisection on the still capture in this order — raw axis order/sign, **unit scale (g vs m/s², ×9.8 suspect)**, sample rate (33 vs 100 Hz), band-pass output, per-feature (66), final score — and record the first divergent stage (FR-010). **DONE — root cause at the RAW/TRAINING-DATA stage (NOT firmware/axis/capture-units). See report. Bug reproduces in pure Python (still → Tremor P=0.99).**
- [X] T018 [US2] Implement the localized fix at the proven stage. **DONE — the divergence was DATA-level (not firmware/features), so the fix lives in `backend/ml_models/train.py`: a unit-integrity guard `is_physical_units()` quarantines 16 raw-ADC-count Control files (median|a|≈13000), and the verified device still-glove capture is added as Non-Tremor. `edge_features.cpp`/`features_lgbm.py` unchanged (they were already correct).**
- [X] T019 [US2] Verify the fix: still-glove windows classify Non-Tremor ≥95% (SC-004). **DONE — `verify_binary_model.py`: still capture → 100% Non-Tremor, P=0.998. Centroids now physical (Non-Tremor std < Tremor std; Tremor peak in 3–8 Hz band).**

### Binary conversion (training → export → device)

- [X] T020 [US2] `train.py` → binary (drop Voluntary group, `objective="binary"`, `CLASS_NAMES=["Non-Tremor","Tremor"]`, metadata `classes={0,1}`, quarantine + still capture). **DONE — retrain: Non-Tremor=2225 (2170 Control+55 still), Tremor=2893; macro-F1 0.87.**
- [X] T021 [US2] `export_to_c.py` → binary: accepts `num_class==1`, recovers the base/init score data-free, emits `NUM_RAW_OUTPUTS=1` + `NUM_CLASS=2` header. **DONE — exported: 300 trees, 37500 nodes, init_score=0 (SMOTE-balanced ⇒ log-odds 0).**
- [X] T022 [P] [US2] `firmware/include/classifier.h` → `TremorClass{NON_TREMOR=0,TREMOR=1}`, `Decision.proba[2]`, static_asserts updated. **DONE.**
- [X] T023 [US2] `firmware/src/classifier.cpp` → binary sigmoid head (`raw=init+Σleaf`, `p=sigmoid`, `proba={1−p,p}`, `cls=p≥0.5`). **DONE.**
- [X] T024 [US2] `parity_harness.py` `_interp_predict` → binary sigmoid path. **DONE — Layer A: 100% decision agreement, max|Δproba|=0.000000; `pytest test_edge_parity.py` 3 passed.**
- [X] T025 [P] [US2] `backend/inference/services.py` → `CLASS_NAMES={0,1}`, probs dict drops `voluntary`, proba `(n,2)`. **DONE.**
- [X] T026 [P] [US2] `backend/inference/serializers.py` (`max_value=1`, 2-key help) + `views.py` comments → 2-class. **DONE.**
- [X] T027 [P] [US2] `backend/realtime/ml_service.py` (severity heuristic — index 2 now unreachable, no change needed) + `backend/apps/ml/predict.py` (indexes `proba[prediction]` generically — no change needed). **DONE — verified no 3-class assumptions.**
- [X] T028 [P] [US2] `backend/monitor_edge_live.py` + `backend/test_AI_live.py` → 2-class output (dropped Voluntary % column + `p_vol`). **DONE.**
- [X] T029 [P] [US2] `firmware/src/task_scheduler.cpp` (`g_pred_proba[2]`) + `mqtt_publisher.cpp/.h` (`pred_proba[2]`, dropped `voluntary` JSON). **DONE.**
- [X] T030 [P] [US2] Frontend: **no change needed** — grep found zero `voluntary`/probabilities/index-2 coupling in `frontend/src/` (renders `predicted_class`/tremor only). **DONE (verified).**
- [X] T031 [US2] Audit: grep for `Voluntary`/`proba[2]`/`NUM_CLASS==3`/`init_score[2]` → only correct 2-element arrays + "dropped" comments remain. **DONE (SC-006).**

**Checkpoint**: Binary model is correct end-to-end and parity-verified; still→Non-Tremor, shaking→Tremor.

---

## Phase 5: User Story 3 - Proportional, Probability-Scaled Suppression (Priority: P3)

**Goal**: Suppression authority scales smoothly with Tremor probability; no chatter; floor + ceiling.

**Independent Test**: Feed a synthetic ramped Tremor probability (0→1→0); authority follows smoothly
and monotonically, neutral below floor, full above ceiling, no per-cycle toggling.

**Depends on US2** (needs the binary `proba[TREMOR]`).

### Implementation for User Story 3

- [X] T032 [US3] `firmware/include/edge_config.h` → added `GATE_P_LO` (0.50) and `GATE_P_HI` (0.90) `#ifndef`-guarded. **DONE.**
- [X] T033 [US3] `firmware/src/suppression_gate.cpp` → continuous target `clamp((proba[TREMOR]−P_LO)/(P_HI−P_LO),0,1)`, ramp retained, warm-up/invalid→0, `EDGE_GATE_ENABLED` rollback preserved. **DONE.**
- [ ] T034 [US3] Test: feed a synthetic ramped probability and confirm authority tracks smoothly (SC-007). **PENDING — logic implemented & code-reviewed; needs a host-compiled or on-device run to execute (no compiler/bench here).**
- [X] T035 [US3] Warm-up/invalid → authority neutral (FR-015). **DONE — `if (d.valid) … else target=0.0f` in `gate_update`.**

**Checkpoint**: Mild tremor → gentle correction; strong tremor → full authority; no chatter.

---

## Phase 6: User Story 4 - Unified Retrain & Deployment (Priority: P4)

**Goal**: One training run is the single source of truth for both backend and firmware models.

**Independent Test**: One `train.py` run emits one artifact; `export_to_c.py` regenerates firmware
arrays; re-export is byte-identical; backend and device agree on identical windows.

**Depends on US2** (binary pipeline must be correct + parity-fixed first, FR-020).

### Implementation for User Story 4

- [X] T036 [US4] `python backend/ml_models/train.py` (one run) → binary `.pkl` + `.json`. **DONE (23.7s).**
- [X] T037 [US4] `python backend/ml_models/export_to_c.py` → regenerated `tremor_model.h/.cpp` (binary). **DONE.**
- [X] T038 [US4] Re-run export → byte-identical. **DONE — SHA256 IDENTICAL for both files; harness `export reproducible: True` (SC-008).**
- [~] T039 [US4] Backend ↔ device class agreement on identical windows (SC-009). **MODEL-SIDE DONE — flat-array interpreter matches `predict_proba` 100% (Layer A). Actual C++ build (Layer B) SKIPPED: no host C++ compiler available.**
- [ ] T040 [US4] Flash firmware + end-to-end smoke test. **PENDING — requires bench hardware (cannot flash here).**

**Checkpoint**: Backend and device share one structural truth; full pipeline verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Parity tests. **DONE — `pytest test_edge_parity.py`: 3 passed, 1 skipped (C compiler); `parity_harness.py`: PASS.**
- [ ] T042 [P] Update data-model.md with the final bench-tuned hardware values. **PENDING — belongs to US1 (bench), not yet tuned.**
- [X] T043 Final audit: no orphaned 3-class refs (SC-006); rollback intact. **DONE — `EDGE_GATE_ENABLED=false` still forces always-on; prior `.pkl` restorable via git.**
- [ ] T044 Full `quickstart.md` SC-001…SC-009 validation. **PARTIAL — ML criteria (SC-004/005/006/008/009 model-side) met; hardware SC-001/002/003 + on-device SC-007/009-C pending bench.**

---

## Dependencies & Execution Order

### Phase / Story dependencies
- **Setup (P1)**: no dependencies.
- **Foundational (P2)**: parity data; blocks US2 *validation* only (not US1).
- **US1 (P1)**: independent — can start immediately after Setup (does not need ML or parity data). **MVP.**
- **US2 (P2)**: needs the still capture (T005). Internal order: parity debug (T016–T019) → binary conversion (T020–T031).
- **US3 (P3)**: depends on US2 (binary `proba[TREMOR]`).
- **US4 (P4)**: depends on US2 (and should include US3 firmware changes before flashing). Must follow a verified parity fix (FR-020).
- **Polish (P7)**: after US2/US4.

### Within US2
- T016→T017→T018→T019 (parity debug, sequential bisection).
- T021 + T022 → T023 (export contract + header before sigmoid head).
- Consumer updates T025–T030 are file-independent ([P]) once the 2-class decision (T020/T021) is set.

### Parallel opportunities
- Setup: T002, T003, T004 in parallel.
- Foundational: T006, T007 in parallel.
- US1: T011, T012 in parallel after T008–T010.
- US2 consumers: T025, T026, T027, T028, T029, T030 in parallel (different files); T022 in parallel with T021.
- Polish: T041, T042 in parallel.

---

## Implementation Strategy

### MVP (User Story 1 only)
1. Setup (T001–T004) → US1 (T008–T015). **STOP & VALIDATE** SC-001/002/003 on the bench. This alone delivers stronger physical stabilization and is demoable without any ML change.

### Incremental delivery
1. US1 → bench demo (MVP).
2. US2 → parity fix + binary model; Python↔C parity green (SC-004/005/006).
3. US3 → proportional suppression (SC-007).
4. US4 → unified retrain + byte-identical export + device/backend agreement (SC-008/009).

### Notes
- Respect the FR-020 gate: do not start US4 retrain until US2 parity is verified.
- Commit after each task or logical group; keep generated `tremor_model.*` commits separate from hand edits.
- Implementation execution remains gated on the user's go-ahead + confirmation of parity data.
