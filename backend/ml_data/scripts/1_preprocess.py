#!/usr/bin/env python
"""
Dataset Preprocessing Script (User Story 1 - MVP)

Cleans, normalizes, and splits the raw tremor detection dataset into train/test sets.

Usage:
    python 1_preprocess.py [--input PATH] [--output DIR]

Outputs:
    - train_normalized.npy, test_normalized.npy
    - train_labels.npy, test_labels.npy
    - normalization_params.json
    - preprocessing_report.txt
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_loader import load_and_preprocess_csv
from utils.validators import (
    check_no_nulls,
    check_shapes,
    check_class_distribution,
    check_normalization,
    check_binary_labels
)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Preprocess tremor detection dataset")
    parser.add_argument(
        "--input",
        type=str,
        default="../../../Dataset.csv",
        help="Path to Dataset.csv (default: ../../../Dataset.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../processed/",
        help="Output directory (default: ../processed/)"
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    return parser.parse_args()


def detect_and_handle_nulls(features: np.ndarray, labels: np.ndarray, threshold: float = 0.05):
    """
    Detect and handle null values.

    Parameters:
    -----------
    features : numpy.ndarray
        Feature matrix
    labels : numpy.ndarray
        Label vector
    threshold : float
        If nulls < threshold (5%), drop rows; if >= threshold, impute with median

    Returns:
    --------
    features_clean, labels_clean : numpy.ndarray
        Cleaned data
    null_report : str
        Report of null handling actions
    """
    print("\n[STEP] Detecting and handling null values...")

    # Check for nulls
    null_mask = np.isnan(features).any(axis=1)
    null_count = null_mask.sum()
    null_pct = null_count / len(features)

    report_lines = []
    report_lines.append(f"Null detection:")
    report_lines.append(f"  Total samples: {len(features)}")
    report_lines.append(f"  Samples with nulls: {null_count} ({null_pct:.2%})")

    if null_count == 0:
        print(f"  No null values detected [OK]")
        report_lines.append("  Action: None (no nulls)")
        return features, labels, "\n".join(report_lines)

    if null_pct < threshold:
        # Drop rows with nulls
        print(f"  Nulls < {threshold:.0%}, dropping {null_count} rows...")
        features_clean = features[~null_mask]
        labels_clean = labels[~null_mask]
        action = f"Dropped {null_count} rows"
    else:
        # Impute with median
        print(f"  Nulls >= {threshold:.0%}, imputing with median...")
        features_clean = features.copy()
        for col in range(features.shape[1]):
            col_null_mask = np.isnan(features_clean[:, col])
            if col_null_mask.any():
                median = np.nanmedian(features_clean[:, col])
                features_clean[col_null_mask, col] = median
        labels_clean = labels
        action = f"Imputed {null_count} rows with median"

    report_lines.append(f"  Action: {action}")
    report_lines.append(f"  Remaining samples: {len(features_clean)}")

    print(f"  {action} [OK]")
    return features_clean, labels_clean, "\n".join(report_lines)


def split_train_test(features: np.ndarray, labels: np.ndarray, test_size: float = 0.2, random_state: int = 42):
    """
    Split data into stratified train/test sets.

    Parameters:
    -----------
    features, labels : numpy.ndarray
        Data to split
    test_size : float
        Proportion for test set (default: 0.2 = 20%)
    random_state : int
        Random seed for reproducibility

    Returns:
    --------
    X_train, X_test, y_train, y_test : numpy.ndarray
        Train and test splits
    split_report : str
        Report of split statistics
    """
    print(f"\n[STEP] Splitting data (80/20 stratified, random_state={random_state})...")

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        stratify=labels,
        random_state=random_state
    )

    # Calculate statistics
    train_size = len(X_train)
    test_size = len(X_test)
    total_size = len(features)

    train_class0_pct = (y_train == 0).mean() * 100
    train_class1_pct = (y_train == 1).mean() * 100
    test_class0_pct = (y_test == 0).mean() * 100
    test_class1_pct = (y_test == 1).mean() * 100

    print(f"  Train: {train_size} samples ({train_size/total_size:.1%})")
    print(f"    Class 0: {(y_train==0).sum()} ({train_class0_pct:.1f}%)")
    print(f"    Class 1: {(y_train==1).sum()} ({train_class1_pct:.1f}%)")
    print(f"  Test: {test_size} samples ({test_size/total_size:.1%})")
    print(f"    Class 0: {(y_test==0).sum()} ({test_class0_pct:.1f}%)")
    print(f"    Class 1: {(y_test==1).sum()} ({test_class1_pct:.1f}%)")

    report_lines = [
        "Train/Test Split:",
        f"  Method: Stratified random split",
        f"  Random seed: {random_state}",
        f"  Train: {train_size} samples ({train_class0_pct:.1f}% class 0, {train_class1_pct:.1f}% class 1)",
        f"  Test: {test_size} samples ({test_class0_pct:.1f}% class 0, {test_class1_pct:.1f}% class 1)"
    ]

    return X_train, X_test, y_train, y_test, "\n".join(report_lines)


def normalize_data(X_train: np.ndarray, X_test: np.ndarray):
    """
    Normalize data using z-score (StandardScaler).

    Fits scaler on train set ONLY, then transforms both train and test.

    Parameters:
    -----------
    X_train, X_test : numpy.ndarray
        Training and test features

    Returns:
    --------
    X_train_norm, X_test_norm : numpy.ndarray
        Normalized features
    scaler : StandardScaler
        Fitted scaler (for extracting mean/std)
    norm_report : str
        Report of normalization parameters
    """
    print("\n[STEP] Normalizing data (z-score: mean=0, std=1)...")
    print("  Fitting StandardScaler on training set ONLY...")

    scaler = StandardScaler()
    X_train_norm = scaler.fit_transform(X_train)
    X_test_norm = scaler.transform(X_test)

    # Extract parameters
    axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    means = scaler.mean_
    stds = scaler.scale_

    print("  Per-axis normalization parameters:")
    for i, axis in enumerate(axis_names):
        print(f"    {axis}: mean={means[i]:8.2f}, std={stds[i]:8.2f}")

    report_lines = ["Normalization:"]
    report_lines.append("  Method: Z-score (StandardScaler)")
    report_lines.append("  Fitted on: Training set only")
    report_lines.append("  Per-axis parameters:")
    for i, axis in enumerate(axis_names):
        report_lines.append(f"    {axis}: mean={means[i]:.2f}, std={stds[i]:.2f}")

    print("  Normalization complete [OK]")

    return X_train_norm, X_test_norm, scaler, "\n".join(report_lines)


def save_normalization_params(scaler: StandardScaler, output_dir: str, train_size: int, test_size: int, random_state: int):
    """Save normalization parameters to JSON."""
    axis_names = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

    params = {
        "method": "z-score",
        "description": "Standardization (mean=0, std=1) fitted on training set",
        "axes": axis_names,
        "mean": {axis: float(mean) for axis, mean in zip(axis_names, scaler.mean_)},
        "std": {axis: float(std) for axis, std in zip(axis_names, scaler.scale_)},
        "fitted_on": "train",
        "train_samples": train_size,
        "test_samples": test_size,
        "random_state": random_state,
        "created_at": datetime.now().isoformat(),
        "dataset_source": "Dataset.csv"
    }

    output_path = os.path.join(output_dir, "normalization_params.json")
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"\n[OUTPUT] Saved normalization parameters to {output_path}")


def save_processed_data(X_train: np.ndarray, X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray, output_dir: str):
    """Save processed data to .npy files."""
    print("\n[STEP] Saving processed data...")

    os.makedirs(output_dir, exist_ok=True)

    # Save feature arrays
    np.save(os.path.join(output_dir, "train_normalized.npy"), X_train)
    np.save(os.path.join(output_dir, "test_normalized.npy"), X_test)
    print(f"  Saved train_normalized.npy: {X_train.shape}")
    print(f"  Saved test_normalized.npy: {X_test.shape}")

    # Save label arrays
    np.save(os.path.join(output_dir, "train_labels.npy"), y_train)
    np.save(os.path.join(output_dir, "test_labels.npy"), y_test)
    print(f"  Saved train_labels.npy: {y_train.shape}")
    print(f"  Saved test_labels.npy: {y_test.shape}")

    print("  All files saved [OK]")


def generate_preprocessing_report(
    output_dir: str,
    null_report: str,
    split_report: str,
    norm_report: str,
    total_time: float
):
    """Generate and save preprocessing report."""
    report_lines = [
        "=" * 70,
        "PREPROCESSING REPORT",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total processing time: {total_time:.2f} seconds",
        "",
        null_report,
        "",
        split_report,
        "",
        norm_report,
        "",
        "=" * 70,
        "VALIDATION CHECKS PASSED",
        "=" * 70,
        "[OK] No NaN or Inf values",
        "[OK] Shapes correct",
        "[OK] Class distribution preserved (±2% tolerance)",
        "[OK] Normalization correct (mean~0, std~1)",
        "[OK] Labels are binary (0 or 1)",
        "",
        "Preprocessing complete. Data ready for ML/DL experiments.",
        "=" * 70
    ]

    report_path = os.path.join(output_dir, "preprocessing_report.txt")
    with open(report_path, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"\n[OUTPUT] Saved preprocessing report to {report_path}")


def main():
    """Main preprocessing pipeline."""
    import time
    start_time = time.time()

    print("=" * 70)
    print("DATASET PREPROCESSING PIPELINE (User Story 1 - MVP)")
    print("=" * 70)

    # Parse arguments
    args = parse_arguments()
    input_path = args.input
    output_dir = args.output
    random_state = args.random_state

    print(f"\nConfiguration:")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Random state: {random_state}")

    try:
        # Step 1: Load and validate CSV
        print("\n[STEP] Loading and validating dataset...")
        features, labels = load_and_preprocess_csv(input_path)

        # Step 2: Handle nulls
        features, labels, null_report = detect_and_handle_nulls(features, labels)

        # Step 3: Verify binary labels
        check_binary_labels(labels, "Initial labels")

        # Step 4: Split train/test
        X_train, X_test, y_train, y_test, split_report = split_train_test(
            features, labels, test_size=0.2, random_state=random_state
        )

        # Step 5: Normalize
        X_train_norm, X_test_norm, scaler, norm_report = normalize_data(X_train, X_test)

        # Step 6: Validation checks
        print("\n[STEP] Running validation checks...")
        check_no_nulls(X_train_norm, "X_train_norm")
        check_no_nulls(X_test_norm, "X_test_norm")
        check_shapes(X_train_norm, X_test_norm, y_train, y_test, len(X_train), len(X_test), 6)
        check_class_distribution(y_train, y_test, tolerance=0.02)
        check_normalization(X_train_norm, mean_tolerance=1e-6, std_tolerance=0.1)
        check_binary_labels(y_train, "y_train")
        check_binary_labels(y_test, "y_test")

        # Step 7: Save outputs
        save_processed_data(X_train_norm, X_test_norm, y_train, y_test, output_dir)
        save_normalization_params(scaler, output_dir, len(y_train), len(y_test), random_state)

        # Step 8: Generate report
        total_time = time.time() - start_time
        generate_preprocessing_report(output_dir, null_report, split_report, norm_report, total_time)

        print("\n" + "=" * 70)
        print("[OK] PREPROCESSING COMPLETE")
        print("=" * 70)
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Output directory: {output_dir}")
        print("\nNext steps:")
        print("  - Run 2_feature_engineering.py for ML feature matrices")
        print("  - Run 3_sequence_preparation.py for DL sequence tensors")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
        print("Please ensure Dataset.csv is at the correct location.")
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
