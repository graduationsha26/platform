# Contract: On-Device Edge Classifier API (firmware C++)

Defines the firmware-internal interfaces. These are the stable seams; signatures may be refined
in implementation but the semantics below are the contract.

## Constants (config.h)

| Name | Value | Meaning |
|------|-------|---------|
| `EDGE_FS_HZ` | 100 | native IMU rate (no resampling) |
| `EDGE_WINDOW_SIZE` | 128 | samples per analysis window (1.28 s) |
| `EDGE_FFT_SIZE` | 128 | radix-2 FFT length (== window) |
| `EDGE_HOP` | 10 | samples between decisions (~100 ms) |
| `EDGE_N_FEATURES` | 66 | feature vector length |
| `EDGE_N_CLASS` | 3 | Non-Tremor / Tremor / Voluntary |
| `GATE_N_VOTE` | (tuned) | votes in the sliding gate window |
| `GATE_ENGAGE_VOTES` | (tuned) | TREMOR votes to engage |
| `GATE_DISENGAGE_VOTES` | (tuned) | non-TREMOR votes to disengage (asymmetric) |
| `GATE_MIN_DWELL_MS` | (tuned) | minimum time between gate state changes |
| `EDGE_GATE_ENABLED` | true | rollback flag → false reverts to always-on suppression |

## Types

```cpp
enum class TremorClass : uint8_t { NON_TREMOR = 0, TREMOR = 1, VOLUNTARY = 2 };
static_assert((uint8_t)TremorClass::TREMOR == 1, "canonical mapping must not invert");

struct Decision {
  TremorClass cls;
  float proba[EDGE_N_CLASS];   // softmax, sums ~1.0
  uint32_t t_decision_us;
  bool valid;                  // false during warm-up / invalid window
};
```

## Feature extraction — `edge_features.h`

```cpp
// Push one calibrated sample into the per-axis ring buffer (called by SensorTask, 100 Hz).
void edge_push_sample(float ax, float ay, float az, float gx, float gy, float gz);

// True once EDGE_WINDOW_SIZE samples have been collected (warm-up gate, FR-011).
bool edge_window_ready();

// Snapshot the current window, band-pass (from zero state), extract the 66 features.
// Returns false if the window is invalid (non-finite / out-of-range) → caller withholds decision.
// `out` is axis-major, order == get_feature_names_66(). (FR-005/FR-006)
bool edge_extract_features(float out[EDGE_N_FEATURES]);
```

**Contract**: `out[i]` equals the Python reference feature `i` within the SC-006 tolerance for
identical window contents. Band-pass uses the hardcoded scipy-designed Butterworth SOS, re-applied
over the buffered window from zero initial state.

## Classification — `classifier.h`

```cpp
// Run the flat-array interpreter on a feature vector → softmax probabilities + class.
Decision classify_features(const float feat[EDGE_N_FEATURES]);

// Convenience: ready? -> extract -> classify; sets Decision.valid accordingly.
Decision classify_current_window();
```

**Contract**: `classify_features` produces `argmax`/`proba` matching the Python model on the same
features per SC-005. Class index maps via `TremorClass` with no inversion (SC-001).

## Suppression gate — `suppression_gate.h`

```cpp
enum class Gate : uint8_t { DISENGAGED, ENGAGING, ENGAGED, DISENGAGING };

// Feed each new decision (called by ClassificationTask). Updates the vote/hysteresis state machine.
void gate_update(const Decision& d, uint32_t now_us);

// Read by ControlTask (200 Hz): is suppression authorized, and at what authority [0..1] (ramp).
bool  gate_suppression_active();
float gate_authority();          // 0.0 disengaged .. 1.0 fully engaged (smooth ramp)
Gate  gate_state();
```

**Contract (FR-003a/FR-003b, SC-009)**:
- Suppression authorized **only** when the gate reflects sustained `TREMOR` (vote ≥ engage
  threshold). Disengages on sustained non-`TREMOR` (asymmetric).
- State changes no more often than `GATE_MIN_DWELL_MS` → no per-cycle actuator chatter under
  alternating borderline decisions.
- `Decision.valid == false` never engages from a disengaged/unknown state; an engaged gate only
  leaves `ENGAGED` via a controlled `DISENGAGING` after timeout (default-safe).
- `EDGE_GATE_ENABLED == false` → `gate_suppression_active()` always true (legacy always-on) for
  rollback.

## ControlTask integration (pid_controller.cpp)

`ControlTask` keeps its existing PID law but multiplies the actuator command by
`gate_authority()` (and/or holds neutral when `!gate_suppression_active()`), so the classifier
gates *whether/how-much* to suppress without changing the control math.
