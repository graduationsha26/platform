# Contract: Data-Driven Parity Procedure (US2)

Defines how Python (`features_lgbm` + `predict_proba`) and C++ (`edge_features.cpp` + interpreter)
are compared on identical raw IMU data to find and fix the "predicts Tremor when still" defect.
Extends `backend/ml_models/parity_harness.py`.

## Layers
- **Layer A — model parity** (existing, no compiler): flat-array interpreter vs `predict_proba` on
  feature rows from `combined_processed_data.csv`. Extended to the binary sigmoid head (see
  binary-model-export-format.md). Gate: agreement ≥99%, `max|Δproba| < 1e-3`.
- **Layer B — DSP/C parity** (needs host C++ compiler): compile `edge_features.cpp` +
  `tremor_model.cpp` + `classifier.cpp` + a shim; compare C features/predictions to Python on the
  same windows.
- **Layer C — raw-capture parity** (NEW): drive both pipelines from a recorded raw IMU CSV and
  compare end-to-end, plus assert the expected verdict (still → Non-Tremor).

## Layer C inputs
| Capture | Path | Rate | Expected verdict |
|---------|------|------|------------------|
| Still | `stable_glove_data_20260620_215329.csv` | ~33 Hz (telemetry) | Non-Tremor ≥95% windows |
| Shaking | _dependency_ | — | Tremor (majority) |
| 100 Hz raw | _dependency (preferred)_ | 100 Hz | faithful device-rate parity |

CSV columns: `Timestamp, aX, aY, aZ, gX, gY, gZ` (accel m/s², gyro deg/s).

## Bisection order (stop at first divergence; that is the root cause)
1. **Raw alignment** — axis order `aX,aY,aZ,gX,gY,gZ`; per-axis sign; **unit scale (g vs m/s²)**.
   Highest-prior suspect: a ×9.8 scale on accel scales all amplitude features.
2. **Sample rate** — capture is 33 Hz vs device 100 Hz; resample deterministically or use a 100 Hz
   capture. For the still case, low-frequency content tolerates the gap.
3. **Band-pass** — Python causal `sosfilt` vs C++ biquad cascade, element-wise on the same window.
4. **Features** — all 66 values Python vs C++; report the first divergent feature index/axis.
5. **Score** — raw margin and `p_tremor` Python vs C++.

## Outputs
- A localized root-cause statement naming the divergent stage (FR-010).
- The implemented fix (in raw handling, units, rate, filter, features, or export) that makes
  still-glove data classify Non-Tremor on-device (SC-004) and brings Python↔C agreement ≥99% (SC-005).

## Acceptance
- Layer A binary parity passes.
- Layer C still-capture verdict: Non-Tremor ≥95% of windows on-device.
- Documented mismatch + fix (no relabeling shortcut). [FR-009, FR-010]
