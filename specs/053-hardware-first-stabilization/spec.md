# Feature Specification: Hardware-First Stabilization & Binary Tremor Pivot

**Feature Branch**: `053-hardware-first-stabilization`
**Created**: 2026-06-21
**Status**: Draft (awaiting Principal-Engineer review sign-off before implementation)
**Input**: User description: "Hardware-First approach — liberate and tune the CMG/gimbal hardware for maximum physical stabilization first; pivot the tremor classifier from 3-class to binary (Tremor=1 / Non-Tremor=0) with a data-driven parity fix; replace the binary suppression gate with probability-scaled proportional engagement; then run one unified retrain that produces both the backend model and the ESP32 C array from a single structural truth."

## Context & Engineering Decisions (resolved before drafting)

This spec supersedes the prior prioritization. It follows a strict **Hardware First** order. The following decisions were resolved during review and are treated as settled inputs (not open questions):

1. **Flywheel authority — RAISE, do not lower.** CMG output torque is `τ = H × ω_gimbal`, where `H = I_flywheel × Ω_flywheel`. The flywheel currently runs at `CMG_ESC_RUN_PULSE_US = 1080 µs`, only 80 µs above the 1000 µs arm/idle pulse — i.e. barely spinning. The lack of "punch" is a momentum deficit, not a gimbal-range deficit. The run pulse will be **raised** (target band ~1200–1300 µs), then the gimbal re-tuned against the higher authority.
2. **Gimbal SPAN = 900 µs, not 1800.** The mapping is `pulse_us = CENTER(1500) + torque × SPAN`, with `torque ∈ [−1, +1]` clamped to `[MIN, MAX]`. With `MIN = 600 / MAX = 2400`, a half-swing of **900** reaches the clamps exactly at ±1.0 torque (full linear range). `SPAN = 1800` would saturate at ±0.5 torque, killing the upper half of control authority. SPAN is the half-swing, not the total travel.
3. **Classification pivot to BINARY.** The `Voluntary` (class 2) category is dropped entirely. The system classifies only **Tremor = 1** vs **Non-Tremor = 0** across the training pipeline, the model export, and the on-device interpreter.
4. **The "predicts Tremor when still" symptom is a parity bug, not a labeling bug.** Training labels were already `Non-Tremor=0 / Tremor=1`; blindly swapping them would corrupt data. The fix is a **data-driven parity debug** using a real still-glove IMU capture (provided at `stable_glove_data_20260620_215329.csv`) to definitively locate any axis-order, sign, or scaling mismatch between the Python feature pipeline and the C++ on-device pipeline.
5. **Proportional engagement** replaces the binary vote→on/off authority: suppression strength scales smoothly with the model's Tremor-class probability.
6. **One unified retrain** produces the backend model and the firmware C arrays from the same single source of truth, deterministically.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hardware Liberation & Stabilization Tuning (Priority: P1)

As the embedded controls engineer, I need the CMG hardware to deliver strong, full-range physical stabilization so that the glove can mechanically counter tremor before any ML logic is layered on top. The gimbal servo must use its full safe mechanical travel, the flywheel must store enough angular momentum to produce meaningful reaction torque, and the PID output must translate into snappy, full-range gimbal motion instead of a barely-moving, "starved" actuator.

**Why this priority**: Physical stabilization authority is the foundation. No amount of ML accuracy matters if the actuator cannot produce counter-torque. This story is the prerequisite for every later phase and is independently demonstrable on the bench with no ML involved.

**Independent Test**: On the bench (flywheel + gimbal only, classifier forced fully engaged or bypassed), command a sweep of synthetic PID outputs and confirm the gimbal traverses its full configured pulse range linearly, the flywheel spins at the raised speed without a brownout/reset, and an induced disturbance produces a visibly stronger counter-motion than the pre-tuning baseline.

**Acceptance Scenarios**:

1. **Given** a full-scale negative-to-positive control command sweep, **When** the gimbal is driven, **Then** the servo pulse moves linearly across the full `MIN…MAX` range, reaching each clamp only at the corresponding ±1.0 command (no dead band in the upper/lower half of authority).
2. **Given** the flywheel is armed and commanded to its raised run speed at boot, **When** the device runs continuously, **Then** the flywheel sustains the higher speed with no flywheel-induced brownout, watchdog reset, or ESC re-arm.
3. **Given** a manually induced disturbance on the target tremor axis, **When** the tuned control loop responds, **Then** the gimbal produces a faster and larger corrective swing than the pre-tuning baseline, and settles without sustained buzzing against a mechanical stop.
4. **Given** a small disturbance, **When** the un-squashed control signal is applied, **Then** the gimbal produces a proportionate, perceptible response (the previously over-damped/"starved" behavior is gone).

