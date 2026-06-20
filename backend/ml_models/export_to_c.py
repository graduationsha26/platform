"""
export_to_c.py — Transpile the trained LightGBM tremor model to an ESP32 C++ flat-array
interpreter (Feature 052).

Reads the trained pipeline (backend/ml_models/lgbm_tremor_model.pkl), extracts the LightGBM
booster, and emits a compact, read-only, data-driven model the firmware traverses iteratively:

  firmware/include/tremor_model.h    # constants + extern array declarations + band-pass SOS
  firmware/src/tremor_model.cpp      # the generated node arrays (do NOT hand-edit)

Why a flat-array interpreter (not m2cgen codegen): ~300 rounds x 3 classes ≈ 900 sub-trees;
m2cgen unrolls every split into nested if/else (one huge function, RecursionError-prone, slow
to compile, float64). Flat arrays + one iterative traversal are tens-of-KB, compile instantly,
and are trivially regenerated on every retrain. See specs/052-edge-ai-inference/research.md §5
and contracts/model-export-format.md.

Exact-parity rules enforced/encoded here:
  - LightGBM numerical split: go LEFT iff  x <= threshold  (decision_type "<=").
  - Multiclass layout: tree i contributes to class (i % num_class), round-robin.
  - raw[c] = init_score[c] + sum(leaf_value for trees with i%num_class==c); softmax -> proba.
  - default_left honored for non-finite inputs (defensive; device inputs are finite).
  - Asserts NO scaler in the pipeline and NO categorical ("==") splits.

The band-pass SOS coefficients (from features_lgbm.BANDPASS_SOS) are emitted into the SAME
header so the firmware filter always matches the trained feature pipeline.

Run:
    python backend/ml_models/export_to_c.py
Re-running on the same .pkl MUST produce byte-identical output (SC-008).
"""

import os
import sys

import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))            # backend/ml_models
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)                          # backend
REPO_ROOT = os.path.dirname(BACKEND_DIR)                           # repo root

sys.path.insert(0, SCRIPT_DIR)
from features_lgbm import (  # noqa: E402
    BANDPASS_SOS, FS, WINDOW_SIZE, LOWCUT, HIGHCUT, N_FEATURES, get_feature_names_66,
)

MODEL_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
H_PATH = os.path.join(REPO_ROOT, "firmware", "include", "tremor_model.h")
CPP_PATH = os.path.join(REPO_ROOT, "firmware", "src", "tremor_model.cpp")

# Float formatting: %.9g round-trips float32 and keeps the output deterministic (SC-008).
def _f(x):
    return f"{float(x):.9g}"


def _cf(x):
    """A valid C++ float literal: %.9g with a guaranteed decimal point + 'f' suffix.
    (Avoids invalid literals like '100f' / '0f' / '1f' for whole-number floats.)"""
    s = f"{float(x):.9g}"
    if "." not in s and "e" not in s and "E" not in s and "inf" not in s and "nan" not in s:
        s += ".0"
    return s + "f"


def _extract_booster(pipe):
    """Get the LightGBM Booster from the imbalanced-learn Pipeline; assert no scaler."""
    # The pipeline must not contain a feature scaler (the model trains on raw 66 features).
    steps = getattr(pipe, "named_steps", {})
    for name, step in steps.items():
        cls = type(step).__name__.lower()
        if "scaler" in name.lower() or "scaler" in cls or "minmax" in cls:
            raise SystemExit(
                f"ABORT: pipeline step '{name}' ({type(step).__name__}) looks like a scaler. "
                "The exporter does not reproduce scalers; bake it into features or remove it."
            )
    clf = steps.get("clf", None)
    if clf is None:
        raise SystemExit("ABORT: pipeline has no 'clf' step.")
    booster = getattr(clf, "booster_", None)
    if booster is None:
        raise SystemExit("ABORT: 'clf' has no fitted booster_ (model not trained?).")
    return booster


