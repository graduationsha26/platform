# Phase 0 Research: Hardware-First Stabilization & Binary Tremor Pivot

All unknowns from the Technical Context are resolved below. No `NEEDS CLARIFICATION` markers remain.

---

## R1 — Gimbal full-range mapping (US1)

**Decision**: `CMG_GIMBAL_SPAN_US = 900`, `CMG_GIMBAL_MIN_US = 600`, `CMG_GIMBAL_MAX_US = 2400`, center 1500, trim 0.

**Rationale**: `torqueToMicros()` computes `us = CENTER + TRIM + torque × SPAN` with `torque ∈ [−1,+1]`, then clamps to `[MIN, MAX]`. SPAN is the **half-swing**. With center 1500 and clamps 600/2400, the half-swing that reaches the clamps exactly at ±1.0 is `2400 − 1500 = 900`. This yields a fully linear torque→pulse map across the entire control range.

**Alternatives considered**:
- `SPAN = 1800` (the original ask): reaches the clamp at torque ±0.5, so the upper half of PID authority is dead/non-linear. Rejected — it directly defeats "full-range" and was based on conflating total travel (1800 µs) with the half-swing.
- Narrower clamps (e.g. 1000–2000, SPAN 500): safer for the MG90s but sacrifices mechanical authority. Kept as the fallback if bench testing reveals binding at 600/2400 (see R9 risk).

---

## R2 — Flywheel reaction-torque authority (US1)

**Decision**: Raise `CMG_ESC_RUN_PULSE_US` from 1080 µs toward ~1200–1300 µs, bench-tuned to the highest value that runs continuously without brownout/reset/ESC re-arm. Keep the existing arm sequence (1000 µs for `CMG_ESC_ARM_MS`).

**Rationale**: CMG output torque is `τ = H × ω_gimbal`, `H = I_flywheel × Ω_flywheel`. The "no punch" symptom is a momentum deficit: 1080 µs is only 80 µs above the 1000 µs arm/idle pulse, so the flywheel is barely spinning and `H ≈ 0`. Increasing the run pulse raises Ω_flywheel and therefore the reaction torque available for the *same* gimbal motion. This is the single highest-leverage hardware change.

**Alternatives considered**:
- Lowering the run pulse (the original ask, "slower/safer"): reduces H → less authority; contradicts the goal. Rejected.
- A software spin-up ramp: unnecessary; the bench-validated sequence sets a constant throttle once. Out of scope unless raising the pulse trips the ESC.

---

## R3 — Un-squashing the PID→CMG signal (US1)

**Decision**: Lower `CMG_TORQUE_FULL_SCALE` (from 160) and raise `CMG_TORQUE_SLEW_PER_S` (from 40), bench-tuned. Starting points: `FULL_SCALE ≈ 60–90`, `SLEW ≈ 120–200/s`. Keep `CONTROL_LOOP_DT_S = 0.005`.

**Rationale**: `torqueCmd = constrain(−pid_output / FULL_SCALE, −1, 1)`. At Kp=2.0, a 10 deg/s tremor gives torque ≈ 0.125 — heavily squashed. Lowering FULL_SCALE saturates the gimbal sooner for the same error (snappier). The slew limiter caps torque change at `SLEW × dt`; at 40/s that is 0.2/cycle (≈25 ms to traverse full range), marginal for 4–8 Hz tremor (half-period 62–125 ms). Raising SLEW restores responsiveness; the documented trade-off is current ramp / brownout, so it is tuned empirically against R2.

**Alternatives considered**:
- Increasing Kp instead: also viable but couples damping (Kd) and integral behavior; the normalizer is the cleaner, more isolated lever. Both can be combined during tuning.
- Removing the slew limiter entirely: rejected — it is the brownout guard; we raise it, not delete it.

---

## R4 — Optional PID / CMG control-law refactor (US1)

**Decision**: Keep the existing PD law (`Ki = 0`) as the baseline. Permit a bounded refactor only if bench data shows benefit, with strict stability guards (no sustained oscillation, no stop-banging, latency budget preserved). Candidate improvement: a light derivative IIR filter to tame gyro-noise-driven D spikes once SLEW is raised.

