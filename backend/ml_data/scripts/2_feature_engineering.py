#!/usr/bin/env python
"""
Feature Engineering Script (User Story 2)

Extracts statistical features from sliding windows for traditional ML models
(Random Forest, SVM, XGBoost).

Usage:
    python 2_feature_engineering.py [--input DIR] [--output DIR]

Outputs:
    - train_features.csv (feature matrix with 30 features + label)
    - test_features.csv (feature matrix with 30 features + label)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.windowing import create_windows_with_labels
from utils.feature_extractors import extract_features_batch, get_feature_names


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract features from sliding windows")
    parser.add_argument(
        "--input",
        type=str,
        default="../processed/",
        help="Input directory with preprocessed data (default: ../processed/)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../processed/",
        help="Output directory for feature matrices (default: ../processed/)"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=100,
        help="Window size in samples (default: 100 samples = 1s at 100Hz)"
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=50,
        help="Stride in samples (default: 50 samples = 50%% overlap)"
    )
    return parser.parse_args()


def load_preprocessed_data(input_dir: str):
    """
    Load preprocessed data from User Story 1 outputs.

    Parameters:
    -----------
    input_dir : str
        Directory containing preprocessed .npy files

    Returns:
    --------
    X_train, X_test, y_train, y_test : numpy.ndarray
        Loaded preprocessed data
    """
    print("\n[STEP] Loading preprocessed data...")

    # Load training data
    X_train = np.load(os.path.join(input_dir, "train_normalized.npy"))
    y_train = np.load(os.path.join(input_dir, "train_labels.npy"))

    # Load test data
    X_test = np.load(os.path.join(input_dir, "test_normalized.npy"))
    y_test = np.load(os.path.join(input_dir, "test_labels.npy"))

    print(f"  Loaded train: {X_train.shape[0]} samples, {X_train.shape[1]} features")
    print(f"  Loaded test: {X_test.shape[0]} samples, {X_test.shape[1]} features")
    print(f"  Train labels: {y_train.shape[0]}, Test labels: {y_test.shape[0]}")

    return X_train, X_test, y_train, y_test


def create_windowed_data(X: np.ndarray, y: np.ndarray, window_size: int, stride: int, dataset_name: str):
    """
    Create sliding windows from continuous data.

    Parameters:
    -----------
    X : numpy.ndarray
        Feature data (samples, features)
    y : numpy.ndarray
        Labels (samples,)
    window_size : int
        Number of samples per window
    stride : int
        Number of samples to shift between windows
    dataset_name : str
        Name for logging (e.g., "train", "test")

    Returns:
    --------
    windows : numpy.ndarray
        Windows with shape (num_windows, window_size, num_features)
    window_labels : numpy.ndarray
        Labels for each window (num_windows,)
    """
    print(f"\n[STEP] Creating sliding windows for {dataset_name} set...")
    print(f"  Window size: {window_size} samples (1 second at 100Hz)")
    print(f"  Stride: {stride} samples (50% overlap)")

    windows, window_labels = create_windows_with_labels(X, y, window_size, stride)

    print(f"  Created {len(windows)} windows")
    print(f"    Class 0: {(window_labels == 0).sum()} ({(window_labels == 0).mean():.1%})")
    print(f"    Class 1: {(window_labels == 1).sum()} ({(window_labels == 1).mean():.1%})")

    return windows, window_labels


def extract_window_features(windows: np.ndarray, axis_names: list, dataset_name: str):
    """
    Extract statistical features from all windows.

    Parameters:
    -----------
    windows : numpy.ndarray
        Windows with shape (num_windows, window_size, num_features)
    axis_names : list
        Names of sensor axes
    dataset_name : str
        Name for logging

    Returns:
    --------
    feature_matrix : numpy.ndarray
        Feature matrix (num_windows, num_features)
    """
    print(f"\n[STEP] Extracting features from {dataset_name} windows...")
    print(f"  Extracting 5 features per axis (RMS, mean, std, skewness, kurtosis)")
    print(f"  Total features: {len(axis_names)} axes × 5 features = {len(axis_names) * 5}")

    feature_matrix = extract_features_batch(windows, axis_names)

    print(f"  Extracted features: {feature_matrix.shape}")

    return feature_matrix


def validate_features(features: np.ndarray, labels: np.ndarray, dataset_name: str):
    """
    Validate extracted features.

    Parameters:
    -----------
    features : numpy.ndarray
        Feature matrix
    labels : numpy.ndarray
        Window labels
    dataset_name : str
        Name for logging
    """
    print(f"\n[STEP] Validating {dataset_name} features...")

    # Check for NaN/Inf
    nan_count = np.isnan(features).sum()
    inf_count = np.isinf(features).sum()

    if nan_count > 0:
        raise ValueError(f"{dataset_name} features contain {nan_count} NaN values")

    if inf_count > 0:
        raise ValueError(f"{dataset_name} features contain {inf_count} Inf values")

    print(f"  No NaN or Inf values [OK]")

    # Check dimensions
    if features.shape[0] != labels.shape[0]:
        raise ValueError(f"Feature count ({features.shape[0]}) != label count ({labels.shape[0]})")

    print(f"  Feature dimensions: {features.shape} [OK]")
    print(f"  Labels: {labels.shape[0]} [OK]")

    # Check feature ranges
    feature_min = features.min(axis=0).mean()
    feature_max = features.max(axis=0).mean()
    print(f"  Feature ranges: min={feature_min:.2f}, max={feature_max:.2f} [OK]")


def save_feature_matrix(features: np.ndarray, labels: np.ndarray, feature_names: list,
                        output_path: str, dataset_name: str):
    """
    Save feature matrix to CSV.

    Parameters:
    -----------
    features : numpy.ndarray
        Feature matrix (num_windows, num_features)
    labels : numpy.ndarray
        Window labels (num_windows,)
    feature_names : list
        Column names for features
    output_path : str
        Path to save CSV
    dataset_name : str
        Name for logging
    """
    print(f"\n[STEP] Saving {dataset_name} feature matrix...")

    # Create DataFrame
    df = pd.DataFrame(features, columns=feature_names)
    df['label'] = labels

    # Save to CSV
    df.to_csv(output_path, index=False)

    print(f"  Saved {output_path}")
    print(f"  Shape: {df.shape[0]} windows × {df.shape[1]} columns (30 features + 1 label)")
    print(f"  File size: {os.path.getsize(output_path) / 1024:.1f} KB")


def main():
    """Main feature engineering pipeline."""
    import time
    start_time = time.time()

    print("=" * 70)
    print("FEATURE ENGINEERING PIPELINE (User Story 2)")
    print("=" * 70)

    # Parse arguments
    args = parse_arguments()
    input_dir = args.input
    output_dir = args.output
    window_size = args.window_size
    stride = args.stride

    print(f"\nConfiguration:")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Window size: {window_size} samples")
    print(f"  Stride: {stride} samples")

    try:
        # Step 1: Load preprocessed data
        X_train, X_test, y_train, y_test = load_preprocessed_data(input_dir)

        # Axis names (from preprocessing)
        axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

        # Step 2: Create sliding windows for train set
        train_windows, train_window_labels = create_windowed_data(
            X_train, y_train, window_size, stride, "train"
        )

        # Step 3: Create sliding windows for test set
        test_windows, test_window_labels = create_windowed_data(
            X_test, y_test, window_size, stride, "test"
        )

        # Step 4: Extract features from train windows
        train_features = extract_window_features(train_windows, axis_names, "train")

        # Step 5: Extract features from test windows
        test_features = extract_window_features(test_windows, axis_names, "test")

        # Step 6: Validate features
        validate_features(train_features, train_window_labels, "train")
        validate_features(test_features, test_window_labels, "test")

        # Step 7: Get feature names
        feature_names = get_feature_names(axis_names)

        # Step 8: Save feature matrices
        os.makedirs(output_dir, exist_ok=True)

        train_output = os.path.join(output_dir, "train_features.csv")
        save_feature_matrix(train_features, train_window_labels, feature_names, train_output, "train")

        test_output = os.path.join(output_dir, "test_features.csv")
        save_feature_matrix(test_features, test_window_labels, feature_names, test_output, "test")

        # Report completion
        total_time = time.time() - start_time

        print("\n" + "=" * 70)
        print("[OK] FEATURE ENGINEERING COMPLETE")
        print("=" * 70)
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Output directory: {output_dir}")
        print("\nGenerated files:")
        print(f"  - train_features.csv: {train_features.shape[0]} windows × {len(feature_names) + 1} columns")
        print(f"  - test_features.csv: {test_features.shape[0]} windows × {len(feature_names) + 1} columns")
        print("\nNext steps:")
        print("  - Use train_features.csv to train ML models (Random Forest, SVM, XGBoost)")
        print("  - Use test_features.csv for model evaluation")
        print("  - Run 3_sequence_preparation.py for DL sequence tensors")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
        print("Please run 1_preprocess.py first to generate preprocessed data.")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[ERROR] Validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
