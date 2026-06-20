"""
features_lgbm.py — Shared 66-feature pipeline for the LightGBM tremor classifier.

Single source of truth for preprocessing + feature extraction, imported by the training
script (backend/ml_models/train.py), the live validators (backend/test_AI_live.py,
backend/monitor_edge_live.py), and the Django inference service
(backend/inference/services.py). Guarantees the 66-feature vector is computed identically
everywhere — and, for Feature 052, identically to the on-device C++ port
(firmware/src/edge_features.cpp).

Pipeline (Feature 052 — native edge rate):
  resample -> 100 Hz  ->  0.5-20 Hz band-pass (4th-order Butterworth, CAUSAL SOS)
  ->  128-sample windows (1.28 s; power-of-2 == FFT length)
  ->  66 features (11 per axis x 6 axes, axis-major)

Why CAUSAL (single-pass sosfilt) instead of the previous zero-phase filtfilt:
  the ESP32 runs the identical biquad cascade as a continuous stream filter (it cannot see
  future samples). Training therefore filters the whole recording with the SAME causal SOS
  before slicing windows, so each training window holds exactly what the device's streamed
  filter produces (after its one-time warm-up). The per-window helper `bandpass_2d` /
  `process_window` is used by the single-window REST/live paths (which lack a continuous
  stream) and applies the same causal SOS to the window.

Feature order per axis (must match the trained model + CSV columns):
  mean, std, median, q1, q3, min, max, peak1_freq, peak1_amp, peak2_freq, peak2_amp
Axis order: AX, AY, AZ, GX, GY, GZ   (live stream aX..gZ map 1:1, same order)

No feature scaler (the LightGBM pipeline uses none).
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt, resample
from scipy.interpolate import interp1d

# ── Constants (Feature 052 native edge rate) ─────────────────────────────────
FS = 100.0                              # model sampling rate (Hz) — device native, no resample
WINDOW_SIZE = 128                       # samples per window (== FFT length, power of 2)
WINDOW_SECONDS = WINDOW_SIZE / FS       # 1.28 s
LOWCUT = 0.5
HIGHCUT = 20.0
BANDPASS_ORDER = 4
SIGNAL_COLS = ["AX", "AY", "AZ", "GX", "GY", "GZ"]

# Causal Butterworth band-pass as second-order sections (SOS). A 4th-order band-pass is an
# 8th-order filter -> 4 biquad sections. These exact coefficients are what the firmware
# hardcodes for esp-dsp's dsps_biquad_f32 cascade (see export note below). Single source of truth.
_NYQ = FS / 2.0
BANDPASS_SOS = butter(BANDPASS_ORDER, [LOWCUT / _NYQ, HIGHCUT / _NYQ], btype="band", output="sos")

# Per-axis feature suffixes, in the exact order produced below.
_FEATURE_TYPES = [
    "mean", "std", "median", "q1", "q3", "min", "max",
    "peak1_freq", "peak1_amp", "peak2_freq", "peak2_amp",
]
N_FEATURES = len(_FEATURE_TYPES) * len(SIGNAL_COLS)   # 66


# ── Helpers ──────────────────────────────────────────────────────────────────

def bandpass(x, sos=BANDPASS_SOS):
    """Causal 4th-order Butterworth band-pass (single-pass sosfilt). 1-D in, 1-D out.

    Applied to a WHOLE recording at training time so each sliced window matches the device's
    continuously-streamed filter output. Causal (not zero-phase) for streaming parity.
    """
    return sosfilt(sos, x)


def bandpass_2d(window_2d, sos=BANDPASS_SOS):
    """Causal band-pass across all axes of a (n, 6) array (axis=0 = time).

    Used by the single-window REST/live paths (which have no continuous stream): the same
    causal SOS is applied to the window from zero initial state.
    """
    return sosfilt(sos, np.asarray(window_2d, dtype=np.float64), axis=0)


def bandpass_zerophase(x, sos=BANDPASS_SOS):
    """Zero-phase fallback (forward-backward) — documented alternative if causal accuracy
    regresses (research.md §2). Reproducible on-device over a buffered window. Not used by
    default."""
    return sosfiltfilt(sos, x)


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


def process_window(raw_window_2d):
    """Canonical single-window path: causal band-pass the raw window, then extract 66 features.

    Used by the single-window REST/live consumers (inference service, test_AI_live) so they
    apply the SAME band-pass as training. (Training itself filters the whole recording before
    slicing; this per-window form is the closest single-window equivalent — see module docstring.)
    """
    return extract_features_66(bandpass_2d(raw_window_2d))


def get_bandpass_sos():
    """Return the causal Butterworth SOS coefficients (shape (n_sections, 6)) — the exact
    values the firmware hardcodes for its esp-dsp biquad cascade."""
    return BANDPASS_SOS.copy()
