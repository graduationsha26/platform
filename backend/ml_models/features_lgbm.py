"""
features_lgbm.py — Shared 66-feature pipeline for the LightGBM tremor classifier.

Single source of truth for preprocessing + feature extraction, imported by BOTH the
training script (backend/ml_models/train.py) and the live validator
(backend/test_AI_live.py), and by the Django inference service
(backend/inference/services.py). Guarantees the 66-feature vector is computed identically
everywhere — exact parity with LGBM.ipynb.

Pipeline (per LGBM.ipynb):
  resample -> 66.67 Hz  ->  0.5-20 Hz band-pass (4th-order, zero-phase)  ->  1 s windows (67 samples)
  ->  66 features (11 per axis x 6 axes, axis-major)

Feature order per axis (must match the trained model + CSV columns):
  mean, std, median, q1, q3, min, max, peak1_freq, peak1_amp, peak2_freq, peak2_amp
Axis order: AX, AY, AZ, GX, GY, GZ   (live stream aX..gZ map 1:1, same order)

No feature scaler (the notebook's LightGBM uses none).
"""

import numpy as np
from scipy.signal import butter, filtfilt, resample
from scipy.interpolate import interp1d

# ── Constants (exact notebook parity) ────────────────────────────────────────
FS = 66.67                              # model sampling rate (Hz)
WINDOW_SECONDS = 1.0
WINDOW_SIZE = int(round(FS * WINDOW_SECONDS))   # 67 samples
LOWCUT = 0.5
HIGHCUT = 20.0
BANDPASS_ORDER = 4
SIGNAL_COLS = ["AX", "AY", "AZ", "GX", "GY", "GZ"]

# Per-axis feature suffixes, in the exact order produced below.
_FEATURE_TYPES = [
    "mean", "std", "median", "q1", "q3", "min", "max",
    "peak1_freq", "peak1_amp", "peak2_freq", "peak2_amp",
]
N_FEATURES = len(_FEATURE_TYPES) * len(SIGNAL_COLS)   # 66


# ── Helpers ──────────────────────────────────────────────────────────────────

def bandpass(x, fs=FS, low=LOWCUT, high=HIGHCUT, order=BANDPASS_ORDER):
    """4th-order Butterworth band-pass, zero-phase (filtfilt). 1-D in, 1-D out."""
    nyq = fs / 2.0
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, x)


def bandpass_2d(window_2d, fs=FS, low=LOWCUT, high=HIGHCUT, order=BANDPASS_ORDER):
    """Vectorized band-pass across all axes of a (n, 6) array (axis=0 = time)."""
    nyq = fs / 2.0
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, window_2d, axis=0)


def resample_df(df, fs=FS):
    """
    Training-time resample to `fs` Hz using the recording's timestamp column `T` (ms).
    `df` must have columns ["T", *SIGNAL_COLS]. Returns a new DataFrame at `fs` Hz.
    (Timestamp-based linear interpolation — identical to LGBM.ipynb.)
    """
    import pandas as pd
    t = (df["T"].values - df["T"].values[0]) / 1000.0      # seconds
    new_t = np.arange(0, t[-1], 1.0 / fs)
    out = pd.DataFrame({"T": new_t * 1000.0})
    for c in SIGNAL_COLS:
        f = interp1d(t, df[c].values, kind="linear", fill_value="extrapolate")
        out[c] = f(new_t)
    return out


def resample_window(window_2d, n=WINDOW_SIZE):
    """
    Live-time resample: convert a fixed-size rolling buffer (m, 6) sampled at the native
    stream rate to exactly `n` samples (= WINDOW_SIZE @ 66.67 Hz) using fast FFT-based
    resampling. Fully vectorized — no Python per-sample loops.
    """
    window_2d = np.asarray(window_2d, dtype=np.float64)
    if window_2d.shape[0] == n:
        return window_2d
    return resample(window_2d, n, axis=0)


def _fft_top2(x, fs=FS, low=LOWCUT, high=HIGHCUT):
    """
    Return (peak1_freq, peak1_amp, peak2_freq, peak2_amp) for the two strongest FFT bins
    within [low, high] Hz, DC-removed. Matches LGBM.ipynb fft_top2().
    """
    x = x - np.mean(x)
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fs)
    mag = np.abs(np.fft.rfft(x))
    mask = (freqs >= low) & (freqs <= high)
    freqs, mag = freqs[mask], mag[mask]
    if mag.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    idx = np.argsort(mag)[::-1]
    i1 = idx[0]
    i2 = idx[1] if idx.size > 1 else idx[0]
    return float(freqs[i1]), float(mag[i1]), float(freqs[i2]), float(mag[i2])


# ── Public API ───────────────────────────────────────────────────────────────

def get_feature_names_66():
    """Return the 66 feature column names in the exact order of extract_features_66()."""
    names = []
    for c in SIGNAL_COLS:
        for t in _FEATURE_TYPES:
            names.append(f"{c}_{t}")
    return names


def extract_features_66(window_2d):
    """
    Extract the 66-feature vector from one analysis window.

    Parameters
    ----------
    window_2d : array-like, shape (window_size, 6)
        Band-pass-filtered window, columns in SIGNAL_COLS order
        [AX, AY, AZ, GX, GY, GZ] (== live [aX, aY, aZ, gX, gY, gZ]).

    Returns
    -------
    np.ndarray, shape (66,)  — axis-major, matching get_feature_names_66().
    """
    window_2d = np.asarray(window_2d, dtype=np.float64)
    if window_2d.ndim != 2 or window_2d.shape[1] != len(SIGNAL_COLS):
        raise ValueError(
            f"window_2d must be (window_size, {len(SIGNAL_COLS)}), got {window_2d.shape}"
        )

    feats = []
    for col in range(window_2d.shape[1]):
        x = window_2d[:, col]
        f1, a1, f2, a2 = _fft_top2(x)
        feats.append(float(np.mean(x)))
        feats.append(float(np.std(x)))
        feats.append(float(np.median(x)))
        feats.append(float(np.percentile(x, 25)))
        feats.append(float(np.percentile(x, 75)))
        feats.append(float(np.min(x)))
        feats.append(float(np.max(x)))
        feats.append(f1)
        feats.append(a1)
        feats.append(f2)
        feats.append(a2)
    return np.asarray(feats, dtype=np.float64)
