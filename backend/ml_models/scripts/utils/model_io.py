"""
Model I/O and Data Loading Utilities

Functions for saving/loading trained models, managing metadata,
and loading feature data for training.
"""

import json
import os
from datetime import datetime
from typing import Dict, Tuple, Any
import joblib
import pandas as pd
import numpy as np
import sklearn
import sys


def load_feature_data(train_path: str, test_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load training and test feature matrices from CSV files.

    Args:
        train_path: Path to train_features.csv
        test_path: Path to test_features.csv

    Returns:
        Tuple of (X_train, y_train, X_test, y_test) as numpy arrays

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If data has unexpected format
    """
    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Training data not found: {train_path}")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test data not found: {test_path}")

    # Load CSV files
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    # Validate structure
    if 'label' not in train_df.columns:
        raise ValueError("Training data missing 'label' column")
    if 'label' not in test_df.columns:
        raise ValueError("Test data missing 'label' column")

    # Split features and labels
    X_train = train_df.drop('label', axis=1).values
    y_train = train_df['label'].values
    X_test = test_df.drop('label', axis=1).values
    y_test = test_df['label'].values

    return X_train, y_train, X_test, y_test


def save_model(model: Any, metadata: Dict, output_dir: str, model_name: str) -> Tuple[str, str]:
    """
    Save trained model and metadata to disk.

    Args:
        model: Trained scikit-learn model object
        metadata: Dict containing hyperparameters, metrics, training info
        output_dir: Directory to save files (e.g., backend/ml_models/models/)
        model_name: Base name for files (e.g., "random_forest", "svm_rbf")

    Returns:
        Tuple of (model_path, metadata_path)

    Raises:
        IOError: If file writing fails
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    model_path = os.path.join(output_dir, f"{model_name}.pkl")
    metadata_path = os.path.join(output_dir, f"{model_name}.json")

    # Save model using joblib (efficient for scikit-learn models)
    joblib.dump(model, model_path)

    # Save metadata as JSON
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    return model_path, metadata_path


def load_model(model_path: str, metadata_path: str) -> Tuple[Any, Dict]:
    """
    Load trained model and metadata from disk.

    Args:
        model_path: Path to .pkl model file
        metadata_path: Path to .json metadata file

    Returns:
        Tuple of (model, metadata)

    Raises:
        FileNotFoundError: If model files don't exist
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    # Load model
    model = joblib.load(model_path)

    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    return model, metadata


def create_metadata(
    model_type: str,
    hyperparameters: Dict,
    performance_metrics: Dict,
    cross_validation: Dict,
    training_info: Dict
) -> Dict:
    """
    Create metadata dictionary for a trained model.

    Args:
        model_type: Name of model class (e.g., "RandomForestClassifier", "SVC")
        hyperparameters: Dict of model hyperparameters
        performance_metrics: Dict with accuracy, precision, recall, f1_score, confusion_matrix, meets_threshold
        cross_validation: Dict with cv_scores, cv_mean, cv_std
        training_info: Dict with timestamp, training_time_seconds, etc.

    Returns:
        Complete metadata dictionary
    """
    # Ensure training info has required fields
    if 'timestamp' not in training_info:
        training_info['timestamp'] = datetime.now().isoformat()
    if 'sklearn_version' not in training_info:
        training_info['sklearn_version'] = sklearn.__version__
    if 'python_version' not in training_info:
        training_info['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    metadata = {
        "model_type": model_type,
        "hyperparameters": hyperparameters,
        "performance_metrics": performance_metrics,
        "cross_validation": cross_validation,
        "training_info": training_info
    }

    return metadata
