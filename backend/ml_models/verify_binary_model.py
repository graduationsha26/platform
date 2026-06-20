"""verify_binary_model.py — sanity-check the cleaned binary model centroids (Feature 053, T019/step3).

Confirms:
  (a) Non-Tremor (stillness + Control) = LOW band-passed variance.
  (b) Tremor (Parkinson) = specific frequency/variance pattern (peak in the tremor band, higher amp).
  (c) The device still-glove capture now classifies Non-Tremor (the original bug is fixed).
"""
import os, sys
import numpy as np
import pandas as pd
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, SCRIPT_DIR)
from features_lgbm import FS, WINDOW_SIZE, SIGNAL_COLS, bandpass, extract_features_66, get_feature_names_66

MODEL = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
COMBINED = os.path.join(BACKEND_DIR, "ml_data", "combined_processed_data.csv")
STILL = os.path.join(REPO_ROOT, "stable_glove_data_20260620_215329.csv")
NAMES = get_feature_names_66()


def feat_idx(axis, kind):
    return axis * 11 + ["mean", "std", "median", "q1", "q3", "min", "max",
                        "peak1_freq", "peak1_amp", "peak2_freq", "peak2_amp"].index(kind)


def main():
    pipe = joblib.load(MODEL)
    comb = pd.read_csv(COMBINED)
    fc = NAMES

    print("=" * 72)
    print("BINARY MODEL CENTROID SANITY CHECK (Feature 053)")
    print("=" * 72)
    print(f"classes: 0=Non-Tremor  1=Tremor   windows: {dict(comb['label'].value_counts().sort_index())}")

    print("\n[A] Band-passed STD per axis (mean over windows) — expect Non-Tremor < Tremor:")
    print(f"    {'axis':5s} {'Non-Tremor':>12s} {'Tremor':>12s}")
    for ax in range(6):
        i = feat_idx(ax, "std")
        nt = comb[comb.label == 0][fc[i]].mean()
        tr = comb[comb.label == 1][fc[i]].mean()
        print(f"    {SIGNAL_COLS[ax]:5s} {nt:12.4f} {tr:12.4f}")

    print("\n[B] Dominant peak FREQUENCY per axis (mean Hz) — expect Tremor in 3-8 Hz tremor band:")
    print(f"    {'axis':5s} {'Non-Tremor':>12s} {'Tremor':>12s}")
    for ax in range(6):
        i = feat_idx(ax, "peak1_freq")
        nt = comb[comb.label == 0][fc[i]].mean()
        tr = comb[comb.label == 1][fc[i]].mean()
        print(f"    {SIGNAL_COLS[ax]:5s} {nt:12.3f} {tr:12.3f}")

    # (c) still capture end-to-end
    df = pd.read_csv(STILL).iloc[:, :7]
    df.columns = ["T"] + SIGNAL_COLS

    def to_ms(t):
        h, m, s = str(t).split(":"); return (int(h) * 3600 + int(m) * 60 + float(s)) * 1000.0
    df["T"] = df["T"].map(to_ms)
    df = df.drop_duplicates(subset="T").sort_values("T").reset_index(drop=True)
    t = (df["T"].values - df["T"].values[0]) / 1000.0
    new_t = np.arange(0, t[-1], 1.0 / FS)
    sig = np.column_stack([np.interp(new_t, t, df[c].values) for c in SIGNAL_COLS])
    filt = np.column_stack([bandpass(sig[:, c]) for c in range(6)])
    rows = [extract_features_66(filt[s:s + WINDOW_SIZE])
            for s in range(0, len(filt) - WINDOW_SIZE + 1, WINDOW_SIZE)]
    X = np.asarray(rows)
    proba = pipe.predict_proba(X)
    cls = np.argmax(proba, axis=1)
    n_nt = int((cls == 0).sum())
    print(f"\n[C] STILL-GLOVE CAPTURE: {len(X)} windows -> Non-Tremor={n_nt} Tremor={int((cls==1).sum())}")
    print(f"    mean P[Non-Tremor]={proba[:,0].mean():.3f}  mean P[Tremor]={proba[:,1].mean():.3f}")
    verdict = "FIXED ✅ (still -> Non-Tremor)" if n_nt / len(X) >= 0.95 else "STILL BROKEN ❌"
    print(f"    VERDICT: {verdict}  ({100*n_nt/len(X):.1f}% Non-Tremor)")


if __name__ == "__main__":
    main()
