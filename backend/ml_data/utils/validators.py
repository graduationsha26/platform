"""
Data Validation Utilities

Functions for checking data integrity, shapes, distributions, and normalization.
"""

import numpy as np
from typing import Tuple, Optional


def check_no_nulls(data: np.ndarray, data_name: str = "data") -> None:
    """
    Check that array contains no NaN or Inf values.

    Parameters:
    -----------
    data : numpy.ndarray
        Array to check
    data_name : str
        Name of the data for error messages

    Raises:
    -------
    ValueError : If NaN or Inf values are found
    """
    nan_count = np.isnan(data).sum()
    inf_count = np.isinf(data).sum()

    if nan_count > 0:
        raise ValueError(f"{data_name} contains {nan_count} NaN values")

    if inf_count > 0:
        raise ValueError(f"{data_name} contains {inf_count} Inf values")

    print(f"[VALIDATION] {data_name}: No NaN or Inf values [OK]")


def check_shapes(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    expected_train_size: int,
    expected_test_size: int,
    expected_features: int
) -> None:
    """
    Validate shapes of train/test splits.

    Parameters:
    -----------
    X_train, X_test : numpy.ndarray
        Feature arrays
    y_train, y_test : numpy.ndarray
        Label arrays
    expected_train_size : int
        Expected number of training samples
    expected_test_size : int
        Expected number of test samples
    expected_features : int
        Expected number of features

    Raises:
    -------
    ValueError : If shapes don't match expectations
    """
    # Check feature shapes
    if X_train.shape != (expected_train_size, expected_features):
        raise ValueError(f"X_train shape {X_train.shape} doesn't match expected {(expected_train_size, expected_features)}")

    if X_test.shape != (expected_test_size, expected_features):
        raise ValueError(f"X_test shape {X_test.shape} doesn't match expected {(expected_test_size, expected_features)}")

    # Check label shapes
    if y_train.shape != (expected_train_size,):
        raise ValueError(f"y_train shape {y_train.shape} doesn't match expected {(expected_train_size,)}")

    if y_test.shape != (expected_test_size,):
        raise ValueError(f"y_test shape {y_test.shape} doesn't match expected {(expected_test_size,)}")

    # Check features match labels
    if X_train.shape[0] != y_train.shape[0]:
        raise ValueError(f"X_train samples ({X_train.shape[0]}) != y_train samples ({y_train.shape[0]})")

    if X_test.shape[0] != y_test.shape[0]:
        raise ValueError(f"X_test samples ({X_test.shape[0]}) != y_test samples ({y_test.shape[0]})")

    print(f"[VALIDATION] Shapes correct:")
    print(f"  X_train: {X_train.shape}, X_test: {X_test.shape}")
    print(f"  y_train: {y_train.shape}, y_test: {y_test.shape} [OK]")


def check_class_distribution(
    y_train: np.ndarray,
    y_test: np.ndarray,
    tolerance: float = 0.02
) -> None:
    """
    Validate that class distribution is preserved in train/test splits.

    Parameters:
    -----------
    y_train, y_test : numpy.ndarray
        Label arrays (binary: 0 or 1)
    tolerance : float
        Acceptable difference in class percentages (default: 0.02 = 2%)

    Raises:
    -------
    ValueError : If class distributions differ by more than tolerance
    """
    # Calculate class distributions
    train_class0_pct = (y_train == 0).mean()
    train_class1_pct = (y_train == 1).mean()
    test_class0_pct = (y_test == 0).mean()
    test_class1_pct = (y_test == 1).mean()

    # Check difference
    diff_class0 = abs(train_class0_pct - test_class0_pct)
    diff_class1 = abs(train_class1_pct - test_class1_pct)

    if diff_class0 > tolerance or diff_class1 > tolerance:
        raise ValueError(
            f"Class distribution mismatch exceeds tolerance ({tolerance}):\n"
            f"  Train: Class 0={train_class0_pct:.3f}, Class 1={train_class1_pct:.3f}\n"
            f"  Test:  Class 0={test_class0_pct:.3f}, Class 1={test_class1_pct:.3f}\n"
            f"  Diff:  Class 0={diff_class0:.3f}, Class 1={diff_class1:.3f}"
        )

    print(f"[VALIDATION] Class distribution preserved (tolerance={tolerance}):")
    print(f"  Train: Class 0={train_class0_pct:.1%}, Class 1={train_class1_pct:.1%}")
    print(f"  Test:  Class 0={test_class0_pct:.1%}, Class 1={test_class1_pct:.1%}")
    print(f"  Diff:  Class 0={diff_class0:.1%}, Class 1={diff_class1:.1%} [OK]")


