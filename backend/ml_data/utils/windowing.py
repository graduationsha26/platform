"""
Sliding Window Utilities

Functions for creating overlapping time windows from continuous sensor data
and assigning labels via majority voting.
"""

import numpy as np
from typing import Tuple, List


def create_windows(data: np.ndarray, window_size: int, stride: int) -> np.ndarray:
    """
    Create overlapping sliding windows from continuous data.

    Parameters:
    -----------
    data : numpy.ndarray
        Input data with shape (num_samples, num_features)
    window_size : int
        Number of samples per window
    stride : int
        Number of samples to shift between windows (stride < window_size for overlap)

    Returns:
    --------
    windows : numpy.ndarray
        Array of windows with shape (num_windows, window_size, num_features)

    Example:
    --------
    >>> data = np.random.randn(1000, 6)  # 1000 samples, 6 features
    >>> windows = create_windows(data, window_size=100, stride=50)
    >>> print(windows.shape)  # (19, 100, 6) - 19 windows
    """
    if len(data) < window_size:
        raise ValueError(f"Data length ({len(data)}) is less than window_size ({window_size})")

    if stride <= 0:
        raise ValueError(f"Stride must be positive, got {stride}")

    # Calculate number of windows
    num_windows = (len(data) - window_size) // stride + 1

    # Pre-allocate array
    num_features = data.shape[1] if len(data.shape) > 1 else 1
    windows = np.zeros((num_windows, window_size, num_features), dtype=data.dtype)

    # Create windows
    for i in range(num_windows):
        start_idx = i * stride
        end_idx = start_idx + window_size
        windows[i] = data[start_idx:end_idx]

    return windows


def assign_window_label(labels: np.ndarray, window_start: int, window_size: int) -> int:
    """
    Assign label to a single window using majority voting.

    Parameters:
    -----------
    labels : numpy.ndarray
        All labels with shape (num_samples,)
    window_start : int
        Starting index of window in labels array
    window_size : int
        Number of samples in window

    Returns:
    --------
    label : int
        Majority label (0 or 1) for this window

    Notes:
    ------
    - If tie (50-50), returns 1 (tremor positive, conservative medical approach)
    """
    window_labels = labels[window_start:window_start + window_size]

    # Count occurrences
    unique, counts = np.unique(window_labels, return_counts=True)
    label_counts = dict(zip(unique, counts))

    # Get majority label
    label_0_count = label_counts.get(0, 0)
    label_1_count = label_counts.get(1, 0)

    if label_1_count >= label_0_count:
        return 1
    else:
        return 0


def assign_window_labels_batch(labels: np.ndarray, window_size: int, stride: int) -> np.ndarray:
    """
    Assign labels to all windows using majority voting.

    Parameters:
    -----------
    labels : numpy.ndarray
        All labels with shape (num_samples,)
    window_size : int
        Number of samples per window
    stride : int
        Number of samples to shift between windows

    Returns:
    --------
    window_labels : numpy.ndarray
        Labels for each window with shape (num_windows,)

    Example:
    --------
    >>> labels = np.array([0,0,0,1,1,1,1,0,0,0])
    >>> window_labels = assign_window_labels_batch(labels, window_size=5, stride=2)
    >>> print(window_labels)  # [0, 1, 1, 0] - 4 windows
    """
    num_windows = (len(labels) - window_size) // stride + 1
    window_labels = np.zeros(num_windows, dtype=labels.dtype)

    for i in range(num_windows):
        start_idx = i * stride
        window_labels[i] = assign_window_label(labels, start_idx, window_size)

    return window_labels


def create_windows_with_labels(
    data: np.ndarray,
    labels: np.ndarray,
    window_size: int,
    stride: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create sliding windows and assign labels in one step.

    Parameters:
    -----------
    data : numpy.ndarray
        Input data with shape (num_samples, num_features)
    labels : numpy.ndarray
        Labels with shape (num_samples,)
    window_size : int
        Number of samples per window
    stride : int
        Number of samples to shift between windows

    Returns:
    --------
    windows : numpy.ndarray
        Array of windows with shape (num_windows, window_size, num_features)
    window_labels : numpy.ndarray
        Labels for each window with shape (num_windows,)

    Example:
    --------
    >>> data = np.random.randn(1000, 6)
    >>> labels = np.random.randint(0, 2, size=1000)
    >>> windows, window_labels = create_windows_with_labels(data, labels, 100, 50)
    >>> print(windows.shape, window_labels.shape)  # (19, 100, 6), (19,)
    """
    windows = create_windows(data, window_size, stride)
    window_labels = assign_window_labels_batch(labels, window_size, stride)

    return windows, window_labels


def pad_incomplete_window(data: np.ndarray, target_size: int) -> Tuple[np.ndarray, bool]:
    """
    Zero-pad an incomplete window at the end of the dataset.

    Parameters:
    -----------
    data : numpy.ndarray
        Incomplete window data with shape (actual_size, num_features)
    target_size : int
        Target window size

    Returns:
    --------
    padded_window : numpy.ndarray
        Zero-padded window with shape (target_size, num_features)
    is_padded : bool
        True if padding was applied

    Example:
    --------
    >>> incomplete = np.random.randn(75, 6)  # Only 75 samples
    >>> padded, is_padded = pad_incomplete_window(incomplete, target_size=128)
    >>> print(padded.shape, is_padded)  # (128, 6), True
    """
    actual_size = len(data)

    if actual_size >= target_size:
        return data[:target_size], False

    # Create padded array
    num_features = data.shape[1] if len(data.shape) > 1 else 1
    padded = np.zeros((target_size, num_features), dtype=data.dtype)
    padded[:actual_size] = data

    return padded, True
