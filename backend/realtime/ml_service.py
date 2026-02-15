"""
Machine learning prediction service for tremor severity analysis.

This module provides ML-based prediction of tremor severity using:
- scikit-learn models (.pkl) for classical ML algorithms
- TensorFlow/Keras models (.h5) for deep learning

The service uses a singleton pattern to ensure models are loaded once
and shared across all MQTT message processing.
"""
import os
import logging
import threading
from typing import Optional, Dict, Tuple
from pathlib import Path

import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class MLPredictionService:
    """
    Singleton service for ML-based tremor severity prediction.

    This service:
    - Loads ML models on first instantiation (lazy loading)
    - Caches models in memory for fast inference
    - Thread-safe for concurrent MQTT message processing
    - Extracts features from raw sensor data
    - Generates predictions with confidence scores

    Models expected:
    - backend/models/tremor_classifier.pkl (scikit-learn)
    - backend/models/tremor_classifier.h5 (TensorFlow/Keras) - optional

    Prediction output:
    {
        "severity": "mild" | "moderate" | "severe",
        "confidence": 0.0-1.0
    }
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        Singleton pattern: ensure only one instance exists.

        Thread-safe implementation using double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize ML models (lazy loading on first access).

        Loads models from backend/models/ directory:
        - tremor_classifier.pkl (required)
        - tremor_classifier.h5 (optional)
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info("Initializing MLPredictionService...")

            self.sklearn_model = None
            self.keras_model = None
            self.models_dir = self._get_models_dir()

            # Load scikit-learn model
            self._load_sklearn_model()

            # Load Keras model (optional)
            self._load_keras_model()

            self._initialized = True
            logger.info("MLPredictionService initialized successfully")

    def _get_models_dir(self) -> Path:
        """
        Get the models directory path.

        Returns:
            Path to backend/models/ directory
        """
        backend_dir = Path(settings.BASE_DIR)
        models_dir = backend_dir / 'models'

        # Create models directory if it doesn't exist
        models_dir.mkdir(exist_ok=True)

        return models_dir

    def _load_sklearn_model(self):
        """
        Load scikit-learn model from .pkl file.

        Expected file: backend/models/tremor_classifier.pkl
        """
        try:
            import joblib

            model_path = self.models_dir / 'tremor_classifier.pkl'

            if not model_path.exists():
                logger.warning(f"scikit-learn model not found at {model_path}. ML predictions will be disabled.")
                return

            self.sklearn_model = joblib.load(model_path)
            logger.info(f"scikit-learn model loaded successfully from {model_path}")

        except ImportError:
            logger.warning("joblib not installed. scikit-learn model loading disabled.")
        except Exception as e:
            logger.error(f"Failed to load scikit-learn model: {e}", exc_info=True)

    def _load_keras_model(self):
        """
        Load TensorFlow/Keras model from .h5 file.

        Expected file: backend/models/tremor_classifier.h5
        """
        try:
            from tensorflow import keras

            model_path = self.models_dir / 'tremor_classifier.h5'

            if not model_path.exists():
                logger.info(f"Keras model not found at {model_path}. Using scikit-learn model only.")
                return

            self.keras_model = keras.models.load_model(model_path)
            logger.info(f"Keras model loaded successfully from {model_path}")

        except ImportError:
            logger.info("TensorFlow not installed. Keras model loading disabled.")
        except Exception as e:
            logger.error(f"Failed to load Keras model: {e}", exc_info=True)

    def _extract_features(self, sensor_data: Dict) -> Optional[np.ndarray]:
        """
        Extract features from raw sensor data for ML prediction.

        Features extracted:
        - tremor_intensity_avg: Average of tremor intensity values
        - tremor_intensity_max: Maximum tremor intensity
        - tremor_intensity_std: Standard deviation of tremor intensity
        - frequency: Tremor frequency in Hz

        Args:
            sensor_data: Dict containing:
                - tremor_intensity: List[float] (0.0-1.0 range)
                - frequency: float (Hz)
                - timestamps: List[str] (ISO format)

        Returns:
            numpy array of shape (1, n_features) or None if extraction fails
        """
        try:
            tremor_intensity = sensor_data.get('tremor_intensity', [])
            frequency = sensor_data.get('frequency', 0.0)

            if not tremor_intensity or frequency <= 0:
                logger.warning("Invalid sensor data for feature extraction")
                return None

            # Convert to numpy array
            tremor_array = np.array(tremor_intensity)

            # Extract statistical features
            tremor_avg = np.mean(tremor_array)
            tremor_max = np.max(tremor_array)
            tremor_std = np.std(tremor_array)

            # Combine features
            features = np.array([[
                tremor_avg,
                tremor_max,
                tremor_std,
                frequency
            ]])

            logger.debug(f"Extracted features: avg={tremor_avg:.3f}, max={tremor_max:.3f}, std={tremor_std:.3f}, freq={frequency:.2f}")

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            return None

    def predict_severity(self, sensor_data: Dict) -> Optional[Dict[str, any]]:
        """
        Predict tremor severity from sensor data.

        Prediction flow:
        1. Extract features from sensor data
        2. Preprocess features (normalization if needed)
        3. Call sklearn model.predict() for severity class
        4. Call model.predict_proba() for confidence score
        5. Map class index to severity label

        Args:
            sensor_data: Dict containing tremor_intensity, frequency, timestamps

        Returns:
            Dict with prediction:
            {
                "severity": "mild" | "moderate" | "severe",
                "confidence": 0.0-1.0
            }
            or None if prediction fails
        """
        try:
            # Check if model is available
            if self.sklearn_model is None and self.keras_model is None:
                logger.warning("No ML models available for prediction")
                return None

            # Extract features
            features = self._extract_features(sensor_data)
            if features is None:
                return None

            # Use sklearn model if available (primary)
            if self.sklearn_model is not None:
                return self._predict_with_sklearn(features)

            # Fallback to Keras model
            elif self.keras_model is not None:
                return self._predict_with_keras(features)

            return None

        except Exception as e:
            logger.error(f"ML prediction failed: {e}", exc_info=True)
            return None

    def _predict_with_sklearn(self, features: np.ndarray) -> Optional[Dict[str, any]]:
        """
        Generate prediction using scikit-learn model.

        Args:
            features: numpy array of shape (1, n_features)

        Returns:
            Prediction dict or None
        """
        try:
            # Get class prediction
            class_index = self.sklearn_model.predict(features)[0]

            # Get confidence scores
            if hasattr(self.sklearn_model, 'predict_proba'):
                probabilities = self.sklearn_model.predict_proba(features)[0]
                confidence = float(np.max(probabilities))
            else:
                confidence = 1.0  # No probability support

            # Map class index to severity label
            severity_map = {
                0: 'mild',
                1: 'moderate',
                2: 'severe'
            }
            severity = severity_map.get(int(class_index), 'moderate')

            logger.info(f"ML prediction: severity={severity}, confidence={confidence:.2f}")

            return {
                'severity': severity,
                'confidence': confidence
            }

        except Exception as e:
            logger.error(f"sklearn prediction failed: {e}", exc_info=True)
            return None

    def _predict_with_keras(self, features: np.ndarray) -> Optional[Dict[str, any]]:
        """
        Generate prediction using Keras model.

        Args:
            features: numpy array of shape (1, n_features)

        Returns:
            Prediction dict or None
        """
        try:
            # Get probability predictions
            probabilities = self.keras_model.predict(features, verbose=0)[0]

            # Get class with highest probability
            class_index = np.argmax(probabilities)
            confidence = float(probabilities[class_index])

            # Map class index to severity label
            severity_map = {
                0: 'mild',
                1: 'moderate',
                2: 'severe'
            }
            severity = severity_map.get(int(class_index), 'moderate')

            logger.info(f"ML prediction (Keras): severity={severity}, confidence={confidence:.2f}")

            return {
                'severity': severity,
                'confidence': confidence
            }

        except Exception as e:
            logger.error(f"Keras prediction failed: {e}", exc_info=True)
            return None