---

### User Story 2 - Binary Classification Pivot & Data-Driven Parity Fix (Priority: P2)

As the engineer, I need the tremor classifier to be a clean two-class model (Tremor vs Non-Tremor) whose on-device behavior exactly matches its trained behavior, so that the device correctly reports Non-Tremor when at rest and Tremor when shaking. The `Voluntary` class is removed throughout. The current inversion symptom (Tremor reported while still) must be diagnosed against real recorded still-glove data and fixed at its true root cause (axis/sign/scaling/feature-order parity), not masked by relabeling.

**Why this priority**: A correct, trustworthy class signal is the prerequisite for proportional engagement (US3) and a meaningful retrain (US4). It is independently testable entirely in software.

**Independent Test**: Train the binary model in Python; run the same trained model and the C++/flat-array interpreter over the provided still-glove capture and over a known shaking capture; confirm both pipelines agree window-by-window and that still → Non-Tremor, shaking → Tremor.

**Acceptance Scenarios**:

1. **Given** the training pipeline, **When** it runs, **Then** it loads only the Non-Tremor (Control) and Tremor (Parkinson) groups, trains a binary objective, and produces a model whose classes are exactly `{0: Non-Tremor, 1: Tremor}` with no `Voluntary` class anywhere in the model, metadata, exporter, or firmware.
2. **Given** the provided still-glove capture, **When** the Python pipeline classifies its windows, **Then** the overwhelming majority are Non-Tremor with high confidence.
3. **Given** the same still-glove windows, **When** the C++/on-device interpreter classifies them, **Then** its per-window class and probability match the Python result within a small numeric tolerance (parity holds).
4. **Given** a detected disagreement between Python and C++ outputs, **When** the parity debug runs, **Then** it isolates the mismatch to a specific stage (raw axis order/sign/scale, band-pass output, a specific feature index, or the final score), and the documented fix makes still-glove data classify as Non-Tremor on-device.
5. **Given** the binary model, **When** it is exported to C, **Then** the on-device inference math reflects a two-class model correctly (single decision score → probability), with no leftover three-class softmax assumptions.

---

### User Story 3 - Proportional, Probability-Scaled Suppression (Priority: P3)

As the engineer, I want suppression strength to scale smoothly with the classifier's Tremor-class confidence, instead of a binary on/off gate, so that mild tremor gets gentle correction and strong tremor gets full authority, with no actuator chatter at the decision boundary.

**Why this priority**: It meaningfully improves stabilization quality and patient comfort, but depends on a trustworthy class signal (US2) and responsive hardware (US1).

**Independent Test**: Feed the control loop a synthetic, ramped Tremor probability (0 → 1 → 0) and confirm the suppression authority follows it smoothly within configured bounds, with no per-cycle toggling and a defined low-confidence floor.

**Acceptance Scenarios**:

1. **Given** a rising Tremor probability, **When** it crosses the engagement region, **Then** suppression authority increases smoothly and monotonically (no instantaneous jump from 0 to full).
2. **Given** a Tremor probability hovering near the decision boundary, **When** it fluctuates cycle-to-cycle, **Then** the actuator does not chatter (anti-chatter dwell/ramp behavior is preserved).
3. **Given** a low Tremor probability below the configured floor, **When** evaluated, **Then** suppression authority is held at neutral (no low-level dithering from noise).
4. **Given** a sustained high Tremor probability, **When** evaluated, **Then** suppression reaches full authority.

---

### User Story 4 - Unified Retrain & Deployment (Priority: P4)

As the engineer, I want a single training run to produce both the backend model and the ESP32 C arrays from one structural source of truth, so that the device and the backend never disagree about what the model is.

**Why this priority**: It is the deployment mechanic that locks the corrected binary model into both consumers consistently. It must come last because it propagates whatever US2 produces.

**Independent Test**: Run the training script once; confirm it emits the binary model artifact; run the C-export step against that artifact; confirm the firmware arrays regenerate; re-run the export and confirm byte-identical output; confirm the backend prediction path consumes the same artifact.

**Acceptance Scenarios**:

1. **Given** a single training run, **When** it completes, **Then** it produces exactly one binary model artifact consumed by both the backend and the C exporter (no separate, divergent models).
2. **Given** that artifact, **When** the C-export step runs, **Then** it regenerates the firmware model header/source as a two-class model and reports a two-class structure.
3. **Given** an unchanged artifact, **When** the C-export step is re-run, **Then** the generated firmware files are byte-identical to the previous run.
4. **Given** the regenerated firmware model, **When** the device runs, **Then** its classifications match the backend's classifications on identical input windows.

