# Phase 1 Data Model: Hardware-First Stabilization & Binary Tremor Pivot

This feature is firmware/ML-centric; there are **no new database tables or Django models**. The
"entities" here are configuration structures, model artifacts, and in-memory signals. Validation
rules are derived from the functional requirements.

---

## 1. CMG Actuation Profile (`firmware/include/config.h`)

The set of compile-time constants defining gimbal mapping, flywheel speed, and torque shaping.

| Field | Current | New (target) | Validation / Rule | FR |
|-------|---------|--------------|-------------------|----|
| `CMG_GIMBAL_CENTER_US` | 1500 | 1500 | neutral pulse | FR-001 |
| `CMG_GIMBAL_TRIM_US` | 0 | 0 (±100 max) | small mechanical neutral shift | FR-001 |
| `CMG_GIMBAL_SPAN_US` | 600 | **900** | MUST equal `CENTER − MIN` = `MAX − CENTER` (linear full range) | FR-002 |
| `CMG_GIMBAL_MIN_US` | 900 | **600** | hard clamp ≥ servo-safe min; reachable only at torque −1.0 | FR-001 |
| `CMG_GIMBAL_MAX_US` | 2100 | **2400** | hard clamp ≤ servo-safe max; reachable only at torque +1.0 | FR-001 |
| `CMG_ESC_RUN_PULSE_US` | 1080 | **~1200–1300** | > arm pulse; highest value with no brownout/reset/re-arm | FR-003 |
| `CMG_ESC_ARM_PULSE_US` | 1000 | 1000 | unchanged arm/idle | FR-003 |
| `CMG_TORQUE_FULL_SCALE` | 160.0 | **↓ (~60–90)** | > 0; smaller → snappier saturation | FR-004 |
| `CMG_TORQUE_SLEW_PER_S` | 40.0 | **↑ (~120–200)** | > 0; larger → faster swing, brownout-bounded | FR-004 |
| `CONTROL_LOOP_DT_S` | 0.005 | 0.005 | matches 200 Hz ControlTask | — |

**Invariant**: `MIN_US ≤ CENTER_US − SPAN_US` and `CENTER_US + SPAN_US ≤ MAX_US` must hold so the
clamp is only reached at exactly ±1.0 torque (no dead authority). With 600/1500/2400/900 this is an
equality (ideal).

## 2. PID Control Law (`firmware/include/config.h`, `pid_controller.cpp`)

| Field | Current | New | Rule | FR |
|-------|---------|-----|------|----|
| `PID_KP` | 2.0 | bench-tuned | proportional gain | FR-004/005 |
| `PID_KI` | 0.0 | 0.0 (unless tuning needs) | integral (anti-windup clamped) | FR-005 |
| `PID_KD` | 0.05 | bench-tuned | derivative; may gain a 1-pole IIR if D-noise grows | FR-005 |
| `PID_INTEGRAL_CLAMP` | 100.0 | unchanged | anti-windup hard clamp | FR-005 |

State (`PidController`): `Kp, Ki, Kd, dt, setpoint(=0), integral, prev_error`. Behavior must remain
stable (no sustained oscillation, no stop-banging); latency budget < 70 ms preserved.

## 3. Binary Tremor Model (artifact + firmware port)

Single shared artifact `backend/ml_models/lgbm_tremor_model.pkl` (+ `.json` metadata), transpiled to
`firmware/include/tremor_model.h` + `src/tremor_model.cpp`.

| Field | 3-class (current) | Binary (new) | Rule | FR |
|-------|-------------------|--------------|------|----|
| classes | `{0:Non-Tremor,1:Tremor,2:Voluntary}` | `{0:Non-Tremor,1:Tremor}` | Tremor MUST = 1 | FR-006/007 |
| objective | multiclass | `binary` | LightGBM binary | FR-006 |
| `num_class` (dump) | 3 | 1 (single tree series) | exporter MUST accept 1 | FR-008 |
| `NUM_TREES` | 900 | ≈300 (= n_estimators) | round-robin degenerates to 1 output | FR-008 |
| raw→proba | softmax over 3 | `sigmoid(init + Σleaf)` | exact-parity w/ `predict_proba` | FR-008 |
| `init_score` | `[0,0,0]` | model base/init score (scalar) | MUST be emitted for parity | FR-008 |
| feature set | 66, axis-major | 66, axis-major (unchanged) | order == `get_feature_names_66()` | FR-011 |

**Validation**: re-export on unchanged `.pkl` is byte-identical (SC-008). No `Voluntary`/`proba[2]`
references survive anywhere (SC-006).

## 4. On-Device Decision (`firmware/include/classifier.h`)

| Field | Current | New | Rule |
|-------|---------|-----|------|
| `TremorClass` | `{NON_TREMOR=0,TREMOR=1,VOLUNTARY=2}` | `{NON_TREMOR=0,TREMOR=1}` | static_assert mapping not inverted |
| `Decision.proba` | `float[3]` | `float[2]` | `proba[0]=1−p`, `proba[1]=p_tremor` |
| `Decision.cls` | argmax(3) | `p≥0.5 ? TREMOR : NON_TREMOR` | — |
| `Decision.valid` | bool | bool | false during warm-up (safe default) |

## 5. Suppression Authority Signal (`suppression_gate.cpp`, `edge_config.h`)

Smoothed `[0,1]` value scaling the PID output, now driven by Tremor probability.

| Field | Current | New | Rule | FR |
|-------|---------|-----|------|----|
| authority source | majority vote → binary target | `clamp((p−P_LO)/(P_HI−P_LO),0,1)` | continuous in p | FR-012 |
| `GATE_P_LO` (new) | — | ~0.5 | floor: below → target 0 (no dither) | FR-014 |
| `GATE_P_HI` (new) | — | ~0.9 | ceiling: at/above → full authority | FR-014 |
| `GATE_RAMP_PER_S` | 2.0 | retained | smooth, monotonic ramp (no jumps) | FR-013 |
| `GATE_MIN_DWELL_MS` | 400 | retained/tuned | anti-chatter | FR-013 |
| `EDGE_GATE_ENABLED` | true | true | false → legacy always-on rollback | FR-015 |
| warm-up/invalid | target 0 | target 0 | never engage from unknown | FR-015 |

**State transition (authority target)**: `invalid → 0`; `valid & p<P_LO → 0`; `valid & p>P_HI → 1`;
else linear interpolation. Actual authority ramps toward target at `GATE_RAMP_PER_S`, dwell-gated.

## 6. Parity Reference Captures (data files)

| Field | Value | Rule |
|-------|-------|------|
| columns | `Timestamp, aX, aY, aZ, gX, gY, gZ` | order == on-device stream + `SIGNAL_COLS` |
| accel units | m/s² (aZ≈9.8 at rest) | MUST match training units (verify; ×9.8 if g-based) |
| gyro units | deg/s (≈0 at rest) | MUST match training units |
| still capture | `stable_glove_data_20260620_215329.csv` (~33 Hz) | Non-Tremor reference; rate-limited fidelity |
| shaking capture | _dependency_ | Tremor reference (counterpart) |
| 100 Hz capture | _dependency (preferred)_ | faithful rate parity vs device's 100 Hz stream |

**Validation outcomes**: still → ≥95% Non-Tremor on-device (SC-004); Python↔C agreement ≥99%,
`max|Δproba|<1e-3` (SC-005).
