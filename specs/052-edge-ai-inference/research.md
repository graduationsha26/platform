# Research: On-Device Edge AI Tremor Classification

Phase 0 decisions. Each entry: **Decision / Rationale / Alternatives**. Firmware facts are from
the firmware investigation (see plan.md Technical Context); external-tool facts are cited.

---

## 1. Sample rate, window length, and FFT size

**Decision**: Operate the edge pipeline at the device's **native 100 Hz**, with an analysis
**window of 128 samples (1.28 s)** and a **128-point FFT**. Retrain the reference model at this
rate/window. Refresh the decision every **10 samples (~100 ms)**.

**Rationale**:
- The IMU truly samples at 100 Hz on-device (the 30 Hz was only the MQTT transmit rate), so
  100 Hz native means **zero on-device resampling** — the biggest latency/complexity win.
- esp-dsp's fast FFT is **radix-2 (power-of-2 only)**; 128 is the natural power-of-2 covering a
  1-second-ish window at 100 Hz. Using window length == FFT length (128) means the Python
  reference (`np.fft.rfft` on 128 samples) and the device FFT share **identical frequency bins**
  (`k·100/128` Hz) → exact peak-frequency parity. (Mixing a 100-sample window with a 128-point
  zero-padded FFT would shift bins and break parity unless padded identically on both sides;
  128/128 avoids the ambiguity entirely.)
- 128-pt FFT ≈ **43 µs** on ESP32 @240 MHz — negligible against the 100 ms cadence.

**Alternatives**:
- *Keep 66.67 Hz, decimate 100→66.67 on-device*: rejected — non-integer resample on an MCU for
  no benefit.
- *100-sample window zero-padded to 128 for the FFT*: workable if both hosts pad identically, but
  128/128 is cleaner and removes a parity foot-gun.
- *arduinoFFT*: rejected (pure-C, slower, FFT-only — no biquads).

> Cost: a one-time retrain (pinned params) at the new rate/window; the backend feature
> definition realigns to 100 Hz/128 so both hosts stay identical (FR-012). Gated on user approval.

---

## 2. Band-pass filter and exact parity

**Decision**: Design the 0.5–20 Hz 4th-order Butterworth band-pass **offline in scipy as SOS**
(`butter(4, [0.5,20]/nyq, btype='band', output='sos')`), hardcode the SOS coefficients into the
firmware, and apply them with esp-dsp `dsps_biquad_f32` as a **cascade of biquads**. The filter
is **re-applied over the buffered 128-sample window from zero initial state every cycle** — not
streamed continuously — so it matches the Python reference applying the same filter per window.

