# Contract: Model Export Format (`export_to_c.py` → firmware)

`backend/ml_models/export_to_c.py` reads the trained pickle and emits a generated,
do-not-hand-edit C model. Re-running on the same `.pkl` MUST produce byte-identical output
(SC-008 reproducibility).

## Input

- `backend/ml_models/lgbm_tremor_model.pkl` — an imbalanced-learn `Pipeline`.
- Booster extracted via `pipe.named_steps['clf'].booster_`; tree structure via `dump_model()`.

## Pre-export assertions (exporter MUST fail loudly if violated)

1. Pipeline contains **no scaler** (only SMOTE, which is inference-irrelevant). If a scaler is
   ever added, its mean/scale MUST be baked into the export (currently: none).
2. **No categorical splits** — every internal node `decision_type == "<="`. (All-numeric IMU
   features; a categorical `==`/bitset split would break the scalar interpreter.)
3. `num_class == 3`; feature count == 66; feature order == `get_feature_names_66()`.

## Output: `firmware/include/tremor_model.h` + `firmware/src/tremor_model.cpp`

Per-node parallel arrays (all trees concatenated, with per-tree root offsets):

| Array | Type | Meaning |
|-------|------|---------|
| `tm_feature[]` | `int16_t` | split feature index, or `-1` for a leaf |
| `tm_threshold[]` | `float` | split threshold (compared with `<=`) |
| `tm_left[]` | `int32_t` | left child node index (taken when `x <= threshold`) |
| `tm_right[]` | `int32_t` | right child node index |
| `tm_default_left[]` | `uint8_t` | NaN/missing direction (defensive) |
| `tm_leaf_value[]` | `float` | additive raw score at a leaf |

Ensemble metadata constants:

| Symbol | Meaning |
|--------|---------|
| `TM_NUM_CLASS` | 3 |
| `TM_NUM_TREES` | total sub-trees (= n_estimators × num_class ≈ 900) |
| `TM_TREE_ROOT[]` | root node index of each sub-tree |
| `TM_TREE_CLASS[]` or rule | class of tree `i` = `i % TM_NUM_CLASS` (round-robin) |
| `TM_INIT_SCORE[]` | per-class init/boost-from-average score (0 for multiclass default; emitted if present) |

## Inference semantics the interpreter MUST implement

1. For each sub-tree, traverse from its root: at an internal node go to `tm_left` iff
   `feat[tm_feature] <= tm_threshold`, else `tm_right`; honor `tm_default_left` if
   `feat[...]` is non-finite. Stop at a leaf (`tm_feature == -1`), take `tm_leaf_value`.
2. `raw[c] = TM_INIT_SCORE[c] + Σ leaf_value over trees with (i % 3 == c)`.
3. `proba = softmax(raw - max(raw))`; `class = argmax(raw)`.

## Validation (parity harness, before firmware integration)

- m2cgen cross-check: generate m2cgen C once (raised recursion limit), diff its `output[]`
  against the interpreter on sample inputs → confirms layout/operator/softmax.
- Python `predict_proba` vs interpreter on held-out windows → SC-005 thresholds.