class _Flat:
    """Accumulates the global flat node arrays across all trees."""

    def __init__(self):
        self.feature = []        # int16: split feature index, or -1 for a leaf
        self.threshold = []      # float
        self.left = []           # int32 child node index
        self.right = []          # int32 child node index
        self.default_left = []   # uint8
        self.leaf_value = []     # float (raw additive score at leaves)

    def add(self, node):
        idx = len(self.feature)
        # reserve slot
        self.feature.append(-1)
        self.threshold.append(0.0)
        self.left.append(-1)
        self.right.append(-1)
        self.default_left.append(0)
        self.leaf_value.append(0.0)

        if "leaf_value" in node and "split_feature" not in node:
            self.feature[idx] = -1
            self.leaf_value[idx] = float(node["leaf_value"])
            return idx

        dt = node.get("decision_type", "<=")
        if dt != "<=":
            raise SystemExit(
                f"ABORT: unsupported decision_type '{dt}' (categorical splits not supported). "
                "All features must be numerical."
            )
        self.feature[idx] = int(node["split_feature"])
        self.threshold[idx] = float(node["threshold"])
        self.default_left[idx] = 1 if node.get("default_left", False) else 0
        # children
        l = self.add(node["left_child"])
        r = self.add(node["right_child"])
        self.left[idx] = l
        self.right[idx] = r
        return idx


def build_flat_model(pipe):
    """Build the flat-array model (the exact data the C file is generated from).

    Returns a dict with feature/threshold/left/right/default_left/leaf_value/tree_root/
    init_score/num_class. Used by export (to emit C) and by the parity harness (to validate
    the interpreter against the Python model without a C compiler).
    """
    booster = _extract_booster(pipe)
    md = booster.dump_model()
    num_class = int(md.get("num_class", 1))
    if num_class != 3:
        raise SystemExit(f"ABORT: expected num_class==3, got {num_class}.")
    max_feature_idx = int(md.get("max_feature_idx", N_FEATURES - 1))
    if max_feature_idx + 1 > N_FEATURES:
        raise SystemExit(
            f"ABORT: model uses feature index up to {max_feature_idx} but N_FEATURES={N_FEATURES}."
        )
    flat = _Flat()
    tree_root = [flat.add(t["tree_structure"]) for t in md["tree_info"]]
    return {
        "feature": flat.feature,
        "threshold": flat.threshold,
        "left": flat.left,
        "right": flat.right,
        "default_left": flat.default_left,
        "leaf_value": flat.leaf_value,
        "tree_root": tree_root,
        "init_score": [0.0] * num_class,   # multiclass default
        "num_class": num_class,
        "num_trees": len(tree_root),
    }


def _c_array(decl, values, fmt, per_line=12):
    lines = [f"{decl} = {{"]
    row = []
    for i, v in enumerate(values):
        row.append(fmt(v))
        if len(row) == per_line:
            lines.append("    " + ", ".join(row) + ",")
            row = []
    if row:
        lines.append("    " + ", ".join(row) + ",")
    lines.append("};")
    return "\n".join(lines)


