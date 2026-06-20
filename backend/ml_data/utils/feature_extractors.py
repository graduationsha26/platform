"""
Feature Extractors — v2 Pipeline

Shared feature extraction for the ML pipeline.  Every consumer (training script,
Django inference service, live MQTT test) imports from this single module to
guarantee that the feature vector is always computed identically.

Feature set (v2): 7 features × 6 axes = 42 features (axis-major order)
  Per axis: mean, std, max, min, rms, median, dominant_freq
  Axes order: aX, aY, aZ, gX, gY, gZ

dominant_freq is the Hz value of the highest-power FFT bin in the Parkinson's
tremor band [3 Hz, 12 Hz].  This naturally ignores the DC gravity component
(0 Hz) and captures the clinically relevant oscillation frequency.
"""

import numpy as np
from typing import List


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _calculate_rms(window: np.ndarray) -> float:
    """Root Mean Square of a 1-D signal window."""
    return float(np.sqrt(np.mean(window ** 2)))


def _calculate_dominant_freq(
    window: np.ndarray,
    sampling_rate_hz: float,
    low_hz: float = 3.0,
    high_hz: float = 12.0,
) -> float:
    """
    Dominant frequency (Hz) in the tremor band [low_hz, high_hz].

    Uses np.fft.rfft on the raw signal (no DC removal needed — we simply
    ignore the 0-Hz bin by setting low_hz >= 3.0).

    Returns 0.0 when no FFT bins fall within the requested band (e.g., the
    window is too short relative to the sampling rate).
    """
    N = len(window)
    fft_magnitude = np.abs(np.fft.rfft(window))
    freqs = np.fft.rfftfreq(N, d=1.0 / sampling_rate_hz)

    band_mask = (freqs >= low_hz) & (freqs <= high_hz)
    band_freqs = freqs[band_mask]
    band_magnitudes = fft_magnitude[band_mask]

    if len(band_magnitudes) == 0:
        return 0.0

    return float(band_freqs[np.argmax(band_magnitudes)])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

FEATURE_TYPES: List[str] = ['mean', 'std', 'max', 'min', 'rms', 'median', 'dominant_freq']
TREMOR_BAND_LOW_HZ: float = 3.0
TREMOR_BAND_HIGH_HZ: float = 12.0


def get_feature_names(axis_names: List[str]) -> List[str]:
    """
    Return the 42 feature column names in the exact order produced by
    extract_window_features().

    Parameters
    ----------
    axis_names : list of str
        Axis labels in order, e.g. ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

    Returns
    -------
    feature_names : list of str
        Length = len(axis_names) * 7
        e.g. ['mean_aX', 'std_aX', 'max_aX', 'min_aX', 'rms_aX',
               'median_aX', 'dominant_freq_aX', 'mean_aY', ...]

    Example
    -------
    >>> names = get_feature_names(['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'])
    >>> len(names)
    42
    >>> names[:7]
    ['mean_aX', 'std_aX', 'max_aX', 'min_aX', 'rms_aX', 'median_aX', 'dominant_freq_aX']
    """
    names: List[str] = []
    for axis in axis_names:
        for feat in FEATURE_TYPES:
            names.append(f'{feat}_{axis}')
    return names


def extract_window_features(
    window_2d: np.ndarray,
    axis_names: List[str],
    sampling_rate_hz: float,
    low_hz: float = TREMOR_BAND_LOW_HZ,
    high_hz: float = TREMOR_BAND_HIGH_HZ,
) -> np.ndarray:
    """
    Extract 42 features from a single multi-axis sensor window.

    Parameters
    ----------
    window_2d : np.ndarray, shape (window_size, num_axes)
        Sensor data in physical units (m/s² for accel, °/s for gyro).
        Must already be converted from raw ADC values before calling this.
    axis_names : list of str
        Names matching the column order of window_2d, e.g.
        ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    sampling_rate_hz : float
        Sampling rate of the data (Hz).  Used for FFT frequency resolution.
        Use ~250.0 for training Excel data, ~30.0 for live ESP32 stream.
    low_hz : float
        Lower bound of Parkinson's tremor frequency band (default: 3.0 Hz).
    high_hz : float
        Upper bound of Parkinson's tremor frequency band (default: 12.0 Hz).

    Returns
    -------
    features : np.ndarray, shape (len(axis_names) * 7,)
        Feature vector in axis-major order:
        [mean_aX, std_aX, max_aX, min_aX, rms_aX, median_aX, dominant_freq_aX,
         mean_aY, ..., dominant_freq_gZ]

    Raises
    ------
    ValueError
        If window_2d.shape[1] != len(axis_names).

    Example
    -------
    >>> import numpy as np
    >>> win = np.random.randn(200, 6)
    >>> feats = extract_window_features(win, ['aX','aY','aZ','gX','gY','gZ'], 250.0)
    >>> feats.shape
    (42,)
    """
    if window_2d.ndim != 2:
        raise ValueError(
            f'window_2d must be 2-D (window_size, num_axes), got shape {window_2d.shape}'
        )
    if window_2d.shape[1] != len(axis_names):
        raise ValueError(
            f'window_2d has {window_2d.shape[1]} columns but axis_names has '
            f'{len(axis_names)} entries'
        )

    features: List[float] = []

    for col_idx in range(len(axis_names)):
        axis_data = window_2d[:, col_idx].astype(np.float64)

        features.append(float(np.mean(axis_data)))
        features.append(float(np.std(axis_data)))
        features.append(float(np.max(axis_data)))
        features.append(float(np.min(axis_data)))
        features.append(_calculate_rms(axis_data))
        features.append(float(np.median(axis_data)))
        features.append(_calculate_dominant_freq(axis_data, sampling_rate_hz, low_hz, high_hz))

    return np.array(features, dtype=np.float64)
