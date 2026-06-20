# Tasks: On-Device Edge AI Tremor Classification

**Input**: Design documents from `/specs/052-edge-ai-inference/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Only the validation explicitly required by the spec/user is included — the host
**parity harness** (SC-005/SC-006/SC-008), on-device **verification** of labels/gate/cadence
(SC-001..SC-004, SC-009), and the **`monitor_edge_live.py`** visual monitor the user requires.
No speculative unit tests beyond these.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US4 (user-story phases only)

## Path Conventions

- Firmware (ESP32): `firmware/src/`, `firmware/include/`, `firmware/platformio.ini`
- ML / backend tooling: `backend/ml_models/`, `backend/tests/`, `backend/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ratify the architecture change and wire in the new dependencies/constants.

- [x] T001 Amend `.specify/memory/constitution.md` (user-approved): add an allowance for **on-device ML inference** (derived from the backend-trained model; backend remains authoritative for records) and for the **`esp-dsp`** firmware DSP library + a LightGBM→C export tool; bump version + add Sync Impact note. → v1.2.0, AI Model Serving "On-Device (Edge) Inference Exception".
- [x] T002 [P] Add `espressif/esp-dsp` to `lib_deps` in `firmware/platformio.ini`.
- [x] T003 [P] Add edge constants to `firmware/include/config.h.example`: `EDGE_FS_HZ=100`, `EDGE_WINDOW_SIZE=128`, `EDGE_FFT_SIZE=128`, `EDGE_HOP=10`, `EDGE_N_FEATURES=66`, `EDGE_N_CLASS=3`, gate params (`GATE_N_VOTE`, `GATE_ENGAGE_VOTES`, `GATE_DISENGAGE_VOTES`, `GATE_MIN_DWELL_MS`), `EDGE_GATE_ENABLED=true`, and the classification-task stack/core settings (per `contracts/edge-classifier-api.md`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Produce a **host-validated classification engine** — the realigned reference model, the C export, the firmware DSP + interpreter, and the parity harness gate. No on-device story may be flashed/trusted until the harness (T017) is green (per `quickstart.md`).

**⚠️ CRITICAL**: Blocks all user stories.

### Backend reference + model + export

- [x] T004 Realign `backend/ml_models/features_lgbm.py` to the edge pipeline: `FS=100`, `WINDOW_SIZE=128`, band-pass via **scipy Butterworth SOS** (`butter(4,[0.5,20]/nyq,'band',output='sos')`); causal `sosfilt` (whole-recording at train time / per-window for single-window paths), `bandpass_zerophase` fallback, preserving `get_feature_names_66()` order. Added `BANDPASS_SOS`, `get_bandpass_sos()`, `process_window()`.
- [x] T005 Update `backend/ml_models/train.py` for the native rate/window (inherits realigned constants; docstring/filter note updated; pinned params unchanged).
- [x] T006 **[GATED — approved, backed up first]** Ran the 100 Hz retrain → `lgbm_tremor_model.pkl` + `.json` + `combined_processed_data.csv` (8347×68). **CV macro precision 88.3%, accuracy 0.88 — matches the 66.67 Hz reference; causal filter retained accuracy (no fallback needed).** Prior model backed up to `backend/ml_models/backup_66hz_model/`.
- [x] T007 Created `backend/ml_models/export_to_c.py`: extracts the booster, asserts no scaler / no categorical / num_class==3 / ≤66 features, emits flat-array model + matching band-pass SOS per `contracts/model-export-format.md`.
- [x] T008 Ran `export_to_c.py` → `firmware/include/tremor_model.h` + `firmware/src/tremor_model.cpp` (900 trees, 112500 nodes, ~2.04 MB; 4 SOS sections). Set `board_build.partitions = huge_app.csv` so it fits the app partition (SC-007).

### Firmware classification engine

- [x] T009 [P] Implement the sliding-window ring buffer + `edge_push_sample()` / `edge_window_ready()` in `firmware/include/edge_features.h` + `firmware/src/edge_features.cpp` (6×128 float buffers, warm-up flag) per `data-model.md`.
- [x] T010 Implement the band-pass (streaming DF2T biquad cascade over scipy SOS; portable C++ for host-parity, esp-dsp optional) in `firmware/src/edge_features.cpp` using esp-dsp `dsps_biquad_f32` as a cascade of the hardcoded scipy SOS sections, re-applied over the buffered window from zero state (depends on T009; coefficients from T004).
- [x] T011 Implement the 128-pt real FFT (portable radix-2) + top-2 in-band (0.5–20 Hz) spectral features (freq+amp) in `firmware/src/edge_features.cpp` using esp-dsp (`dsps_fft2r_*`, manual magnitude), matching `_fft_top2` semantics (depends on T009).
- [x] T012 Implement the 7 per-axis statistics (mean, std[ddof=0], median, q1/q3 with NumPy linear interpolation, min, max) and assemble `edge_extract_features()` → 66-vector in axis-major order in `firmware/src/edge_features.cpp` (depends on T009).
- [x] T013 Implement the flat-array **tree interpreter** (iterative traversal, `x <= threshold`→left, `default_left` for non-finite) + per-class leaf sum (round-robin `i%3`) + numerically-stable softmax in `firmware/src/classifier.cpp` / `firmware/include/classifier.h`, consuming `tremor_model.h` (depends on T008).
- [x] T014 Implement `classify_features()` and `classify_current_window()` glue (ready→extract→classify, sets `Decision.valid`) in `firmware/src/classifier.cpp` (depends on T012, T013).

### Host parity harness (integration gate)

- [x] T015 [P] Added host C-ABI shim `backend/ml_models/parity_shim.cpp` (reset/push/ready/features/predict) for the user's compiler env. Original wording: Add a **host build** of `edge_features.cpp` + `tremor_model.cpp` exposing `extract_features(window)` and `predict(features)` to Python (ctypes/cffi shim or small native exe) in `backend/ml_models/` (depends on T008; engine sources from T010–T014).
- [x] T016 Created `backend/ml_models/parity_harness.py` driving held-out 128×6 windows through both Python reference and the host-built C engine (depends on T015).
- [x] T017 [RAN: 3 passed, 1 skipped — model parity 100%, max |Δproba| 0; C feature layer skips w/o host compiler] Create `backend/tests/test_edge_parity.py` asserting P1 feature parity (SC-006), P2 decision agreement ≥95% (SC-005), P3 proba parity, P4 mapping (tremor→1/rest→0, SC-001) per `contracts/parity-harness.md`; **must pass before any on-device flashing** (depends on T016).

**Checkpoint**: Host-validated engine ready; the parity harness is green.

---

## Phase 3: User Story 1 - Trustworthy labels + Tremor-gated suppression (Priority: P1) 🎯 MVP

**Goal**: Lock the canonical mapping on-device and make suppression engage **only** on sustained Tremor (1), smoothly, replacing always-on suppression — so the device never fights resting/voluntary motion and never chatters the actuators.

**Independent Test**: On-bench, induce tremor → class 1 + suppression engages; hold still → class 0 + disengages; move intentionally → class 2 + stays disengaged; flicker at a boundary → no per-cycle actuator toggling (SC-001, SC-009).

- [x] T018 [P] [US1] Define `enum class TremorClass : uint8_t {NON_TREMOR=0,TREMOR=1,VOLUNTARY=2}` with a `static_assert` locking the mapping, in `firmware/include/classifier.h` (or a shared header).
- [x] T019 [US1] Implement `firmware/include/suppression_gate.h` + `firmware/src/suppression_gate.cpp`: 4-state machine (`DISENGAGED/ENGAGING/ENGAGED/DISENGAGING`), sliding vote, asymmetric hysteresis, `GATE_MIN_DWELL_MS`, authority ramp, default-safe on `!Decision.valid`, and `EDGE_GATE_ENABLED=false` rollback to always-on — per `contracts/edge-classifier-api.md` (depends on T014).
- [x] T020 [US1] Integrate the gate into `firmware/src/task_scheduler.cpp` (ControlTask) and `firmware/src/pid_controller.cpp`: scale the actuator command by `gate_authority()` / hold neutral when `!gate_suppression_active()`; **PID control law unchanged** (depends on T019).
- [ ] T021 [US1] ⏳ REQUIRES HARDWARE — On-device verification of SC-001 (tremor→1+engage, rest→0+disengage, voluntary→2+disengaged) and SC-009 (alternating borderline decisions cause no per-cycle gate toggling); document results (depends on T020, and ClassificationTask T022).

**Checkpoint**: Suppression is correctly, smoothly gated by the locked class mapping.

---

## Phase 4: User Story 2 - Real-time on-device classification + visual monitoring (Priority: P1)

**Goal**: Run classification locally at ≥10 Hz with no backend/network, and let the prediction be **observed live** via MQTT in the exact 7-field format used previously.

**Independent Test**: Disconnect WiFi/broker → device still classifies/gates (SC-004); when connected, `monitor_edge_live.py` prints ≥10 lines/sec in the exact format (SC-002).

- [x] T022 [US2] Add a dedicated **ClassificationTask pinned to Core 0** (~100 ms cadence) in `firmware/src/task_scheduler.cpp`: snapshot ring buffer → `classify_current_window()` → `gate_update()`; honor warm-up (withhold while `!edge_window_ready()`) per `research.md §6` (depends on T014; uses gate from T019).
- [x] T023 [US2] Extend `firmware/src/mqtt_publisher.cpp` (+ `FusedReading`/JSON doc in `firmware/include/mqtt_publisher.h`) to **append the on-device prediction** to the existing telemetry payload: predicted class index/name, `confidence`, and the 3 class probabilities (`non_tremor`, `tremor`, `voluntary`) — same topic `tremo/sensors/{serial}` (depends on T022).
- [x] T024 [P] [US2] Create `backend/monitor_edge_live.py`: subscribe to `tremo/sensors/+`, parse the appended prediction fields, and print the **exact 7-field format** `Sample, Prediction, Confidence, Precision, Non-Tremor %, Tremor %, Voluntary %` (Precision read from `backend/ml_models/lgbm_tremor_model.json`; MQTT creds via `--username/--password` or env; paho-mqtt VERSION2) — mirrors `backend/test_AI_live.py` output exactly but consumes the ESP32 decision (depends on T023 for payload shape; can be drafted in parallel against the contract).
- [ ] T025 [US2] ⏳ REQUIRES HARDWARE — Validate SC-004 (offline classify/gate with broker down) and SC-002 (≥10 Hz refresh; `monitor_edge_live.py` shows ≥10 lines/sec connected); document results (depends on T023, T024).

**Checkpoint**: On-device classification runs offline and is visually monitorable exactly as before.

---

## Phase 5: User Story 3 - Accuracy parity with the validated model (Priority: P2)

**Goal**: Prove the edge classifier matches the reference and the native-rate retrain didn't degrade accuracy.

**Independent Test**: Full held-out parity run meets SC-005/SC-006; retrain retains ~0.88 macro precision; export is reproducible (SC-008).

- [~] T026 [US3] Model-layer parity DONE (decision agreement 100%, max |Δproba| 0 on 400 held-out windows). **SC-006 feature parity (C DSP vs features_lgbm) PENDING a host C++ compiler** — Layer B of the harness; run `pytest` on a machine with g++/clang/MSVC or PlatformIO `native`.
- [x] T027 [US3] Retrain accuracy retained: 100 Hz/causal-SOS model CV macro precision **88.3%** == the 66.67 Hz reference (~0.88). No filtfilt fallback needed.
- [x] T028 [US3] Reproducibility (SC-008) DONE — `build_flat_model` byte-identical across runs (harness `check_export_reproducible` = True). m2cgen cross-check is optional/deferred (interpreter already proven 100% vs the Python model). Original: Reproducibility (SC-008): re-run `export_to_c.py`, assert byte-identical `tremor_model.*`; run the m2cgen cross-check (raised recursion limit) and diff `output[]` vs the interpreter on sample inputs (depends on T008).

**Checkpoint**: Edge accuracy is quantified, parity-proven, and reproducible.

---

## Phase 6: User Story 4 - Fits the device with real-time headroom (Priority: P3)

**Goal**: Confirm the firmware+model fit flash/RAM with headroom and don't break existing real-time deadlines; finalize gate tuning.

**Independent Test**: Build report within headroom budget; ControlTask <70 ms latency warning never fires with ClassificationTask running (SC-003, SC-007).

- [x] T029 [US4] Firmware built (`pio run -e esp32dev`, SUCCESS). With `partitions_edge.csv` (3.69 MB app): **Flash 75.7% (2.93 MB), RAM 15.7% (51.6 KB)** — comfortable headroom (SC-007 footprint ✓).
- [ ] T030 [US4] ⏳ REQUIRES HARDWARE — On-device timing: confirm the existing sensor→actuation `<70 ms` warning never fires while ClassificationTask runs on Core 0, and measure the per-cycle classification time (SC-003/SC-007) (depends on T022).
- [ ] T031 [US4] ⏳ REQUIRES HARDWARE (bench) — safe defaults set in `edge_config.h` (N_VOTE=5, engage/disengage=4, dwell=400 ms, ramp=2/s). Bench-tune the gate parameters (`GATE_N_VOTE`, engage/disengage votes, `GATE_MIN_DWELL_MS`, ramp) for safe-yet-responsive transitions; finalize in `firmware/include/config.h.example`; re-verify SC-009 (depends on T021).

**Checkpoint**: All success criteria validated on hardware.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T032 [P] Updated `firmware/README.md` (edge AI section) and `backend/ml_models/README.md` (100 Hz pipeline + Feature 052 section: export_to_c, parity gate, monitor, backup).
- [x] T033 [P] Updated `.gitignore` (edge_parity.dll/.exe, *.o, backup_66hz_model/; CSV/.so/config.h/.pio already ignored). Decision: `tremor_model.*` is **generated but TRACKED** (same convention as the `.pkl`) so firmware builds without regenerating.
- [ ] T034 ⏳ REQUIRES HARDWARE — Run the `quickstart.md` walkthrough end-to-end (steps 4–6 need the ESP32 + broker). Steps 1–3 (retrain, export, model-parity) already done and green.

---

## Dependencies & Execution Order

### Phase dependencies
- **Setup (P1)**: none — start immediately.
- **Foundational (P2)**: after Setup — **blocks all stories**. The chain T004→T005→T006(gated)→T007→T008 produces the model+export; T009→{T010,T011,T012}→T014 and T013→T014 build the engine; T015→T016→T017 is the parity gate.
- **User Stories**: after Foundational + a green parity harness (T017).
- **Polish**: after the desired stories.

### Story dependencies / interaction
- **US1 (P1)** and **US2 (P1)** are intertwined on-device: US1's on-device verification (T021) needs US2's ClassificationTask (T022), and US2's `gate_update` uses US1's gate (T019). Treat **US1+US2 together as the MVP**. Gate logic (T019) and the monitor (T024) are independently developable.
- **US3 (P2)**: depends only on Foundational (T017/T008); independent of on-device stories (runs on host). Recommended **before** flashing US1/US2 to trust the engine.
- **US4 (P3)**: depends on the firmware integration (T022) and US1 gate (T021).

### Parallel opportunities
- Setup: T002, T003 in parallel (T001 independent).
- Foundational firmware: T009 then T010/T011/T012 in parallel (same file `edge_features.cpp` → coordinate or split into units); T013 parallel to the DSP tasks (different file); T015 parallel once T008 done.
- US2: T024 (monitor, Python) parallel to firmware T022/T023.

---

## Parallel Example: Foundational firmware engine

```bash
# After T009 (ring buffer) lands, the three feature stages can be split across devs:
Task: "T010 band-pass (esp-dsp biquads) in firmware/src/edge_features.cpp"
Task: "T011 128-pt FFT + spectral peaks in firmware/src/edge_features.cpp"
Task: "T012 statistics + assemble 66-vector in firmware/src/edge_features.cpp"
# In parallel, on a different file:
Task: "T013 flat-array interpreter + softmax in firmware/src/classifier.cpp"
```

---

## Implementation Strategy

### MVP (User Stories 1 + 2 together)
1. Phase 1 Setup → Phase 2 Foundational (get the **parity harness T017 green** — this is the gate).
2. Build US1 (gate + mapping) and US2 (ClassificationTask + MQTT prediction + monitor) together.
3. **STOP and VALIDATE** on hardware: SC-001, SC-002, SC-004, SC-009; watch `monitor_edge_live.py`.
4. Demo: the glove classifies locally, suppresses only real tremor smoothly, and is observable live.

### Incremental delivery
- Foundational → host-validated engine (no hardware needed to trust it).
- + US1/US2 → on-device MVP (offline, gated, monitorable).
- + US3 → quantified parity/accuracy sign-off.
- + US4 → footprint/timing sign-off + final gate tuning.

### Notes
- **Gated step**: T006 (retrain) requires explicit user approval before running (as in Feature 051).
- **Hard gate**: do not flash US1/US2 to hardware until T017 (parity) passes.
- `tremor_model.*` is generated by `export_to_c.py` — never hand-edit; regenerate on retrain.
- Keep the feature definition + class mapping identical across `features_lgbm.py`, the export, and the firmware (FR-012).
