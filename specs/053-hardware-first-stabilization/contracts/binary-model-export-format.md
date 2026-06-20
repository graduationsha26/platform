# Contract: Binary Model Export Format (US2, US4)

Defines the structural contract between `backend/ml_models/export_to_c.py`, the generated
`firmware/include/tremor_model.h` + `src/tremor_model.cpp`, and the on-device interpreter
`firmware/src/classifier.cpp`. Supersedes the 3-class format from Feature 052 for the binary pivot.

## Inputs
- `backend/ml_models/lgbm_tremor_model.pkl` — imbalanced-learn `Pipeline(SMOTE, LGBMClassifier(objective="binary"))`, no scaler.

## Booster expectations (binary)
- `booster.dump_model()["num_class"] == 1` (binary uses a single tree series).
- `num_trees == n_estimators` (no ×num_class round-robin expansion).
- A non-zero **base/init score** is present when `boost_from_average` is active; it MUST be captured.
- Splits remain numerical (`decision_type "<="`); categorical (`==`) splits remain unsupported → ABORT.
- No scaler step in the pipeline → ABORT if found (unchanged guard).

## Generated header constants (`tremor_model.h`)
```
NUM_OUTPUTS  = 1            // binary single series (replaces NUM_CLASS=3)
NUM_TREES    = <n_estimators>
NUM_NODES    = <count>
NUM_FEATURES = 66
WINDOW_SIZE  = 128
SAMPLE_RATE_HZ = 100.0f
init_score[NUM_OUTPUTS]    // base/init margin (scalar for binary)
// flat node arrays unchanged: feature[], threshold[], left[], right[], default_left[], leaf_value[]
// tree_root[NUM_TREES]; bandpass_sos[4][6] unchanged
```
The generated comment header MUST state `0=Non-Tremor, 1=Tremor` (no Voluntary).

## Inference semantics (`classifier.cpp`)
```
raw = init_score[0] + Σ_t leaf_value[ traverse(tree_root[t]) ]   // all trees, single series
p_tremor = 1 / (1 + exp(-raw))                                    // sigmoid (NOT softmax)
proba = { 1 - p_tremor, p_tremor }
cls   = (p_tremor >= 0.5) ? TREMOR : NON_TREMOR
```
Traversal rule unchanged: go LEFT iff `x <= threshold` (finite), else `default_left`.

## Determinism
- Re-running `export_to_c.py` on an unchanged `.pkl` MUST produce byte-identical `.h`/`.cpp`
  (float literals via `%.9g` + guaranteed decimal/`f` suffix). [SC-008]

## Acceptance
- `parity_harness.py` Layer A: interpreter (float32) vs `pipe.predict_proba` → decision agreement
  ≥99%, `max|Δproba| < 1e-3`. [SC-005]
- No symbol named `NUM_CLASS==3`, `proba[2]`, `Voluntary`, or `init_score[2]` remains. [SC-006]
