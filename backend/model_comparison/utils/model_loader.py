"""
Model Loader Utility

Unified interface for loading both scikit-learn (.pkl) and TensorFlow/Keras (.h5) models
with their associated metadata JSON files.
"""

import os
import json
import logging
import joblib
from typing import Dict, Any, Tuple, Optional

# Try to import TensorFlow, but allow script to run without it for ML-only comparison
try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    tf = None

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Unified model loader for scikit-learn and TensorFlow/Keras models.

    Supports loading:
    - scikit-learn models: .pkl files via joblib
    - TensorFlow/Keras models: .h5 files via tf.keras.models.load_model
    - Metadata: .json files with model performance metrics and training info
    """

    @staticmethod
    def load_model(model_path: str, model_type: str) -> Any:
        """
        Load a trained model from file.

        Args:
            model_path: Absolute path to model file (.pkl or .h5)
            model_type: Model type identifier ('rf', 'svm', 'lstm', 'cnn_1d')

        Returns:
            Loaded model object (scikit-learn estimator or Keras model)

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model_type is invalid
            Exception: If model loading fails
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            if model_type in ['rf', 'svm']:
                # scikit-learn models (ML)
                logger.debug(f"Loading scikit-learn model from {model_path}")
                model = joblib.load(model_path)
                logger.info(f"✓ Loaded {model_type.upper()} model: {type(model).__name__}")
                return model

            elif model_type in ['lstm', 'cnn_1d']:
                # TensorFlow/Keras models (DL)
                if not HAS_TENSORFLOW:
                    raise ImportError(f"TensorFlow is required to load {model_type.upper()} models. "
                                    f"Install with: pip install tensorflow>=2.13.0")
                logger.debug(f"Loading TensorFlow/Keras model from {model_path}")
                model = tf.keras.models.load_model(model_path)
                logger.info(f"✓ Loaded {model_type.upper()} model: {model.name}")
                return model

            else:
                raise ValueError(f"Invalid model_type: {model_type}. "
                               f"Expected one of: 'rf', 'svm', 'lstm', 'cnn_1d'")

        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise

    @staticmethod
    def load_metadata(metadata_path: str) -> Dict[str, Any]:
        """
        Load model metadata from JSON file.

        Args:
            metadata_path: Absolute path to metadata JSON file

        Returns:
            Dictionary containing model metadata:
                - model_type: "ML" or "DL"
                - performance_metrics: accuracy, precision, recall, F1, confusion_matrix
                - training_history: epochs, training_time, etc.
                - training_info: timestamp, samples, features, versions

        Raises:
            FileNotFoundError: If metadata file doesn't exist
            json.JSONDecodeError: If JSON is malformed
        """
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            logger.debug(f"Loaded metadata from {metadata_path}")
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in metadata file {metadata_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load metadata from {metadata_path}: {e}")
            raise

    @staticmethod
    def load_model_with_metadata(model_path: str, metadata_path: str,
                                 model_type: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Load both model and metadata together.

        Args:
            model_path: Path to model file
            metadata_path: Path to metadata JSON file
            model_type: Model type identifier

        Returns:
            Tuple of (model, metadata)

        Raises:
            FileNotFoundError: If either file doesn't exist
        """
        model = ModelLoader.load_model(model_path, model_type)
        metadata = ModelLoader.load_metadata(metadata_path)
        return model, metadata

    @staticmethod
    def detect_model_type_from_path(model_path: str) -> Optional[str]:
        """
        Detect model type from file path.

        Args:
            model_path: Path to model file

        Returns:
            Detected model type ('rf', 'svm', 'lstm', 'cnn_1d') or None
        """
        basename = os.path.basename(model_path).lower()

        if 'rf' in basename or 'random_forest' in basename:
            return 'rf'
        elif 'svm' in basename:
            return 'svm'
        elif 'lstm' in basename:
            return 'lstm'
        elif 'cnn' in basename or '1d_cnn' in basename:
            return 'cnn_1d'
        else:
            return None