**Primary**: causal single-pass `sosfilt` (forward only) in both reference and device.
**Fallback**: `filtfilt` (zero-phase) over the window if causal retraining loses accuracy —
also exactly reproducible on-device because we already re-filter the fixed window each cycle
(forward then reverse, replicating scipy's odd-padding/`padlen`).

**Rationale**:
- Re-filtering the 128-sample window from zero state is the **parity-critical** insight: a
  continuously-streamed filter would carry state across windows that the per-window Python
  reference does not have, causing drift at window edges. Per-window re-filter from zero state =
  identical inputs to identical math = identical features. Cost is trivial (128×6×~2 biquad
  sections ≈ a few µs).
- esp-dsp's built-in coefficient generators are **RBJ cookbook-Q biquads, not Butterworth**, so
  the precise band requires scipy-designed SOS hardcoded and fed to `dsps_biquad_f32`
  (`coef = {b0,b1,b2,a1,a2}`, 2-float state per section).
- Causal first because it's the simplest C with no padding subtleties; the retrain lets the model
  learn on causally-filtered features so parity is exact. filtfilt kept as a documented fallback
  for accuracy (SC-005), and it's still achievable because we operate on a fixed window.

**Alternatives**:
- *Continuous streaming biquad*: rejected for the cross-window state-drift parity problem above.
- *esp-dsp `dsps_biquad_gen_bpf0db_f32`*: rejected as the design source — cookbook-Q ≠ the
  validated Butterworth response; would change features vs the trained model.

---

## 3. FFT magnitude and spectral features

**Decision**: Use esp-dsp radix-2 real FFT on the 128-sample (mean-removed) window:
`dsps_fft2r_init_fc32` (once) → pack interleaved complex → `dsps_fft2r_fc32` → `dsps_bit_rev_fc32`
→ recover real spectrum → compute magnitude `sqrtf(re²+im²)` only for bins in 0.5–20 Hz, then take
the **top-2 magnitudes** and their frequencies (matching `_fft_top2`: DC removed, band mask,
descending sort, top-2 freq+amp).

**Rationale**: DFT is implementation-independent, so esp-dsp magnitudes match `np.fft.rfft`
magnitudes within float tolerance given the same length/window. We only need magnitudes for the
~`0.5..20 Hz` bins (≈ bins 1..26 of 65), so compute `sqrtf` selectively (the LX6 FPU does mul/add
in hardware but `sqrt`/division in software).

**Parity caveats**:
- Compute the band mask with the same inclusive bounds (`>=0.5 & <=20.0`) and the same `rfftfreq`
  spacing (`fs/N`).
- For the top-2 selection, ties are essentially impossible in float; tolerance covers any
  sort-order ambiguity. Validate in the harness.

**Alternatives**: *Goertzel per bin* (cheaper if only a few bins mattered) — rejected; we need the
argmax over the whole band, FFT is simplest and fast enough. *esp-dsp `fft4r` real path* — slightly
faster; acceptable optimization but `fft2r` is simpler to reason about for parity (revisit if CPU-bound).

---

## 4. Statistical-feature parity details

**Decision**: Replicate NumPy semantics exactly in C for the 7 per-axis statistics:
- `mean`, `min`, `max`: direct.
- `std`: **population** std (`ddof=0`, NumPy default).
- `median`: average of the two middle order statistics for even n (n=128 → mean of ranks 63,64).
- `q1`/`q3`: NumPy **linear interpolation** percentile (default `method='linear'`) — sort, then
  interpolate between ranks `(n-1)·p`. Must match NumPy's interpolation, not a nearest-rank quantile.

**Rationale**: q1/q3/median require sorting the 128-sample window (cheap); the only correctness
risk is the percentile interpolation convention, which must mirror NumPy's default to hit the
SC-006 tolerance.

**Alternatives**: nearest-rank quantiles — rejected (would diverge from the trained features).

---

## 5. Model transpilation: LightGBM → C

**Decision**: Generate a **flat-array tree interpreter** from the trained booster, via a new
`backend/ml_models/export_to_c.py`:
- Load the pickle, take `pipe.named_steps['clf'].booster_`, call `dump_model()`.
- Emit `firmware/include/tremor_model.h` + `firmware/src/tremor_model.cpp` with per-node arrays
  (`feature[]` int16 / `-1` for leaf, `threshold[]` float32, `left[]`/`right[]` int32,
  `default_left[]` uint8, `leaf_value[]` float32), tree→class round-robin metadata, and
  `NUM_CLASS=3`, `NUM_ITER`.
- A generic iterative traversal: at each internal node go **left iff `x[feature] <= threshold`**
  (LightGBM numerical default), else right; honor `default_left` for non-finite inputs (defensive).
- Prediction: sum `leaf_value` per class over trees with `tree_index % 3 == c` → raw scores →
  **softmax (subtract max for stability)** → `proba[3]`; `argmax` = class.

**Rationale** (all confirmed in research):
- LightGBM multiclass grows **one tree per class per round**, laid out **round-robin**: tree `i`
  → class `i % num_class`. With `n_estimators=300` that's ~**900 sub-trees** (~300/class).
- Numerical split goes **left on `<=`** (using `<` would mismatch on boundary values).
- Our pipeline has **no scaler** (only SMOTE, which is train-time only and ignored at inference)
  and **only numeric features** (no categorical `==`/bitset splits) — the exporter asserts both.
- A flat-array interpreter is **smallest flash (tens–low-hundreds of KB), fastest, instantly
  compilable, and trivially regenerable** from the `.pkl` — versus m2cgen's monolithic unrolled
  `if/else` function (RecursionError risk at ~900 trees, slow compile, float64-only).
- float32 thresholds/leaf values are fine on the LX6 FPU; validate argmax/proba vs the float64
  Python model.

**Cross-check**: run **m2cgen** once (raise `sys.setrecursionlimit`) and diff its `output[]`
against the interpreter on sample inputs to confirm operator/layout/softmax handling — then ship
the interpreter, not m2cgen output.

**Alternatives**:
- *m2cgen as shipped artifact*: rejected — monolithic function, compile blowup, float64.
- *treelite/TL2cgen*: rejected — treelite dropped C codegen; TL2cgen isn't MCU-tuned (hosted,
  double-precision).
- *emlearn / micromlgen*: rejected — neither supports LightGBM (sklearn-trees / XGBoost only).

**Size reduction levers** (apply only if footprint requires AND SC-005 parity holds): reduce
`n_estimators` 300→~150, cap `max_depth`, quantize thresholds/leaves to int16. Expected
**unnecessary** at our flash budget, but available.

---

## 6. Classification task placement & cadence

**Decision**: Add a dedicated **`ClassificationTask` pinned to Core 0** (alongside the 30 Hz
MqttTask), running every ~100 ms: snapshot the ring buffer → band-pass(window) → 66 features →
interpreter → softmax → `Decision` → feed the gate.

**Rationale**: Core 1 is saturated (100 Hz SensorTask + 200 Hz ControlTask with a <70 ms
sensor→actuation hard budget). Putting inference on Core 0 keeps it **off the real-time control
path** (SC-003/SC-007). One cycle (≈ filter + 43 µs FFT×6 + sort×6 + ~900-tree traversal) is well
under 100 ms with large margin.

