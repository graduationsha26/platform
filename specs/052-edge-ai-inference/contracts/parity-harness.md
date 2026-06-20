# Contract: Host Parity Harness (`test_edge_parity.py`)

The gate that MUST be green before any firmware integration. Proves the C++ port computes the
same features and the same predictions as the Python reference, on the host.

## What it compiles

- `firmware/src/edge_features.cpp` (DSP + 66 features) and `firmware/src/tremor_model.cpp`
  (generated interpreter), built for the **host** (native compiler or a small C harness exe),
  exposing two entry points usable from Python (via subprocess/ctypes/cffi):
  - `extract_features(window[128][6]) -> float[66]`
  - `predict(features[66]) -> {class:int, proba:float[3]}`

## Inputs

- A held-out set of 128-sample, 6-axis windows drawn from `combined_processed_data.csv`'s source
  recordings (raw windows, pre-feature), covering all three classes — including a known clean
  tremor window and a known resting window.

## Checks & thresholds

| ID | Check | Pass condition |
|----|-------|----------------|
| P1 (SC-006) | Feature parity | For every window, every one of 66 C features matches the Python `extract_features_66` value within `atol`/`rtol` (bring-up target `1e-3`) |
| P2 (SC-005) | Decision agreement | C `argmax` == Python model `argmax` on ≥95% of windows |
| P3 (SC-005) | Probability parity | Per-class `proba` within tolerance of Python `predict_proba` |
| P4 (SC-001) | Mapping | Known tremor window → class 1; known resting window → class 0 |
| P5 | m2cgen oracle | Interpreter `proba` matches m2cgen `output[]` within tolerance on sample inputs |
| P6 (SC-008) | Reproducibility | Re-running `export_to_c.py` yields byte-identical `tremor_model.*` |

## Notes

- The harness feeds the **same raw windows** to both paths and applies the **same band-pass /
  window / FFT length** on both sides (the realigned `features_lgbm.py` is the Python reference).
- Float32 (C) vs float64 (Python) drift is expected and covered by tolerance; argmax must still
  agree at the P2 rate.
- Runs under `pytest backend/tests/test_edge_parity.py`; CI is out of scope (local only).
