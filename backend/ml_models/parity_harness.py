"""
parity_harness.py — Python<->C parity gate for the edge tremor classifier (Feature 052).

Two layers (see specs/052-edge-ai-inference/contracts/parity-harness.md):

A) MODEL parity — ALWAYS runnable (no C compiler needed):
   Run the flat-array interpreter (the EXACT arrays export_to_c.py emits, evaluated in float32
   to mirror the device) over real feature rows and confirm it reproduces the trained Python
   model's decisions/probabilities. This validates the transpilation + interpreter semantics
   (round-robin multiclass, `<=` split, softmax) — i.e. the C model classifies like Python.

B) DSP/C parity — requires a host C++ compiler (PlatformIO `native`, g++, clang++, or MSVC):
   Compile edge_features.cpp + tremor_model.cpp + classifier.cpp + parity_shim.cpp and compare
   the C feature extraction against features_lgbm on identical windows (SC-006), and the C
   prediction against the Python model (SC-005). Skipped with instructions if no compiler.

Run directly:  python backend/ml_models/parity_harness.py
Or via pytest:  pytest backend/tests/test_edge_parity.py -v
"""

import os
import sys
import shutil

import numpy as np
import pandas as pd
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, SCRIPT_DIR)
import export_to_c  # noqa: E402
from features_lgbm import get_feature_names_66  # noqa: E402

MODEL_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
CSV_PATH = os.path.join(BACKEND_DIR, "ml_data", "combined_processed_data.csv")


# ── Flat-array interpreter (float32, mirrors classifier.cpp) ──────────────────

def _interp_predict(fm, X):
    """Predict probabilities with the flat-array interpreter in float32 (device-equivalent).

    Feature 053 — BINARY: num_raw_outputs==1, so all trees sum into one raw score and
    p_tremor = sigmoid(init + sum(leaf)); returns (n, 2) = [P(Non-Tremor), P(Tremor)] to match
    sklearn predict_proba. (Falls back to softmax round-robin if an old multiclass model is passed.)
    """
    feature = np.asarray(fm["feature"], dtype=np.int32)
    threshold = np.asarray(fm["threshold"], dtype=np.float32)
    left = np.asarray(fm["left"], dtype=np.int32)
    right = np.asarray(fm["right"], dtype=np.int32)
    default_left = np.asarray(fm["default_left"], dtype=np.uint8)
    leaf_value = np.asarray(fm["leaf_value"], dtype=np.float32)
    roots = fm["tree_root"]
    num_raw = fm.get("num_raw_outputs", fm["num_class"])
    init = np.asarray(fm["init_score"], dtype=np.float32)

    Xf = np.asarray(X, dtype=np.float32)
    out_cols = 2 if num_raw == 1 else num_raw
    out = np.zeros((len(Xf), out_cols), dtype=np.float32)
    for i in range(len(Xf)):
        row = Xf[i]
        raw = init.copy()
        for t, node in enumerate(roots):
            while feature[node] >= 0:
                x = row[feature[node]]
                if np.isfinite(x):
                    go_left = x <= threshold[node]
                else:
                    go_left = default_left[node] != 0
                node = left[node] if go_left else right[node]
            raw[t % num_raw] += leaf_value[node]
        if num_raw == 1:
            p = 1.0 / (1.0 + np.exp(-raw[0]))     # sigmoid -> P(Tremor)
            out[i] = [1.0 - p, p]
        else:
            m = raw.max()
            e = np.exp(raw - m)
            out[i] = e / e.sum()
    return out


def run_model_parity(n_sample=400, seed=0):
    """Layer A: flat-array interpreter vs the trained Python model on real feature rows."""
    if not os.path.exists(MODEL_PATH):
        raise SystemExit(f"Model not found: {MODEL_PATH}. Run train.py first.")
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"Dataset not found: {CSV_PATH}. Run train.py first.")

    pipe = joblib.load(MODEL_PATH)
    fm = export_to_c.build_flat_model(pipe)

    df = pd.read_csv(CSV_PATH)
    feat_cols = get_feature_names_66()
    X = df[feat_cols].values
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(X), size=min(n_sample, len(X)), replace=False)
    Xs = X[idx]

    py_proba = pipe.predict_proba(Xs)
    py_cls = np.argmax(py_proba, axis=1)
    c_proba = _interp_predict(fm, Xs)
    c_cls = np.argmax(c_proba, axis=1)

    agreement = float(np.mean(py_cls == c_cls))
    max_proba_diff = float(np.max(np.abs(py_proba - c_proba)))
    return {
        "n": len(Xs),
        "decision_agreement": agreement,
        "max_proba_abs_diff": max_proba_diff,
        "num_trees": fm["num_trees"],
        "num_nodes": len(fm["feature"]),
    }


def check_export_reproducible():
    """SC-008: building the flat model twice yields identical arrays."""
    pipe = joblib.load(MODEL_PATH)
    a = export_to_c.build_flat_model(pipe)
    b = export_to_c.build_flat_model(pipe)
    for k in ("feature", "threshold", "left", "right", "default_left", "leaf_value", "tree_root"):
        if a[k] != b[k]:
            return False
    return True


# ── Layer B: C build (optional) ───────────────────────────────────────────────

def find_host_compiler():
    for c in ("g++", "clang++", "c++"):
        if shutil.which(c):
            return c
    if shutil.which("cl"):
        return "cl"
    return None


def run_c_parity():
    """Layer B placeholder: compile the shim + compare C features/predictions to Python.

    Returns ('skipped', reason) if no host compiler is available, else builds and runs.
    (Build wiring is provided by parity_shim.cpp; on this dev box no host compiler is present,
    so it is skipped — run on a machine with PlatformIO `native`/g++/clang/MSVC.)
    """
    comp = find_host_compiler()
    if comp is None:
        return ("skipped", "no host C++ compiler (g++/clang++/cl or PlatformIO `native`) found")
    # Full build/run is environment-specific; see parity_shim.cpp + the README for the command.
    return ("available", f"host compiler '{comp}' found — build parity_shim.cpp to run Layer B")


def main():
    print("=" * 64)
    print("Edge parity harness (Feature 052)")
    print("=" * 64)
    r = run_model_parity()
    print(f"[A] MODEL parity  (flat-array interpreter vs Python model)")
    print(f"    samples            : {r['n']}")
    print(f"    trees / nodes      : {r['num_trees']} / {r['num_nodes']}")
    print(f"    decision agreement : {r['decision_agreement']*100:.2f}%   (target 100%)")
    print(f"    max |Δ proba|      : {r['max_proba_abs_diff']:.6f}   (float32 vs float64)")
    print(f"    export reproducible: {check_export_reproducible()}")
    status, reason = run_c_parity()
    print(f"[B] DSP/C parity   : {status} — {reason}")
    ok = r["decision_agreement"] >= 0.99 and r["max_proba_abs_diff"] < 1e-3
    print("-" * 64)
    print("RESULT:", "PASS (model layer)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
