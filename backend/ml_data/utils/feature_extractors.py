"""
Statistical Feature Extractors

Functions for extracting statistical features from time-series windows for traditional ML models.
"""

import numpy as np
from scipy import stats
from typing import Dict, List


def calculate_rms(window: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) of a signal window.

    RMS measures the overall energy/intensity of the signal.

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values

    Returns:
    --------
    rms : float
        Root mean square value (always non-negative)

    Formula:
    --------
    RMS = sqrt(mean(x^2))

    Example:
    --------
    >>> window = np.array([1, 2, 3, 4, 5])
    >>> rms = calculate_rms(window)
    >>> print(f"{rms:.2f}")  # 3.32
    """
    return np.sqrt(np.mean(window ** 2))


def calculate_mean(window: np.ndarray) -> float:
    """
    Calculate mean (average) of a signal window.

    Represents the central tendency or DC offset.

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values

    Returns:
    --------
    mean : float
        Average value

    Example:
    --------
    >>> window = np.array([1, 2, 3, 4, 5])
    >>> mean = calculate_mean(window)
    >>> print(mean)  # 3.0
    """
    return np.mean(window)


def calculate_std(window: np.ndarray) -> float:
    """
    Calculate standard deviation of a signal window.

    Measures signal variability/spread around the mean.

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values

    Returns:
    --------
    std : float
        Standard deviation (always non-negative)

    Example:
    --------
    >>> window = np.array([1, 2, 3, 4, 5])
    >>> std = calculate_std(window)
    >>> print(f"{std:.2f}")  # 1.41
    """
    return np.std(window)


def calculate_skewness(window: np.ndarray) -> float:
    """
    Calculate skewness of a signal window.

    Measures asymmetry of the distribution.

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values

    Returns:
    --------
    skewness : float
        Skewness value
        - skew = 0: symmetric distribution
        - skew > 0: right tail (positive spikes)
        - skew < 0: left tail (negative spikes)

    Example:
    --------
    >>> window = np.array([1, 2, 3, 4, 5])
    >>> skew = calculate_skewness(window)
    >>> print(f"{skew:.2f}")  # ~0.00 (symmetric)
    """
    return stats.skew(window)


def calculate_kurtosis(window: np.ndarray) -> float:
    """
    Calculate kurtosis of a signal window.

    Measures tail heaviness (presence of outliers/spikes).

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values

    Returns:
    --------
    kurtosis : float
        Excess kurtosis value
        - kurt = 0: normal distribution
        - kurt > 0: heavy tails (sharp peaks, outliers)
        - kurt < 0: light tails (flat distribution)

    Example:
    --------
    >>> window = np.array([1, 2, 3, 4, 5])
    >>> kurt = calculate_kurtosis(window)
    >>> print(f"{kurt:.2f}")  # ~-1.30 (uniform-like)
    """
    return stats.kurtosis(window)


def extract_features_single_axis(window: np.ndarray) -> Dict[str, float]:
    """
    Extract all 5 statistical features for a single axis.

    Parameters:
    -----------
    window : numpy.ndarray
        1D array of sensor values for one axis

    Returns:
    --------
    features : dict
        Dictionary with keys: 'RMS', 'mean', 'std', 'skewness', 'kurtosis'

    Example:
    --------
    >>> window_aX = np.random.randn(100)
    >>> features = extract_features_single_axis(window_aX)
    >>> print(features.keys())  # dict_keys(['RMS', 'mean', 'std', 'skewness', 'kurtosis'])
    """
    return {
        'RMS': calculate_rms(window),
        'mean': calculate_mean(window),
        'std': calculate_std(window),
        'skewness': calculate_skewness(window),
        'kurtosis': calculate_kurtosis(window)
    }


def extract_features_all_axes(window: np.ndarray, axis_names: List[str]) -> Dict[str, float]:
    """
    Extract all features for all axes in a multi-dimensional window.

    Parameters:
    -----------
    window : numpy.ndarray
        2D array with shape (window_size, num_axes)
    axis_names : list of str
        Names of axes (e.g., ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'])

    Returns:
    --------
    features : dict
        Dictionary with keys like 'RMS_aX', 'mean_aX', 'std_aX', etc.
        Total: num_axes × 5 features

    Example:
    --------
    >>> window = np.random.randn(100, 6)  # 100 samples, 6 axes
    >>> axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    >>> features = extract_features_all_axes(window, axis_names)
    >>> print(len(features))  # 30 (6 axes × 5 features)
    >>> print(list(features.keys())[:5])  # ['RMS_aX', 'mean_aX', 'std_aX', 'skewness_aX', 'kurtosis_aX']
    """
    if window.shape[1] != len(axis_names):
        raise ValueError(f"Number of axes in window ({window.shape[1]}) doesn't match axis_names ({len(axis_names)})")

    all_features = {}

    for i, axis_name in enumerate(axis_names):
        axis_window = window[:, i]
        axis_features = extract_features_single_axis(axis_window)

        # Add features with axis suffix
        for feature_name, feature_value in axis_features.items():
            feature_key = f"{feature_name}_{axis_name}"
            all_features[feature_key] = feature_value

    return all_features


def extract_features_batch(
    windows: np.ndarray,
    axis_names: List[str]
) -> np.ndarray:
    """
    Extract features for a batch of windows (vectorized).

    Parameters:
    -----------
    windows : numpy.ndarray
        3D array with shape (num_windows, window_size, num_axes)
    axis_names : list of str
        Names of axes (e.g., ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'])

    Returns:
    --------
    feature_matrix : numpy.ndarray
        2D array with shape (num_windows, num_features)
        where num_features = num_axes × 5

    Example:
    --------
    >>> windows = np.random.randn(10, 100, 6)  # 10 windows, 100 samples each, 6 axes
    >>> axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    >>> feature_matrix = extract_features_batch(windows, axis_names)
    >>> print(feature_matrix.shape)  # (10, 30) - 10 windows, 30 features
    """
    num_windows = windows.shape[0]
    num_features = len(axis_names) * 5

    feature_matrix = np.zeros((num_windows, num_features))

    for i in range(num_windows):
        features_dict = extract_features_all_axes(windows[i], axis_names)
        # Convert dict to array (preserves insertion order in Python 3.7+)
        feature_matrix[i] = list(features_dict.values())

    return feature_matrix


def get_feature_names(axis_names: List[str]) -> List[str]:
    """
    Generate feature column names for a given set of axes.

    Parameters:
    -----------
    axis_names : list of str
        Names of axes (e.g., ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'])

    Returns:
    --------
    feature_names : list of str
        List of feature names in order
        (e.g., ['RMS_aX', 'mean_aX', ..., 'kurtosis_gZ'])

    Example:
    --------
    >>> axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    >>> feature_names = get_feature_names(axis_names)
    >>> print(len(feature_names))  # 30
    >>> print(feature_names[:5])  # ['RMS_aX', 'mean_aX', 'std_aX', 'skewness_aX', 'kurtosis_aX']
    """
    feature_types = ['RMS', 'mean', 'std', 'skewness', 'kurtosis']
    feature_names = []

    for axis_name in axis_names:
        for feature_type in feature_types:
            feature_names.append(f"{feature_type}_{axis_name}")

    return feature_names
