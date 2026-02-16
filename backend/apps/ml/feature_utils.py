"""
Feature Extraction Utility for Raw Feature Pipeline

This module defines the standard 6-feature schema used across training and inference.
All scripts must use these constants to ensure consistency.

Feature Schema:
    - aX, aY, aZ: Accelerometer 3-axis readings (m/s²)
    - gX, gY, gZ: Gyroscope 3-axis readings (°/s)

Usage:
    from apps.ml.feature_utils import FEATURE_COLUMNS, extract_features

    # In training scripts
    X = df[FEATURE_COLUMNS].values  # Shape: (n_samples, 6)

    # In inference
    sensor_reading = extract_features(mqtt_message)
"""

import pandas as pd
import numpy as np

# Standard 6-feature schema for raw sensor pipeline
FEATURE_COLUMNS = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

# Expected sensor ranges (for validation)
SENSOR_RANGES = {
    'aX': (-20.0, 20.0),  # m/s²
    'aY': (-20.0, 20.0),
    'aZ': (-20.0, 20.0),
    'gX': (-2000.0, 2000.0),  # °/s
    'gY': (-2000.0, 2000.0),
    'gZ': (-2000.0, 2000.0),
}


def validate_feature_columns(df):
    """
    Validate that a DataFrame contains all required feature columns.

    Args:
        df (pd.DataFrame): DataFrame to validate

    Returns:
        bool: True if all columns present

    Raises:
        ValueError: If any required columns are missing
    """
    missing_cols = set(FEATURE_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"DataFrame missing required columns: {sorted(missing_cols)}\n"
            f"Required columns: {FEATURE_COLUMNS}\n"
            f"Found columns: {sorted(df.columns)}"
        )
    return True


def extract_features_from_dataframe(df):
    """
    Extract the 6 standard features from a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with sensor data

    Returns:
        np.ndarray: Feature matrix with shape (n_samples, 6)

    Raises:
        ValueError: If required columns are missing or data contains NaN values
    """
    # Validate columns exist
    validate_feature_columns(df)

    # Extract features maintaining column order
    X = df[FEATURE_COLUMNS].values

    # Validate no missing values
    if pd.isna(X).any():
        nan_counts = pd.isna(df[FEATURE_COLUMNS]).sum()
        raise ValueError(
            f"Dataset contains missing values in feature columns:\n"
            f"{nan_counts[nan_counts > 0]}"
        )

    return X


def extract_features_from_dict(sensor_data):
    """
    Extract 6 features from a dictionary (e.g., from MQTT JSON message).

    Args:
        sensor_data (dict): Dictionary with keys: aX, aY, aZ, gX, gY, gZ

    Returns:
        np.ndarray: Feature array with shape (6,)

    Raises:
        ValueError: If any required fields are missing or non-numeric
    """
    # Validate all fields present
    missing_fields = set(FEATURE_COLUMNS) - set(sensor_data.keys())
    if missing_fields:
        raise ValueError(
            f"Sensor data missing required fields: {sorted(missing_fields)}\n"
            f"Required fields: {FEATURE_COLUMNS}\n"
            f"Provided fields: {sorted(sensor_data.keys())}"
        )

    # Extract and validate numeric values
    features = []
    for field in FEATURE_COLUMNS:
        value = sensor_data[field]
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"Sensor field '{field}' must be numeric, got {type(value).__name__}: {value}"
            )
        features.append(float(value))

    return np.array(features, dtype=np.float64)


def validate_sensor_ranges(sensor_values, warn_only=True):
    """
    Validate that sensor values are within expected physical ranges.

    Args:
        sensor_values (np.ndarray or dict): Sensor values (6,) array or dict
        warn_only (bool): If True, log warnings instead of raising exceptions (default: True)

    Returns:
        bool: True if all values within range, False if any out of range

    Raises:
        ValueError: If warn_only=False and values are out of range
    """
    # Convert array to dict for validation
    if isinstance(sensor_values, np.ndarray):
        if sensor_values.shape != (6,):
            raise ValueError(f"Expected shape (6,), got {sensor_values.shape}")
        sensor_dict = dict(zip(FEATURE_COLUMNS, sensor_values))
    else:
        sensor_dict = sensor_values

    # Check each sensor against expected range
    out_of_range = []
    for field, (min_val, max_val) in SENSOR_RANGES.items():
        value = sensor_dict[field]
        if not (min_val <= value <= max_val):
            out_of_range.append(f"{field}={value:.2f} (expected: {min_val} to {max_val})")

    if out_of_range:
        message = (
            f"Sensor values out of expected range:\n"
            f"  {', '.join(out_of_range)}\n"
            f"This may indicate device malfunction or calibration issues."
        )
        if warn_only:
            print(f"WARNING: {message}")
            return False
        else:
            raise ValueError(message)

    return True


def load_training_data(dataset_path='Dataset.csv'):
    """
    Load training data with 6-feature extraction and validation.

    Args:
        dataset_path (str): Path to Dataset.csv file

    Returns:
        tuple: (X, y) where X is (n_samples, 6) features, y is labels

    Raises:
        FileNotFoundError: If dataset file doesn't exist
        ValueError: If dataset has missing columns or NaN values
    """
    import os

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    # Load dataset
    df = pd.read_csv(dataset_path)

    # Extract features
    X = extract_features_from_dataframe(df)

    # Extract labels if present
    label_cols = ['label', 'Result', 'tremor_severity']
    y = None
    for label_col in label_cols:
        if label_col in df.columns:
            y = df[label_col].values
            break

    print(f"Loaded {len(X)} samples with {X.shape[1]} features from {dataset_path}")
    if y is not None:
        print(f"Labels found: {len(np.unique(y))} unique classes")

    return X, y


if __name__ == '__main__':
    # Test feature extraction
    import sys

    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    else:
        dataset_path = 'Dataset.csv'

    print(f"Testing feature extraction on {dataset_path}...")
    X, y = load_training_data(dataset_path)
    print(f"✓ Feature extraction successful")
    print(f"  Shape: {X.shape}")
    print(f"  Features: {FEATURE_COLUMNS}")
    print(f"  Sample (first row): {X[0]}")
