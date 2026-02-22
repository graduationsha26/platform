#!/usr/bin/env python
"""
Sequence Preparation Script (User Story 3)

Creates fixed-length sequence tensors for deep learning models (LSTM, CNN, hybrid).

Usage:
    python 3_sequence_preparation.py [--input DIR] [--output DIR]

Outputs:
    - train_sequences.npy (3D tensor: num_windows × 128 × 6)
    - test_sequences.npy (3D tensor: num_windows × 128 × 6)
    - train_seq_labels.npy (labels for train sequences)
    - test_seq_labels.npy (labels for test sequences)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.windowing import create_windows_with_labels, pad_incomplete_window


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Prepare sequences for deep learning models")
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
        help="Output directory for sequence tensors (default: ../processed/)"
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=128,
        help="Sequence length in samples (default: 128 samples = 1.28s at 100Hz)"
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=64,
        help="Stride in samples (default: 64 samples = 50%% overlap)"
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


def create_sequences(X: np.ndarray, y: np.ndarray, sequence_length: int, stride: int,
                     dataset_name: str, pad_incomplete: bool = True):
    """
    Create fixed-length sequences from continuous data.

    Parameters:
    -----------
    X : numpy.ndarray
        Feature data (samples, features)
    y : numpy.ndarray
        Labels (samples,)
    sequence_length : int
        Number of samples per sequence
    stride : int
        Number of samples to shift between sequences
    dataset_name : str
        Name for logging (e.g., "train", "test")
    pad_incomplete : bool
        Whether to zero-pad incomplete sequences at boundaries

    Returns:
    --------
    sequences : numpy.ndarray
        Sequences with shape (num_sequences, sequence_length, num_features)
    sequence_labels : numpy.ndarray
        Labels for each sequence (num_sequences,)
    padded_count : int
        Number of padded sequences
    """
    print(f"\n[STEP] Creating sequences for {dataset_name} set...")
    print(f"  Sequence length: {sequence_length} samples (1.28 seconds at 100Hz)")
    print(f"  Stride: {stride} samples (50% overlap)")

    # Create windows using sliding window utility
    sequences, sequence_labels = create_windows_with_labels(X, y, sequence_length, stride)

    padded_count = 0

    # Handle incomplete sequence at end if needed
    if pad_incomplete:
        remaining_samples = len(X) - (len(sequences) * stride)
        if remaining_samples > 0 and remaining_samples < sequence_length:
            print(f"  Found incomplete sequence at end: {remaining_samples} samples")
            print(f"  Padding to {sequence_length} samples with zeros...")

            # Get remaining data
            start_idx = len(sequences) * stride
            incomplete_window = X[start_idx:]
            incomplete_labels = y[start_idx:]

            # Pad window
            padded_window, is_padded = pad_incomplete_window(incomplete_window, sequence_length)

            if is_padded:
                # Assign label using majority voting on non-padded portion
                unique, counts = np.unique(incomplete_labels, return_counts=True)
                label_counts = dict(zip(unique, counts))
                label = 1 if label_counts.get(1, 0) >= label_counts.get(0, 0) else 0

                # Add padded sequence
                sequences = np.vstack([sequences, padded_window[np.newaxis, :, :]])
                sequence_labels = np.append(sequence_labels, label)
                padded_count = 1

    print(f"  Created {len(sequences)} sequences")
    print(f"    Regular sequences: {len(sequences) - padded_count}")
    print(f"    Padded sequences: {padded_count}")
    print(f"    Class 0: {(sequence_labels == 0).sum()} ({(sequence_labels == 0).mean():.1%})")
    print(f"    Class 1: {(sequence_labels == 1).sum()} ({(sequence_labels == 1).mean():.1%})")

    return sequences, sequence_labels, padded_count


def validate_sequences(sequences: np.ndarray, labels: np.ndarray,
                       expected_shape: tuple, dataset_name: str):
    """
    Validate sequence tensors.

    Parameters:
    -----------
    sequences : numpy.ndarray
        Sequence tensor (num_sequences, sequence_length, num_features)
    labels : numpy.ndarray
        Sequence labels (num_sequences,)
    expected_shape : tuple
        Expected shape (sequence_length, num_features)
    dataset_name : str
        Name for logging
    """
    print(f"\n[STEP] Validating {dataset_name} sequences...")

    # Check 3D shape
    if len(sequences.shape) != 3:
        raise ValueError(f"Expected 3D tensor, got shape {sequences.shape}")

    expected_full_shape = (sequences.shape[0], expected_shape[0], expected_shape[1])
    if sequences.shape[1:] != expected_shape:
        raise ValueError(
            f"Sequence shape mismatch: got {sequences.shape}, expected (N, {expected_shape[0]}, {expected_shape[1]})"
        )

    print(f"  3D tensor shape: {sequences.shape} [OK]")
    print(f"    Format: ({sequences.shape[0]} sequences, {sequences.shape[1]} timesteps, {sequences.shape[2]} features)")

    # Check for NaN/Inf
    nan_count = np.isnan(sequences).sum()
    inf_count = np.isinf(sequences).sum()

    if nan_count > 0:
        raise ValueError(f"{dataset_name} sequences contain {nan_count} NaN values")

    if inf_count > 0:
        raise ValueError(f"{dataset_name} sequences contain {inf_count} Inf values")

    print(f"  No NaN or Inf values [OK]")

    # Check label count matches sequence count
    if len(labels) != sequences.shape[0]:
        raise ValueError(
            f"Label count ({len(labels)}) != sequence count ({sequences.shape[0]})"
        )

    print(f"  Label count matches sequence count: {len(labels)} [OK]")

    # Check data type
    print(f"  Data type: {sequences.dtype} [OK]")

    # Check value ranges
    seq_min = sequences.min()
    seq_max = sequences.max()
    seq_mean = sequences.mean()
    seq_std = sequences.std()

    print(f"  Value ranges: min={seq_min:.2f}, max={seq_max:.2f}, mean={seq_mean:.2f}, std={seq_std:.2f} [OK]")


def save_sequences(sequences: np.ndarray, labels: np.ndarray, output_dir: str,
                   dataset_name: str, padded_count: int):
    """
    Save sequence tensors to .npy files.

    Parameters:
    -----------
    sequences : numpy.ndarray
        Sequence tensor (num_sequences, sequence_length, num_features)
    labels : numpy.ndarray
        Sequence labels (num_sequences,)
    output_dir : str
        Output directory
    dataset_name : str
        Name for output files (e.g., "train", "test")
    padded_count : int
        Number of padded sequences (for reporting)
    """
    print(f"\n[STEP] Saving {dataset_name} sequences...")

    os.makedirs(output_dir, exist_ok=True)

    # Save sequences
    seq_path = os.path.join(output_dir, f"{dataset_name}_sequences.npy")
    np.save(seq_path, sequences)
    seq_size_mb = os.path.getsize(seq_path) / (1024 * 1024)

    print(f"  Saved {seq_path}")
    print(f"    Shape: {sequences.shape}")
    print(f"    Size: {seq_size_mb:.2f} MB")

    # Save labels
    labels_path = os.path.join(output_dir, f"{dataset_name}_seq_labels.npy")
    np.save(labels_path, labels)
    labels_size_kb = os.path.getsize(labels_path) / 1024

    print(f"  Saved {labels_path}")
    print(f"    Shape: {labels.shape}")
    print(f"    Size: {labels_size_kb:.2f} KB")

    if padded_count > 0:
        print(f"  NOTE: {padded_count} sequence(s) were zero-padded at dataset boundaries")


def main():
    """Main sequence preparation pipeline."""
    import time
    start_time = time.time()

    print("=" * 70)
    print("SEQUENCE PREPARATION PIPELINE (User Story 3)")
    print("=" * 70)

    # Parse arguments
    args = parse_arguments()
    input_dir = args.input
    output_dir = args.output
    sequence_length = args.sequence_length
    stride = args.stride

    print(f"\nConfiguration:")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Sequence length: {sequence_length} samples")
    print(f"  Stride: {stride} samples")

    try:
        # Step 1: Load preprocessed data
        X_train, X_test, y_train, y_test = load_preprocessed_data(input_dir)

        # Step 2: Create sequences for train set
        train_sequences, train_labels, train_padded = create_sequences(
            X_train, y_train, sequence_length, stride, "train", pad_incomplete=True
        )

        # Step 3: Create sequences for test set
        test_sequences, test_labels, test_padded = create_sequences(
            X_test, y_test, sequence_length, stride, "test", pad_incomplete=True
        )

        # Step 4: Validate sequences
        expected_shape = (sequence_length, 6)  # (128 timesteps, 6 features)
        validate_sequences(train_sequences, train_labels, expected_shape, "train")
        validate_sequences(test_sequences, test_labels, expected_shape, "test")

        # Step 5: Save sequences
        save_sequences(train_sequences, train_labels, output_dir, "train", train_padded)
        save_sequences(test_sequences, test_labels, output_dir, "test", test_padded)

        # Report completion
        total_time = time.time() - start_time

        print("\n" + "=" * 70)
        print("[OK] SEQUENCE PREPARATION COMPLETE")
        print("=" * 70)
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Output directory: {output_dir}")
        print("\nGenerated files:")
        print(f"  - train_sequences.npy: {train_sequences.shape}")
        print(f"  - test_sequences.npy: {test_sequences.shape}")
        print(f"  - train_seq_labels.npy: {train_labels.shape}")
        print(f"  - test_seq_labels.npy: {test_labels.shape}")
        print("\nTensor format:")
        print(f"  - Shape: (num_sequences, {sequence_length}, 6)")
        print(f"  - Compatible with: LSTM, CNN, Conv-LSTM, Transformer models")
        print(f"  - Features: [aX, aY, aZ, gX, gY, gZ] (normalized)")
        print("\nNext steps:")
        print("  - Use train_sequences.npy to train DL models (LSTM, CNN, hybrid)")
        print("  - Use test_sequences.npy for model evaluation")
        print("  - Load with: np.load('train_sequences.npy')")
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