**Rationale**: The current loop is bench-validated (`run_zizo`). Aggressive un-squashing can amplify derivative noise; a single-pole D filter is a low-risk addition. Anything larger (e.g. notch/resonator at the tremor band, feed-forward) is deferred unless tuning demands it.

**Alternatives considered**: Full controller redesign (state-space / band-pass resonant control) — rejected for scope/risk in a graduation timeline; revisit only if PD cannot meet SC-003.

---

## R5 — Binary LightGBM export & on-device inference math (US2)

**Decision**: Convert the model to a **binary** objective. In `export_to_c.py`, accept `num_class == 1` (binary boosters report a single tree series, ≈300 trees) and emit the model's **base/init score** so the device reproduces the raw margin exactly. In `classifier.cpp`, replace 3-class softmax+argmax with: `raw = init + Σ leaf_values`; `p_tremor = sigmoid(raw)`; `proba = {1 − p_tremor, p_tremor}`; `cls = p_tremor ≥ 0.5 ? TREMOR : NON_TREMOR`. `classifier.h` enum and `Decision.proba` become 2-class; static_asserts updated (Non-Tremor=0, Tremor=1).

**Rationale**: A binary LightGBM does not round-robin across 3 outputs; `dump_model()` gives `num_class == 1` and prediction is `sigmoid(raw_margin)`. The current exporter's `assert num_class == 3` and the interpreter's softmax are structurally wrong for binary. The base/init score matters: with `boost_from_average`, the raw margin includes a non-zero initial score; parity (`predict_proba` vs interpreter) fails if it is dropped. The interpreter stays generic (round-robin with `num_outputs`), choosing sigmoid when `num_outputs == 1`.

**Validation**: `parity_harness.py` Layer A is extended to the binary path and must hit ≥99% decision agreement and `max|Δproba| < 1e-3` between `pipe.predict_proba` and the float32 interpreter.

**Alternatives considered**:
- Keep 3-class and merge Voluntary→Tremor post-hoc: rejected — the user explicitly wants Voluntary removed from the architecture, and a merged head still carries the third series.
- Multiclass-with-2-classes (softmax over 2): works but is non-idiomatic and doubles trees vs a true binary objective; rejected for size/clarity.

---

## R6 — Data-driven parity debug methodology (US2)

**Decision**: A staged bisection comparing the Python pipeline (`features_lgbm` + `predict_proba`) against the C++ pipeline (`edge_features.cpp` + interpreter) on the **same raw samples**, in this order:
1. **Raw alignment**: column/axis order (`aX,aY,aZ,gX,gY,gZ`), per-axis **sign**, and **unit scale** (g vs m/s²) — accel capture is m/s² (aZ≈9.8); confirm training data uses the same units, else apply the correct scale.
2. **Sample rate**: the still capture is ~33 Hz (MQTT telemetry); the device classifies at 100 Hz. For faithful parity, capture a 100 Hz raw stream or resample the 33 Hz capture deterministically; for the *still* case, low-frequency content makes rate less critical for the Non-Tremor verdict.
3. **Band-pass output**: compare filtered windows (Python causal `sosfilt` vs C++ biquad cascade) element-wise.
4. **Per-feature**: compare all 66 features Python vs C++; localize any divergent index.
5. **Final score**: compare raw margin / probability.

The fix is whatever stage first diverges; success = still-glove windows classify Non-Tremor on-device (SC-004) and Python↔C agreement ≥99% (SC-005).

**Rationale**: "Predicts Tremor when still" with already-correct labels (`Control=0, Parkinson=1`, locked by `static_assert` in `classifier.h`) is definitionally a pipeline-parity defect, not a labeling defect. Bisecting from raw→features→score pinpoints the true cause instead of masking it. Unit scale (×9.8) is the highest-prior suspect because amplitude features scale linearly with it.

**Alternatives considered**:
- Swapping training labels (the original ask): rejected — labels are already correct; swapping would corrupt them and scramble the third class. Documented as an anti-pattern.
- Trusting Layer-A model parity alone: insufficient — Layer A proves the *interpreter* matches the *model on the same features*; it cannot catch a raw/feature mismatch upstream. The raw-capture mode is the new, necessary check.

