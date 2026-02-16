"""
Normalization Utility for Raw Feature Pipeline

This module provides z-score normalization functions using params.json.
Ensures consistent preprocessing between training and inference.

Normalization Formula:
    normalized_value = (raw_value - mean) / std

Usage:
    from apps.ml.normalize import load_params, normalize_features

    # Load normalization parameters once at startup
    params = load_params('ml_data/params.json')

    # Normalize sensor readings during inference
    normalized = normalize_features(raw_sensor_data, params)
"""

import json
import numpy as np
import os


def load_params(params_path='ml_data/params.json'):
    """
    Load normalization parameters from params.json.

    Args:
        params_path (str): Path to params.json file

    Returns:
        dict: Normalization parameters with 'features' list and 'metadata'

    Raises:
        FileNotFoundError: If params.json doesn't exist
        ValueError: If params.json has invalid schema or missing features
    """
    if not os.path.exists(params_path):
        raise FileNotFoundError(
            f"Normalization parameters not found: {params_path}\n"
            f"Run 'python apps/ml/generate_params.py' to create it."
        )

    with open(params_path, 'r') as f:
        params = json.load(f)

    # Validate schema
    if 'features' not in params:
        raise ValueError(f"Invalid params.json: missing 'features' key")

    if not isinstance(params['features'], list):
        raise ValueError(f"Invalid params.json: 'features' must be a list")

    # Validate 6 features present
    if len(params['features']) != 6:
        raise ValueError(
            f"Invalid params.json: expected 6 features, got {len(params['features'])}"
        )

    # Validate each feature has name, mean, std
    required_keys = ['name', 'mean', 'std']
    for i, feature in enumerate(params['features']):
        missing = set(required_keys) - set(feature.keys())
        if missing:
            raise ValueError(
                f"Invalid params.json: feature {i} missing keys: {missing}"
            )

        # Validate std > 0 (prevent division by zero)
        if feature['std'] <= 0:
            raise ValueError(
                f"Invalid params.json: feature '{feature['name']}' has std={feature['std']}, "
                f"must be > 0 to prevent division by zero"
            )

    return params


def normalize_features(raw_features, params):
    """
    Apply z-score normalization to raw sensor features.

    Args:
        raw_features (np.ndarray): Raw sensor values, shape (6,) or (n_samples, 6)
        params (dict): Normalization parameters loaded from params.json

    Returns:
        np.ndarray: Normalized features with same shape as input

    Raises:
        ValueError: If feature count doesn't match params.json or array contains NaN/Inf
    """
    # Convert to numpy array if needed
    if not isinstance(raw_features, np.ndarray):
        raw_features = np.array(raw_features, dtype=np.float64)

    # Validate shape
    if raw_features.ndim == 1:
        if raw_features.shape[0] != 6:
            raise ValueError(
                f"Expected 6 features, got {raw_features.shape[0]}. "
                f"Shape should be (6,) or (n_samples, 6)"
            )
        is_single_sample = True
    elif raw_features.ndim == 2:
        if raw_features.shape[1] != 6:
            raise ValueError(
                f"Expected 6 features in last dimension, got {raw_features.shape[1]}. "
                f"Shape should be (6,) or (n_samples, 6)"
            )
        is_single_sample = False
    else:
        raise ValueError(
            f"Invalid input shape: {raw_features.shape}. "
            f"Expected (6,) or (n_samples, 6)"
        )

    # Validate no NaN or Inf values
    if np.isnan(raw_features).any():
        raise ValueError("Input contains NaN values. Cannot normalize.")
    if np.isinf(raw_features).any():
        raise ValueError("Input contains Inf values. Cannot normalize.")

    # Extract mean and std arrays from params
    means = np.array([f['mean'] for f in params['features']], dtype=np.float64)
    stds = np.array([f['std'] for f in params['features']], dtype=np.float64)

    # Apply z-score normalization: (x - mean) / std
    normalized = (raw_features - means) / stds

    # Validate normalized output
    if np.isnan(normalized).any():
        raise ValueError(
            "Normalization produced NaN values. Check params.json for zero std values."
        )
    if np.isinf(normalized).any():
        raise ValueError(
            "Normalization produced Inf values. Check params.json for zero std values."
        )

    return normalized


def denormalize_features(normalized_features, params):
    """
    Reverse z-score normalization to get back raw sensor values.

    Args:
        normalized_features (np.ndarray): Normalized values, shape (6,) or (n_samples, 6)
        params (dict): Normalization parameters loaded from params.json

    Returns:
        np.ndarray: Raw sensor values with same shape as input

    Formula:
        raw_value = (normalized_value * std) + mean
    """
    if not isinstance(normalized_features, np.ndarray):
        normalized_features = np.array(normalized_features, dtype=np.float64)

    # Extract mean and std arrays
    means = np.array([f['mean'] for f in params['features']], dtype=np.float64)
    stds = np.array([f['std'] for f in params['features']], dtype=np.float64)

    # Reverse normalization
    raw = (normalized_features * stds) + means

    return raw


def get_normalization_bounds(params, n_std=3):
    """
    Calculate expected normalized value bounds (±n standard deviations).

    Args:
        params (dict): Normalization parameters
        n_std (int): Number of standard deviations (default: 3 for 99.7% of data)

    Returns:
        tuple: (lower_bound, upper_bound) for normalized values

    Most normalized values should fall within [-3, +3] (assuming normal distribution).
    Values outside this range may indicate outliers or sensor issues.
    """
    return (-n_std, n_std)


def validate_normalized_range(normalized_features, params, n_std=3, warn_only=True):
    """
    Validate that normalized features are within expected range.

    Args:
        normalized_features (np.ndarray): Normalized features
        params (dict): Normalization parameters
        n_std (int): Number of standard deviations to allow (default: 3)
        warn_only (bool): If True, log warnings instead of raising exceptions

    Returns:
        bool: True if all values within range

    Raises:
        ValueError: If warn_only=False and values are out of range
    """
    lower, upper = get_normalization_bounds(params, n_std)

    # Check if any values outside bounds
    out_of_bounds = (normalized_features < lower) | (normalized_features > upper)

    if out_of_bounds.any():
        out_count = out_of_bounds.sum()
        message = (
            f"{out_count} normalized values outside expected range [{lower}, {upper}]. "
            f"This may indicate outliers or sensor issues."
        )
        if warn_only:
            print(f"WARNING: {message}")
            return False
        else:
            raise ValueError(message)

    return True


if __name__ == '__main__':
    # Test normalization
    import sys

    if len(sys.argv) > 1:
        params_path = sys.argv[1]
    else:
        params_path = 'ml_data/params.json'

    print(f"Testing normalization with {params_path}...")

    try:
        # Load params
        params = load_params(params_path)
        print(f"✓ Loaded parameters: {len(params['features'])} features")

        # Test with sample sensor reading
        raw_sample = np.array([0.5, -0.3, 10.2, 0.05, -0.02, 0.01])
        print(f"\nRaw sample: {raw_sample}")

        # Normalize
        normalized = normalize_features(raw_sample, params)
        print(f"Normalized: {normalized}")

        # Denormalize
        recovered = denormalize_features(normalized, params)
        print(f"Recovered: {recovered}")

        # Check if recovered matches original (within floating point precision)
        if np.allclose(raw_sample, recovered):
            print("✓ Normalization round-trip successful")
        else:
            print("✗ Normalization round-trip failed")
            print(f"  Difference: {np.abs(raw_sample - recovered)}")

    except FileNotFoundError as e:
        print(f"✗ {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Validation error: {e}")
        sys.exit(1)
