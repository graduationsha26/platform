"""
parity_debug_raw.py — Layer C raw-capture parity debug (Feature 053, task T016/T017).

Drives the trained model from a recorded raw IMU CSV and reports, stage by stage, why the
device may classify a STILL glove as Tremor. Bisection order (contracts/parity-procedure.md):
  1. raw alignment (axis order / sign / unit scale)
  2. sample rate (capture vs device 100 Hz)
  3. band-pass output
  4. per-feature (66)
  5. final score / class

Run:  python backend/ml_models/parity_debug_raw.py
"""
import os, sys
import numpy as np
import pandas as pd
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, SCRIPT_DIR)

from features_lgbm import (
    FS, WINDOW_SIZE, SIGNAL_COLS, bandpass, extract_features_66,
    get_feature_names_66,
)

MODEL_PATH = os.path.join(SCRIPT_DIR, "lgbm_tremor_model.pkl")
COMBINED = os.path.join(BACKEND_DIR, "ml_data", "combined_processed_data.csv")
STILL = os.path.join(REPO_ROOT, "stable_glove_data_20260620_215329.csv")
CLASS_NAMES = ["Non-Tremor", "Tremor"]   # Feature 053: binary


def parse_seconds(ts):
    """'HH:MM:SS.mmm' -> seconds (float), relative to first sample."""
    out = []
    for t in ts:
        h, m, s = t.split(":")
        out.append(int(h) * 3600 + int(m) * 60 + float(s))
    out = np.array(out)
    return out - out[0]


def resample_to(sig_2d, t_sec, fs=FS):
    """Linear-interp a (n,6) signal sampled at times t_sec onto a uniform fs grid."""
    new_t = np.arange(0, t_sec[-1], 1.0 / fs)
    out = np.empty((len(new_t), sig_2d.shape[1]))
    for c in range(sig_2d.shape[1]):
        out[:, c] = np.interp(new_t, t_sec, sig_2d[:, c])
    return out


def windows_predict(pipe, sig_2d, label):
    """Causal band-pass whole signal, slice 128 non-overlapping windows, predict each."""
    filt = np.empty_like(sig_2d)
    for c in range(sig_2d.shape[1]):
        filt[:, c] = bandpass(sig_2d[:, c])
    rows = []
    for start in range(0, len(filt) - WINDOW_SIZE + 1, WINDOW_SIZE):
        rows.append(extract_features_66(filt[start:start + WINDOW_SIZE]))
    if not rows:
        print(f"  [{label}] no full 128-sample window ({len(filt)} samples)"); return None
    X = np.asarray(rows)
    proba = pipe.predict_proba(X)
    cls = np.argmax(proba, axis=1)
    counts = {CLASS_NAMES[i]: int((cls == i).sum()) for i in range(len(CLASS_NAMES))}
    print(f"  [{label}] {len(X)} windows -> {counts}   mean P[tremor]={proba[:,1].mean():.3f}")
    return X, proba, cls


def main():
    pipe = joblib.load(MODEL_PATH)
    print("=" * 70)
    print("Layer C raw-capture parity debug — still glove")
    print("=" * 70)

    df = pd.read_csv(STILL)
    cols = list(df.columns)
    print(f"[1] RAW ALIGNMENT")
    print(f"    capture columns : {cols}")
    print(f"    expected order  : ['Timestamp', *{SIGNAL_COLS}] (case-insensitive)")
    sig = df[["aX", "aY", "aZ", "gX", "gY", "gZ"]].values.astype(float)
    print(f"    accel mean |g|  : {np.linalg.norm(sig[:, :3], axis=1).mean():.3f} m/s^2  (≈9.8 ⇒ m/s²)")
    print(f"    per-axis mean   : " + ", ".join(f"{SIGNAL_COLS[i]}={sig[:,i].mean():+.3f}" for i in range(6)))
    print(f"    per-axis std    : " + ", ".join(f"{SIGNAL_COLS[i]}={sig[:,i].std():.4f}" for i in range(6)))

    t = parse_seconds(df.iloc[:, 0].astype(str).values)
    rate = (len(t) - 1) / t[-1]
    print(f"[2] SAMPLE RATE   : capture ≈ {rate:.1f} Hz ; device/model = {FS:.0f} Hz")

    print(f"[3/4/5] PREDICTIONS (band-pass -> 66 feat -> model)")
    # Native-rate windows (what a naive 1:1 replay would do)
    windows_predict(pipe, sig, f"as-is @ {rate:.0f}Hz")
    # Device-equivalent: resample to 100 Hz first
    sig100 = resample_to(sig, t, FS)
    res_native = windows_predict(pipe, sig100, "resampled @ 100Hz (device-equivalent)")

    # Compare still feature vector against the trained Non-Tremor vs Tremor centroids.
    print(f"[*] FEATURE-SPACE LOCATION (vs trained class centroids)")
    comb = pd.read_csv(COMBINED)
    feat_cols = get_feature_names_66()
    if res_native is not None:
        Xs = res_native[0]
        still_mean = Xs.mean(axis=0)
        for lbl, name in [(0, "Non-Tremor"), (1, "Tremor")]:
            c = comb[comb["label"] == lbl][feat_cols].mean(axis=0).values
            d = np.linalg.norm(still_mean - c)
            print(f"    L2 distance still->{name:11s} centroid = {d:.2f}")
        # Show a few discriminative amplitude features
        print(f"    still std(AX,AY,AZ,GX,GY,GZ) per-window-mean:")
        for ax in range(6):
            idx = ax * 11 + 1  # std is the 2nd feature per axis
            tr = comb[comb["label"] == 1][feat_cols[idx]].mean()
            nt = comb[comb["label"] == 0][feat_cols[idx]].mean()
            print(f"      {SIGNAL_COLS[ax]}_std: still={still_mean[idx]:.4f}  "
                  f"train_nontremor={nt:.4f}  train_tremor={tr:.4f}")


if __name__ == "__main__":
    main()