---

## R7 — Proportional probability-scaled suppression (US3)

**Decision**: Derive the gate authority **target** from `proba[TREMOR]` via a clamped linear map with a low-confidence floor and full-authority ceiling: `target = clamp((p − P_LO) / (P_HI − P_LO), 0, 1)`, with new params (e.g. `GATE_P_LO ≈ 0.5`, `GATE_P_HI ≈ 0.9`) in `edge_config.h`. Keep the existing authority **ramp** (`GATE_RAMP_PER_S`) and `GATE_MIN_DWELL_MS` for anti-chatter. Retain the rollback path (`EDGE_GATE_ENABLED=false` → always-on) and the warm-up safe default (invalid decision → target 0).

**Rationale**: The control seam already exists (`pid_output *= edge::gate_authority()`, a smoothed float). Replacing the vote→binary target with a continuous probability map gives gentle correction for mild tremor and full authority for strong tremor, while the existing ramp prevents instantaneous jumps and the floor prevents dither from softmax noise. Minimal, localized change to `suppression_gate.cpp`.

**Alternatives considered**:
- Raw `p` as authority (no floor/scale): rejected — dithers near p≈0.3–0.5 from classifier noise.
- Keep the majority-vote gate and only soften the ramp: rejected — still binary in intent; doesn't meet FR-012 "scale continuously".
- Map confidence to PID gains instead of output scaling: more invasive, risks loop stability; output scaling is the safer equivalent.

---

## R8 — Unified, deterministic retrain & propagation (US4)

**Decision**: Single `train.py` run produces `lgbm_tremor_model.pkl` (+ `.json`) as the sole source of truth; `export_to_c.py` regenerates `tremor_model.h/.cpp` from it; re-running the export on the unchanged `.pkl` is byte-identical (SC-008, already enforced by `%.9g` formatting + reproducible flat build). Backend `inference/services.py` consumes the same `.pkl` at runtime. Retrain happens **after** the parity fix (FR-020) so both consumers inherit a correct model. PINNED hyperparameters keep the run reproducible; adapt them to the binary objective (`objective="binary"`, drop multiclass-only params).

**Rationale**: The "single structural truth" goal is the existing designed flow; the only changes are the class count and objective. Ordering retrain last guarantees the corrected pipeline (R6) is what gets baked in.

**Alternatives considered**: Separate models for backend vs device — rejected outright (the whole point is one artifact). Re-tuning hyperparameters via search during the run — rejected (non-reproducible; keep pinned, re-pin once if binary metrics regress).

---

## R9 — Backend / telemetry / frontend 2-class propagation (US2, FR-019)

**Decision**: Update every consumer that assumes 3 classes to 2: `inference/services.py` (`CLASS_NAMES = {0:'Non-Tremor',1:'Tremor'}`, drop `voluntary` from the probs dict, `proba` shape (n,2)), `serializers.py`/`views.py` response schema, `realtime/ml_service.py`, `apps/ml/predict.py`, `monitor_edge_live.py`, `test_AI_live.py`, the MQTT telemetry payload (`pred_proba` → 2 entries) in `task_scheduler.cpp`/`mqtt_publisher`, and the frontend tremor component (render 2-class; tolerate a missing third value). Audit via grep for `Voluntary`/`voluntary`/`proba[2]`/`[2]` index assumptions.

**Rationale**: A clean architectural removal (SC-006) requires no orphaned third-class references anywhere; otherwise indexers (`proba[2]`) or label maps silently break or mislabel.

**Risks / mitigations**:
- **MG90s binding at 600/2400 µs** → if bench shows stall/buzz, tighten clamps to the verified safe range (R1 fallback), keeping SPAN = (center − MIN).
- **33 Hz capture fidelity** → obtain a 100 Hz raw capture for definitive parity; treat the 33 Hz still capture as sufficient only for the rest/axis/sign/scale checks.
- **Binary base-score parity** → if `max|Δproba|` exceeds tolerance, the dropped init/base score is the first thing to verify (R5).