def main():
    if not os.path.exists(MODEL_PATH):
        raise SystemExit(f"ABORT: model not found: {MODEL_PATH}. Run train.py first.")

    pipe = joblib.load(MODEL_PATH)
    fm = build_flat_model(pipe)
    num_class = fm["num_class"]
    num_trees = fm["num_trees"]
    tree_root = fm["tree_root"]
    init_score = fm["init_score"]

    class _FlatView:
        feature = fm["feature"]
        threshold = fm["threshold"]
        left = fm["left"]
        right = fm["right"]
        default_left = fm["default_left"]
        leaf_value = fm["leaf_value"]
    flat = _FlatView()

    num_nodes = len(flat.feature)
    sos = [[float(v) for v in row] for row in BANDPASS_SOS]   # (n_sections, 6): b0,b1,b2,a0,a1,a2
    n_sections = len(sos)

    feat_names = get_feature_names_66()

    # ── tremor_model.h ────────────────────────────────────────────────────────
    h = []
    h.append("// AUTO-GENERATED by backend/ml_models/export_to_c.py — DO NOT HAND-EDIT.")
    h.append("// Regenerate after every retrain:  python backend/ml_models/export_to_c.py")
    h.append("// Source: backend/ml_models/lgbm_tremor_model.pkl  (Feature 052)")
    h.append("#pragma once")
    h.append("#include <cstdint>")
    h.append("")
    h.append("namespace tremor_model {")
    h.append("")
    h.append(f"constexpr int   NUM_CLASS    = {num_class};   // 0=Non-Tremor, 1=Tremor, 2=Voluntary")
    h.append(f"constexpr int   NUM_TREES    = {num_trees};   // = n_estimators * NUM_CLASS (round-robin)")
    h.append(f"constexpr int   NUM_NODES    = {num_nodes};")
    h.append(f"constexpr int   NUM_FEATURES = {N_FEATURES};")
    h.append(f"constexpr float SAMPLE_RATE_HZ = {_cf(FS)};")
    h.append(f"constexpr int   WINDOW_SIZE  = {WINDOW_SIZE};")
    h.append("")
    h.append("// Per-node flat arrays (all trees concatenated). Leaf iff feature[i] < 0.")
    h.append("extern const int16_t feature[NUM_NODES];")
    h.append("extern const float   threshold[NUM_NODES];")
    h.append("extern const int32_t left[NUM_NODES];")
    h.append("extern const int32_t right[NUM_NODES];")
    h.append("extern const uint8_t default_left[NUM_NODES];")
    h.append("extern const float   leaf_value[NUM_NODES];")
    h.append("")
    h.append("// Root node index of each sub-tree; tree t contributes to class (t % NUM_CLASS).")
    h.append("extern const int32_t tree_root[NUM_TREES];")
    h.append("extern const float   init_score[NUM_CLASS];")
    h.append("")
    h.append("// Causal Butterworth band-pass SOS (matches backend/ml_models/features_lgbm.py).")
    h.append(f"// {LOWCUT}-{HIGHCUT} Hz, 4th-order, {n_sections} biquad sections at {_f(FS)} Hz.")
    h.append(f"constexpr int   BANDPASS_N_SECTIONS = {n_sections};")
    h.append("// Each row: {b0, b1, b2, a0, a1, a2} (scipy SOS order; a0 == 1).")
    h.append("extern const float bandpass_sos[BANDPASS_N_SECTIONS][6];")
    h.append("")
    h.append("} // namespace tremor_model")
    h.append("")

    # ── tremor_model.cpp ──────────────────────────────────────────────────────
    c = []
    c.append("// AUTO-GENERATED by backend/ml_models/export_to_c.py — DO NOT HAND-EDIT.")
    c.append("// Source: backend/ml_models/lgbm_tremor_model.pkl  (Feature 052)")
    c.append('#include "tremor_model.h"')
    c.append("")
    c.append("namespace tremor_model {")
    c.append("")
    c.append("// Feature index order (axis-major), for reference only:")
    for i in range(0, len(feat_names), 6):
        c.append("//   " + ", ".join(f"{i+j}:{feat_names[i+j]}" for j in range(min(6, len(feat_names) - i))))
    c.append("")
    c.append(_c_array("const int16_t feature[NUM_NODES]", flat.feature, lambda v: str(int(v))))
    c.append("")
    c.append(_c_array("const float threshold[NUM_NODES]", flat.threshold, _cf))
    c.append("")
    c.append(_c_array("const int32_t left[NUM_NODES]", flat.left, lambda v: str(int(v))))
    c.append("")
    c.append(_c_array("const int32_t right[NUM_NODES]", flat.right, lambda v: str(int(v))))
    c.append("")
    c.append(_c_array("const uint8_t default_left[NUM_NODES]", flat.default_left, lambda v: str(int(v))))
    c.append("")
    c.append(_c_array("const float leaf_value[NUM_NODES]", flat.leaf_value, _cf))
    c.append("")
    c.append(_c_array("const int32_t tree_root[NUM_TREES]", tree_root, lambda v: str(int(v)), per_line=16))
    c.append("")
    c.append(_c_array("const float init_score[NUM_CLASS]", init_score, _cf))
    c.append("")
    c.append("const float bandpass_sos[BANDPASS_N_SECTIONS][6] = {")
    for row in sos:
        c.append("    {" + ", ".join(_cf(v) for v in row) + "},")
    c.append("};")
    c.append("")
    c.append("} // namespace tremor_model")
    c.append("")

    os.makedirs(os.path.dirname(H_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(CPP_PATH), exist_ok=True)
    with open(H_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(h))
    with open(CPP_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(c))

    print(f"[OK] num_class={num_class} num_trees={num_trees} num_nodes={num_nodes} "
          f"bandpass_sections={n_sections}")
    print(f"[SAVED] {H_PATH}")
    print(f"[SAVED] {CPP_PATH}")
    approx_kb = (num_nodes * (2 + 4 + 4 + 4 + 1 + 4)) / 1024.0
    print(f"  approx model array size: {approx_kb:.1f} KB (flash, read-only)")


if __name__ == "__main__":
    main()