---

### Edge Cases

- **Flywheel over-speed / current spike**: raising flywheel speed and slew rate must not trigger a brownout, watchdog reset, or ESC desync. If it does, the run pulse / slew must be backed off to the highest stable value.
- **Gimbal hitting hard stops**: at the widened 600–2400 µs range, the gimbal must not command-and-hold against a mechanical stop (stall current, buzzing, gear wear). Transient excursions to the clamps are acceptable; sustained ones are not.
- **Classifier warm-up**: during band-pass / window warm-up after boot or calibration, the decision is invalid; suppression must default to safe (neutral) and never engage from an unknown state.
- **Two-class boundary noise**: a Tremor probability oscillating near the threshold must not produce actuator chatter.
- **Parity tolerance failure**: if Python and C++ outputs cannot be brought within tolerance, the discrepancy must be surfaced (not silently rounded away), because it indicates a remaining pipeline mismatch.
- **Stale telemetry**: the backend/dashboard must correctly render a two-class prediction (and a now-absent third class) without breaking existing consumers expecting three probabilities.

---

## Requirements *(mandatory)*

### Functional Requirements

**Hardware liberation & control tuning (US1)**

- **FR-001**: The gimbal control mapping MUST use the full safe mechanical pulse range such that a full-scale control command (±1.0) maps linearly to the configured pulse limits, with no portion of control authority clamped away before the extremes.
- **FR-002**: The gimbal half-swing (`SPAN`) MUST equal the distance from center to each clamp (target `SPAN = 900 µs` with center 1500, limits 600–2400) so the mapping is linear across full authority.
- **FR-003**: The flywheel run command MUST be raised to increase stored angular momentum and reaction-torque authority (target ~1200–1300 µs), set to the highest value that runs continuously without brownout/reset/ESC re-arm.
- **FR-004**: The PID-to-CMG signal MUST be "un-squashed" so the PID can command snappy, full-range gimbal motion — by lowering the torque full-scale normalizer and increasing the torque slew-rate limit — while remaining within current/brownout-safe bounds.
- **FR-005**: The control law MAY be refactored to translate gyro error into gimbal torque more effectively, provided behavior remains stable (no sustained oscillation or stop-banging) and the sensor-to-actuation latency budget is preserved.

**Binary classification pivot & parity (US2)**

- **FR-006**: The training pipeline MUST classify only two classes — `0 = Non-Tremor`, `1 = Tremor` — using a binary objective, and MUST NOT load, train on, or emit a `Voluntary` class.
- **FR-007**: The class mapping `Tremor = 1`, `Non-Tremor = 0` MUST be consistent and locked across the training pipeline, the model metadata, the C exporter, and the on-device classifier.
- **FR-008**: The model export MUST produce a firmware model that reflects a two-class structure, and the on-device interpreter MUST compute its decision with the correct binary inference math (single decision score → probability), with no residual three-class assumptions.
- **FR-009**: The system MUST include a data-driven parity procedure that compares the Python feature/inference pipeline against the C++ on-device pipeline using the provided still-glove capture (and a shaking capture), reporting agreement per window.
- **FR-010**: When the parity procedure detects a discrepancy, it MUST localize the root cause to a specific stage — raw axis order, axis sign, unit/scale, feature index/order, band-pass output, or final score — and the implemented fix MUST make still-glove data classify as Non-Tremor on-device.
- **FR-011**: The raw IMU axis order, sign, and units consumed on-device MUST match those used to train the model (reference: capture columns `aX, aY, aZ, gX, gY, gZ`; accel in m/s², gyro in deg/s).

**Proportional suppression (US3)**

- **FR-012**: Suppression authority MUST scale continuously with the Tremor-class probability rather than a binary on/off decision.
- **FR-013**: Suppression MUST retain anti-chatter behavior (minimum dwell and/or authority ramp) so a probability fluctuating near the boundary does not toggle actuators per cycle.
- **FR-014**: Suppression MUST apply a low-confidence floor below which authority stays neutral, preventing dithering from classifier noise, and reach full authority under sustained high confidence.
- **FR-015**: During invalid/warm-up decisions, suppression MUST default to neutral (safe) and never engage from an unknown state.

**Unified retrain & deployment (US4)**

