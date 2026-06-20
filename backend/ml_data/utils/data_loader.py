"""
CSV Data Loader and Validation

Functions for loading Dataset.csv, validating structure, and dropping disabled sensors.
"""

import pandas as pd
import numpy as np
from typing import Tuple
import os


def load_dataset(csv_path: str) -> pd.DataFrame:
    """
    Load the tremor detection dataset from CSV.

    Parameters:
    -----------
    csv_path : str
        Path to Dataset.csv file

    Returns:
    --------
    df : pandas.DataFrame
        Loaded dataset with all columns

    Raises:
    -------
    FileNotFoundError : If CSV file doesn't exist
    ValueError : If CSV structure is invalid
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to load CSV: {e}")

    return df


def validate_structure(df: pd.DataFrame) -> None:
    """
    Validate that DataFrame has expected column structure.

    Parameters:
    -----------
    df : pandas.DataFrame
        Dataset to validate

    Raises:
    -------
    ValueError : If structure is invalid
    """
    expected_columns = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ', 'mX', 'mY', 'mZ', 'Result']

    if not all(col in df.columns for col in expected_columns):
        missing = [col for col in expected_columns if col not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    if len(df) == 0:
        raise ValueError("Dataset is empty")

    # Check data types (should be numeric)
    for col in expected_columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column {col} is not numeric")

    # Check Result column has only 0 and 1
    unique_labels = df['Result'].unique()
    if not set(unique_labels).issubset({0, 1}):
        raise ValueError(f"Result column has invalid values: {unique_labels}")


def drop_magnetometer_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop magnetometer columns (mX, mY, mZ) as they are disabled (all -1).

    Parameters:
    -----------
    df : pandas.DataFrame
        Dataset with magnetometer columns

    Returns:
    --------
    df_clean : pandas.DataFrame
        Dataset with only accelerometer, gyroscope, and Result columns
    """
    # Verify magnetometer columns are indeed all -1
    mag_cols = ['mX', 'mY', 'mZ']
    for col in mag_cols:
        if (df[col] != -1).any():
            print(f"WARNING: {col} has values other than -1")

    # Drop magnetometer columns
    df_clean = df.drop(columns=mag_cols)

    return df_clean


def load_and_preprocess_csv(csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Complete loading pipeline: load, validate, drop magnetometer, separate features/labels.

    Parameters:
    -----------
    csv_path : str
        Path to Dataset.csv

    Returns:
    --------
    features : numpy.ndarray
        Feature matrix with shape (N, 6) - 6 active sensor axes
    labels : numpy.ndarray
        Label vector with shape (N,) - binary classification (0 or 1)
    """
    # Load
    df = load_dataset(csv_path)
    print(f"[INFO] Loaded dataset: {len(df)} samples")

    # Validate
    validate_structure(df)
    print("[INFO] Dataset structure validated")

    # Drop magnetometer
    df_clean = drop_magnetometer_columns(df)
    print("[INFO] Dropped magnetometer columns (mX, mY, mZ)")

    # Separate features and labels
    feature_cols = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    features = df_clean[feature_cols].values
    labels = df_clean['Result'].values

    print(f"[INFO] Features shape: {features.shape}")
    print(f"[INFO] Labels shape: {labels.shape}")

    return features, labels