def check_normalization(
    X_train: np.ndarray,
    mean_tolerance: float = 1e-6,
    std_tolerance: float = 0.1
) -> None:
    """
    Validate that data is normalized (z-score: mean~0, std~1).

    Parameters:
    -----------
    X_train : numpy.ndarray
        Training data (should be normalized)
    mean_tolerance : float
        Max acceptable deviation from mean=0
    std_tolerance : float
        Max acceptable deviation from std=1

    Raises:
    -------
    ValueError : If normalization is not correct
    """
    # Calculate per-axis statistics
    means = X_train.mean(axis=0)
    stds = X_train.std(axis=0)

    # Check all axes are close to mean=0, std=1
    mean_ok = np.allclose(means, 0, atol=mean_tolerance)
    std_ok = np.allclose(stds, 1, atol=std_tolerance)

    if not mean_ok:
        max_mean_dev = np.abs(means).max()
        raise ValueError(f"Normalization failed: max mean deviation = {max_mean_dev:.4f} (tolerance={mean_tolerance})")

    if not std_ok:
        max_std_dev = np.abs(stds - 1).max()
        raise ValueError(f"Normalization failed: max std deviation = {max_std_dev:.4f} (tolerance={std_tolerance})")

    print(f"[VALIDATION] Normalization correct:")
    print(f"  Per-axis means: {means}")
    print(f"  Per-axis stds:  {stds}")
    print(f"  Mean tolerance: {mean_tolerance}, Std tolerance: {std_tolerance} [OK]")


def check_no_data_leakage(
    X_train: np.ndarray,
    X_test: np.ndarray
) -> None:
    """
    Verify that no samples appear in both train and test sets.

    Parameters:
    -----------
    X_train, X_test : numpy.ndarray
        Training and test feature arrays

    Raises:
    -------
    ValueError : If any samples are found in both sets

    Note:
    -----
    This check can be expensive for large datasets as it requires
    comparing all train samples against all test samples.
    """
    # Convert rows to tuples for set operations
    train_tuples = set(map(tuple, X_train))
    test_tuples = set(map(tuple, X_test))

    # Find intersection
    overlap = train_tuples.intersection(test_tuples)

    if len(overlap) > 0:
        raise ValueError(f"Data leakage detected: {len(overlap)} samples appear in both train and test sets")

    print(f"[VALIDATION] No data leakage: {len(train_tuples)} train samples, {len(test_tuples)} test samples, 0 overlap [OK]")


def check_value_ranges(
    data: np.ndarray,
    data_name: str = "data",
    expected_min: Optional[float] = None,
    expected_max: Optional[float] = None,
    warn_only: bool = True
) -> None:
    """
    Check that data values fall within expected ranges.

    Parameters:
    -----------
    data : numpy.ndarray
        Data to check
    data_name : str
        Name for error messages
    expected_min : float, optional
        Expected minimum value
    expected_max : float, optional
        Expected maximum value
    warn_only : bool
        If True, print warning instead of raising error

    Raises:
    -------
    ValueError : If values are outside expected range (only if warn_only=False)
    """
    actual_min = data.min()
    actual_max = data.max()

    issues = []

    if expected_min is not None and actual_min < expected_min:
        issues.append(f"Min value {actual_min:.2f} < expected {expected_min}")

    if expected_max is not None and actual_max > expected_max:
        issues.append(f"Max value {actual_max:.2f} > expected {expected_max}")

    if issues:
        message = f"[VALIDATION] {data_name} value range issues: {'; '.join(issues)}"
        if warn_only:
            print(f"WARNING: {message}")
        else:
            raise ValueError(message)
    else:
        range_str = f"[{actual_min:.2f}, {actual_max:.2f}]"
        if expected_min is not None or expected_max is not None:
            expected_str = f"[{expected_min if expected_min is not None else '-∞'}, {expected_max if expected_max is not None else '∞'}]"
            print(f"[VALIDATION] {data_name} range {range_str} within expected {expected_str} [OK]")
        else:
            print(f"[VALIDATION] {data_name} range {range_str} [OK]")


def check_binary_labels(labels: np.ndarray, label_name: str = "labels") -> None:
    """
    Verify that labels contain only 0 and 1 (binary classification).

    Parameters:
    -----------
    labels : numpy.ndarray
        Label array
    label_name : str
        Name for error messages

    Raises:
    -------
    ValueError : If labels contain values other than 0 or 1
    """
    unique_labels = np.unique(labels)

    if not set(unique_labels).issubset({0, 1}):
        raise ValueError(f"{label_name} contains invalid values: {unique_labels}. Expected only {{0, 1}}")

    label_0_count = (labels == 0).sum()
    label_1_count = (labels == 1).sum()

    print(f"[VALIDATION] {label_name} are binary:")
    print(f"  Class 0: {label_0_count} ({label_0_count/len(labels):.1%})")
    print(f"  Class 1: {label_1_count} ({label_1_count/len(labels):.1%}) [OK]")