**Alternatives**: *inference inside SensorTask/ControlTask on Core 1* — rejected (jeopardizes the
control deadline). *Every-sample feature recompute* — rejected (wasteful; 100 ms hop meets SC-002).

---

## 7. Suppression gate smoothing (FR-003b / SC-009)

**Decision**: A **4-state gate** (`DISENGAGED → ENGAGING → ENGAGED → DISENGAGING`) driven by a
**sliding-window vote with hysteresis and a minimum dwell time**:
- Keep the last `N_VOTE` decisions (e.g., 5 ≈ 500 ms).
- **Engage** only when ≥ `ENGAGE_VOTES` of the recent window are `TREMOR` (e.g., 4/5).
- **Disengage** only when ≥ `DISENGAGE_VOTES` are non-`TREMOR`, with `DISENGAGE_VOTES`
  set so it won't immediately flip back (asymmetric hysteresis).
- Enforce a **minimum dwell** (e.g., ≥300–500 ms) before any further state change, so alternating
  borderline windows cannot toggle actuators per cycle.
- Optional **authority ramp** on engage/disengage so PID effort changes smoothly, not as a step.
- **Default-safe**: on `Decision.valid == false` (warm-up/invalid window) the gate never engages
  from unknown; an engaged gate moves to a controlled `DISENGAGING` only after a timeout.

**Rationale**: The classifier can oscillate at class boundaries; raw per-cycle gating (10 Hz)
would chatter the gimbal servo/ESC. Vote + hysteresis + dwell + ramp make transitions safe and
smooth (the user's explicit hardware-safety requirement). The PID **control law is unchanged** —
only whether/with-what-authority it is engaged.

**Alternatives**: *Single-sample threshold gate* — rejected (chatter). *Fixed long debounce only*
— rejected (sluggish engage on real tremor); the asymmetric vote engages fast on sustained tremor
while resisting spurious disengage.

**Open tuning** (defer to implementation/bench): exact `N_VOTE`, `ENGAGE_VOTES`,
`DISENGAGE_VOTES`, dwell ms, ramp profile — tuned on-bench; SC-009 verifies no per-cycle chatter.

---

## 8. Numeric type and tolerances

**Decision**: **float32** everywhere on-device (LX6 hardware FPU). Parity tolerances validated by
the host harness: per-feature relative/absolute tolerance for SC-006 (e.g., `atol≈1e-3`,
`rtol≈1e-3`, tuned during harness bring-up), and ≥95% class agreement + within-tolerance raw
scores for SC-005.

**Rationale**: The FPU makes float32 fast; the model is float64 in Python but argmax is virtually
always identical and probability drift is tiny. Avoid per-sample division/`sqrt` where possible
(software-emulated on LX6).

**Alternatives**: *fixed-point int16* — rejected (no benefit with an FPU; adds quantization error).
*float64 on-device* — rejected (no FP64 hardware; slower, larger).

---

## 9. Footprint (to verify at build)

**Estimate**: esp-dsp linked code a few KB–~10 KB; FFT twiddle table ~512 B (N=128) + ~1 KB
working buffer; flat-array model tens–low-hundreds of KB flash; ring buffer 128×6×4 B = 3 KB.
All comfortably within ~3.2 MB free flash / ~480 KB free RAM. **Measured** via `pio run -v` /
linker map at integration (SC-007); estimates are not a substitute for the build report.

---

## 10. Backend alignment (records remain authoritative — FR-012)

**Decision**: `features_lgbm.py`/`train.py` realign to 100 Hz / 128-window / same filter, so the
backend `inference` path and the device compute identical features and use the identical class
mapping; the backend stays the **system of record** while the device drives only local suppression.

**Rationale**: Single source of truth for feature definition + mapping prevents the two hosts from
drifting (FR-012). The export tool derives the C model purely from the trained `.pkl`.

---

## Resolved unknowns

| Unknown | Resolution |
|---------|-----------|
| Native rate / window / FFT size | 100 Hz, 128-sample window, 128-pt radix-2 FFT; retrain |
| Filter parity strategy | Per-window re-filter from zero state; scipy-SOS Butterworth into esp-dsp biquads; causal primary, filtfilt fallback |
| DSP library | esp-dsp (`lib_deps = espressif/esp-dsp`) over arduinoFFT |
| Transpilation method | Flat-array interpreter from `dump_model()`; m2cgen as oracle only |
| Multiclass tree layout | round-robin, tree `i` → class `i % 3`; sum leaves/class → softmax |
| Split operator | `x <= threshold` → left |
| Scaler / categorical | none / none (asserted by exporter) |
| Numeric type | float32 (hardware FPU) |
| Task placement | dedicated ClassificationTask on Core 0, ~100 ms |
| Gate smoothing | vote + asymmetric hysteresis + min dwell + ramp; default-safe on invalid |