- **FR-016**: A single training run MUST produce exactly one model artifact that is the shared source of truth for both the backend prediction path and the firmware C export.
- **FR-017**: The C-export step MUST regenerate the firmware model files from that single artifact and MUST be deterministic (byte-identical output on re-run against an unchanged artifact).
- **FR-018**: The backend prediction path and the on-device classifier MUST agree on identical input windows after the unified retrain.
- **FR-019**: Existing telemetry/dashboard consumers MUST continue to function with a two-class prediction (the previously third probability is removed/handled gracefully).

**Process gate**

- **FR-020**: Phases MUST be executed in order (Hardware → Binary pivot + parity → Proportional engagement → Unified retrain), each conceptually resolved before the next; the binary-model retrain (US4) MUST follow a verified parity fix (US2).

### Key Entities *(include if feature involves data)*

- **CMG actuation profile**: The set of physical drive parameters — gimbal center, half-swing span, min/max pulse clamps, flywheel run command, torque full-scale normalizer, torque slew-rate limit — that determine stabilization authority and responsiveness.
- **PID control law**: The error→output relationship driving the gimbal from the target-axis gyro rate (setpoint = 0), including gains and any refactored error-to-torque translation.
- **Binary tremor model**: A two-class (Non-Tremor=0 / Tremor=1) classifier expressed as a single shared artifact, transpiled into a firmware-resident form for on-device inference.
- **Suppression authority signal**: A smoothed `[0,1]` value derived from Tremor probability that scales the control output, with floor, ramp, and anti-chatter behavior.
- **Parity reference captures**: Real ESP32-recorded IMU datasets (still-glove provided; shaking to be used) used to verify Python↔C++ pipeline agreement and diagnose mismatches.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full-scale control command sweep drives the gimbal across its full configured pulse range linearly, with each clamp reached only at the corresponding ±1.0 command (zero dead authority in either half).
- **SC-002**: The flywheel sustains its raised run speed indefinitely with zero brownouts, watchdog resets, or ESC re-arms over a continuous 10-minute run.
- **SC-003**: For a manually induced disturbance, the tuned system produces a visibly larger/faster corrective gimbal response than the pre-tuning baseline, with no sustained buzzing against a stop.
- **SC-004**: With the parity fix in place, ≥95% of still-glove windows classify as Non-Tremor on-device, and induced shaking classifies as Tremor.
- **SC-005**: Python and C++ pipelines agree on ≥99% of windows over the reference captures (class match), with probability differences within a small defined tolerance.
- **SC-006**: No `Voluntary` class remains anywhere across training, metadata, export, firmware, or telemetry.
- **SC-007**: Suppression authority tracks a ramped Tremor-probability input smoothly and monotonically through the engagement region, with zero per-cycle actuator toggling at the boundary and neutral output below the confidence floor.
- **SC-008**: One training run yields a single shared model artifact; re-running the C export against it produces byte-identical firmware files.
- **SC-009**: The backend prediction path and the on-device classifier produce identical classes on the same input windows after the unified retrain.

## Assumptions

- The MG90s can safely traverse 600–2400 µs without binding; if bench testing reveals binding, the clamps are tightened to the verified safe range.
- The provided still-glove capture (`stable_glove_data_20260620_215329.csv`, columns `Timestamp, aX, aY, aZ, gX, gY, gZ`, accel in m/s² with aZ≈9.8 g at rest, gyro in deg/s≈0 at rest) is representative of true rest and suitable as a Non-Tremor parity reference. A shaking/Tremor reference capture will be used similarly.
- The existing band-pass / windowing / 66-feature pipeline and its Python↔C++ sharing mechanism remain the basis; the pivot changes the number of classes and inference head, not the feature set, unless parity debugging proves a feature-level mismatch.
- Development is local-only (bench + local backend); no production deployment or containerization is in scope.
- The "raise flywheel" and "un-squash signal" magnitudes are tuned empirically on the bench within brownout-safe limits; the numeric targets in this spec are starting points, not hard contractual values.

## Dependencies

- A representative **shaking/Tremor reference capture** (counterpart to the provided still capture) is needed to fully validate FR-009/FR-010 and SC-004/SC-005.
- Bench access to the assembled CMG (flywheel ESC + gimbal servo + IMU) is required to validate US1 (FR-001…FR-005) and the parity captures.
- The user will confirm the raw parity data set and grant go-ahead before implementation execution begins (per the agreed review gate).

## Out of Scope

- Any retention of, or migration path for, the `Voluntary` class.
- Backend/dashboard redesign beyond gracefully handling a two-class prediction.
- Production deployment, CI/CD, or containerization.
- Changes to the IMU sampling rate, Kalman fusion, or MQTT transport, except where the parity debug proves an axis/sign/scale defect originating there.
