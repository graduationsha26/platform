"""
Model I/O Utilities

Functions for loading sequence data, saving/loading models, and creating metadata.
"""

import os
import json
import numpy as np
import tensorflow as tf
from typing import Tuple, Dict, Any


def load_sequence_data(train_path: str, test_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load training and test sequence data from .npy files.

    Args:
        train_path: Path to directory containing train_sequences.npy and train_seq_labels.npy
        test_path: Path to directory containing test_sequences.npy and test_seq_labels.npy

    Returns:
        Tuple of (X_train, y_train, X_test, y_test)
        - X_train: Training sequences (N, timesteps, features)
        - y_train: Training labels (N,)
        - X_test: Test sequences (M, timesteps, features)
        - y_test: Test labels (M,)

    Raises:
        FileNotFoundError: If sequence files don't exist
        ValueError: If data shapes or values are invalid
    """
    # Construct file paths
    train_sequences_file = os.path.join(train_path, 'train_sequences.npy')
    train_labels_file = os.path.join(train_path, 'train_seq_labels.npy')
    test_sequences_file = os.path.join(test_path, 'test_sequences.npy')
    test_labels_file = os.path.join(test_path, 'test_seq_labels.npy')

    # Check if files exist
    for filepath in [train_sequences_file, train_labels_file, test_sequences_file, test_labels_file]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Required file not found: {filepath}")

    # Load data
    X_train = np.load(train_sequences_file)
    y_train = np.load(train_labels_file)
    X_test = np.load(test_sequences_file)
    y_test = np.load(test_labels_file)

    return X_train, y_train, X_test, y_test


def save_model(model: Any, metadata: Dict, output_dir: str, model_name: str) -> Tuple[str, str]:
    """
    Save trained model and metadata to disk.

    Args:
        model: Trained Keras model
        metadata: Metadata dictionary (from create_metadata)
        output_dir: Directory to save files
        model_name: Base name for model files (e.g., "lstm_model")

    Returns:
        Tuple of (model_path, metadata_path)

    Raises:
        OSError: If save fails due to disk/permissions
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Construct file paths
    model_path = os.path.join(output_dir, f"{model_name}.h5")
    metadata_path = os.path.join(output_dir, f"{model_name}.json")

    # Save model as .h5 format
    model.save(model_path)

    # Save metadata as JSON
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    return model_path, metadata_path


def load_model(model_path: str, metadata_path: str) -> Tuple[Any, Dict]:
    """
    Load trained model and metadata from disk.

    Args:
        model_path: Path to .h5 model file
        metadata_path: Path to .json metadata file

    Returns:
        Tuple of (model, metadata)

    Raises:
        FileNotFoundError: If files don't exist
    """
    # Check if files exist
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    # Load model
    model = tf.keras.models.load_model(model_path)

    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    return model, metadata


def create_metadata(
    model_type: str,
    architecture_summary: str,
    hyperparameters: Dict,
    performance_metrics: Dict,
    training_history: Dict,
    training_info: Dict
) -> Dict:
    """
    Create metadata dictionary for model export.

    Args:
        model_type: Model architecture type (e.g., "LSTM", "CNN1D")
        architecture_summary: Output of model.summary() as string
        hyperparameters: Dictionary of hyperparameters used for training
        performance_metrics: Dictionary of performance metrics (from evaluate_model)
        training_history: Dictionary of training history (epochs, losses, accuracies)
        training_info: Dictionary of training information (timestamp, versions, etc.)

    Returns:
        Complete metadata dictionary ready for JSON serialization
    """
    import tensorflow as tf
    import sys

    # Add TensorFlow and Python versions to training_info if not present
    if 'tensorflow_version' not in training_info:
        training_info['tensorflow_version'] = tf.__version__
    if 'python_version' not in training_info:
        training_info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    metadata = {
        "model_type": model_type,
        "architecture_summary": architecture_summary,
        "hyperparameters": hyperparameters,
        "performance_metrics": performance_metrics,
        "training_history": training_history,
        "training_info": training_info
    }

    return metadata
