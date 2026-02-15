"""Business logic services for inference."""

import joblib
import json
import os
import time
from pathlib import Path
from typing import Dict, Tuple, Any, Optional

# import tensorflow as tf  # Will be imported when needed
import numpy as np

from django.conf import settings

from .exceptions import ModelNotFoundError, ModelLoadError, InferenceTimeoutError


class ModelCache:
    """
    Singleton cache for loaded ML/DL models.

    Implements lazy loading: models are loaded on first access and cached in memory
    for subsequent requests. This eliminates 500ms-2s load time per request.

    Thread-safe for concurrent predictions (models are read-only after loading).
    """

    _instance = None
    _models = {}  # {model_name: (model_object, metadata_dict)}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self, model_name: str) -> Tuple[Any, Dict]:
        """
        Get model from cache or load if not cached.

        Args:
            model_name: Model identifier (rf, svm, lstm, cnn_1d)

        Returns:
            Tuple of (model_object, metadata_dict)

        Raises:
            ModelNotFoundError: If model file doesn't exist
            ModelLoadError: If model loading fails
        """
        # Check cache first
        if model_name in self._models:
            return self._models[model_name]

        # Load model and cache it
        model_loader = ModelLoader()
        model_path = model_loader._get_model_path(model_name)
        metadata_path = model_loader._get_metadata_path(model_name)

        # Verify files exist
        if not os.path.exists(model_path):
            raise ModelNotFoundError(
                f"Model file not found: {model_name}. "
                f"Please ensure Feature 005 (ML models) or Feature 006 (DL models) is complete."
            )

        if not os.path.exists(metadata_path):
            raise ModelNotFoundError(
                f"Model metadata not found: {model_name}. "
                f"Expected metadata file at {metadata_path}"
            )

        # Load model and metadata
        model_obj = model_loader.load_model(model_path)
        metadata = model_loader.load_metadata(metadata_path)

        # Cache for future requests
        self._models[model_name] = (model_obj, metadata)

        return model_obj, metadata

    def clear_cache(self):
        """Clear all cached models (useful for testing or reloading)."""
        self._models.clear()


class ModelLoader:
    """
    Service for loading ML/DL models and their metadata.

    Supports:
    - scikit-learn models (.pkl via joblib)
    - TensorFlow/Keras models (.h5 via tf.keras)
    - Model metadata from JSON files
    """

    @staticmethod
    def load_model(model_path: str):
        """
        Load model from file.

        Args:
            model_path: Path to model file (.pkl or .h5)

        Returns:
            Loaded model object

        Raises:
            ModelLoadError: If loading fails
        """
        try:
            file_ext = Path(model_path).suffix.lower()

            if file_ext == '.pkl':
                # Load scikit-learn model
                model = joblib.load(model_path)
                return model

            elif file_ext in ['.h5', '.keras']:
                # Load TensorFlow/Keras model
                import tensorflow as tf
                model = tf.keras.models.load_model(model_path)
                return model

            else:
                raise ValueError(f"Unsupported model file extension: {file_ext}")

        except Exception as e:
            raise ModelLoadError(
                f"Failed to load model from {model_path}: {str(e)}"
            )

    @staticmethod
    def load_metadata(metadata_path: str) -> Dict:
        """
        Load model metadata from JSON file.

        Args:
            metadata_path: Path to metadata JSON file

        Returns:
            Metadata dictionary

        Raises:
            ModelLoadError: If metadata loading fails
        """
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            raise ModelLoadError(
                f"Failed to load metadata from {metadata_path}: {str(e)}"
            )

    @staticmethod
    def detect_model_type(model_path: str) -> str:
        """
        Detect model type from file extension.

        Args:
            model_path: Path to model file

        Returns:
            'ml' for .pkl files, 'dl' for .h5/.keras files

        Raises:
            ValueError: If file extension not recognized
        """
        file_ext = Path(model_path).suffix.lower()

        if file_ext == '.pkl':
            return 'ml'
        elif file_ext in ['.h5', '.keras']:
            return 'dl'
        else:
            raise ValueError(f"Cannot detect model type from extension: {file_ext}")

    def _get_model_path(self, model_name: str) -> str:
        """
        Get full path to model file.

        Args:
            model_name: Model identifier (rf, svm, lstm, cnn_1d)

        Returns:
            Full path to model file
        """
        from django.conf import settings

        # Map model names to file paths
        model_map = {
            'rf': settings.ML_MODELS_DIR / 'rf_model.pkl',
            'svm': settings.ML_MODELS_DIR / 'svm_model.pkl',
            'lstm': settings.DL_MODELS_DIR / 'lstm_model.h5',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.h5',
        }

        if model_name not in model_map:
            raise ModelNotFoundError(
                f"Unknown model name: {model_name}. "
                f"Valid options: {list(model_map.keys())}"
            )

        return str(model_map[model_name])

    def _get_metadata_path(self, model_name: str) -> str:
        """
        Get full path to model metadata JSON file.

        Args:
            model_name: Model identifier (rf, svm, lstm, cnn_1d)

        Returns:
            Full path to metadata JSON file
        """
        from django.conf import settings

        # Map model names to metadata paths
        metadata_map = {
            'rf': settings.ML_MODELS_DIR / 'rf_model.json',
            'svm': settings.ML_MODELS_DIR / 'svm_model.json',
            'lstm': settings.DL_MODELS_DIR / 'lstm_model.json',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.json',
        }

        if model_name not in metadata_map:
            raise ModelNotFoundError(f"Unknown model name: {model_name}")

        return str(metadata_map[model_name])


class PreprocessingService:
    """
    Service for preprocessing sensor data before inference.

    Automatically detects model type and applies correct preprocessing:
    - ML models: Feature extraction, StandardScaler
    - DL models: Sequence normalization
    """

    def preprocess(self, data: np.ndarray, model_type: str, metadata: Dict) -> np.ndarray:
        """
        Preprocess data based on model type.

        Args:
            data: Raw sensor data
            model_type: 'ml' or 'dl'
            metadata: Model metadata with preprocessing params

        Returns:
            Preprocessed data ready for model inference
        """
        if model_type == 'ml':
            return self._preprocess_ml(data, metadata)
        elif model_type == 'dl':
            return self._preprocess_dl(data, metadata)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def _preprocess_ml(self, data: np.ndarray, metadata: Dict) -> np.ndarray:
        """
        Preprocess data for ML models (RF, SVM).

        Args:
            data: Input features (should be 18 features)
            metadata: Model metadata with StandardScaler parameters

        Returns:
            Preprocessed features ready for ML model
        """
        # Ensure data is numpy array
        data = np.array(data)

        # For ML models, data should already be 18 engineered features
        # Apply StandardScaler if scaler params exist in metadata
        if 'preprocessing' in metadata and 'scaler_params' in metadata['preprocessing']:
            scaler_params = metadata['preprocessing']['scaler_params']

            if 'mean' in scaler_params and 'std' in scaler_params:
                mean = np.array(scaler_params['mean'])
                std = np.array(scaler_params['std'])

                # Apply standardization: (x - mean) / std
                data = (data - mean) / std

        return data

    def _preprocess_dl(self, data: np.ndarray, metadata: Dict) -> np.ndarray:
        """
        Preprocess data for DL models (LSTM, 1D-CNN).

        Args:
            data: Raw sequences (128 timesteps × 6 axes)
            metadata: Model metadata with normalization parameters

        Returns:
            Preprocessed sequences ready for DL model
        """
        # Ensure data is numpy array
        data = np.array(data)

        # For DL models, data should be 128×6 sequences
        # Apply normalization if params exist in metadata
        if 'preprocessing' in metadata and 'normalization' in metadata['preprocessing']:
            norm_params = metadata['preprocessing']['normalization']

            if 'mean' in norm_params and 'std' in norm_params:
                mean = np.array(norm_params['mean'])
                std = np.array(norm_params['std'])

                # Apply normalization per axis
                data = (data - mean) / std

        return data


class SeverityMapper:
    """
    Maps model prediction probabilities to severity levels (0-3).

    Thresholds per spec FR-019:
    - 0 (none): probability < 0.3
    - 1 (mild): probability 0.3-0.5
    - 2 (moderate): probability 0.5-0.7
    - 3 (severe): probability > 0.7
    """

    @staticmethod
    def map_to_severity(probability: float) -> int:
        """
        Map prediction probability to severity level.

        Args:
            probability: Model prediction probability (0.0-1.0)

        Returns:
            Severity level (0-3)
        """
        if probability < 0.3:
            return 0  # None
        elif probability < 0.5:
            return 1  # Mild
        elif probability < 0.7:
            return 2  # Moderate
        else:
            return 3  # Severe


class InferenceService:
    """
    Main inference service that orchestrates the inference workflow.

    Workflow:
    1. Load model (with caching)
    2. Preprocess input data
    3. Execute model prediction
    4. Map probability to severity
    5. Return results with metadata
    """

    def __init__(self):
        self.model_cache = ModelCache()
        self.model_loader = ModelLoader()
        self.preprocessing_service = PreprocessingService()
        self.severity_mapper = SeverityMapper()

    def predict(
        self,
        model_name: str,
        sensor_data: np.ndarray,
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        Perform inference prediction.

        Args:
            model_name: Model to use (rf, svm, lstm, cnn_1d)
            sensor_data: Raw sensor data (will be preprocessed)
            include_metadata: Whether to include P3 metadata

        Returns:
            Dictionary with prediction, severity, and optional metadata

        Raises:
            InferenceError: If prediction fails
            InferenceTimeoutError: If prediction takes >5 seconds
        """
        start_time = time.perf_counter()

        try:
            # 1. Load model (with caching)
            model, metadata = self.model_cache.get_model(model_name)

            # 2. Detect model type and preprocess
            model_path = self.model_loader._get_model_path(model_name)
            model_type = self.model_loader.detect_model_type(model_path)

            preprocessed_data = self.preprocessing_service.preprocess(
                sensor_data, model_type, metadata
            )

            # 3. Execute model prediction
            if model_type == 'ml':
                # scikit-learn models
                # Reshape to 2D if needed (sklearn expects 2D)
                if preprocessed_data.ndim == 1:
                    preprocessed_data = preprocessed_data.reshape(1, -1)

                # Get probability for positive class (tremor detected)
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(preprocessed_data)[0][1]  # Probability of class 1
                else:
                    # If no predict_proba, use predict and assume binary
                    pred = model.predict(preprocessed_data)[0]
                    proba = float(pred)

                prediction = bool(proba >= 0.5)

            elif model_type == 'dl':
                # TensorFlow/Keras models
                # Ensure 3D shape for DL models (batch_size, timesteps, features)
                if preprocessed_data.ndim == 2:
                    preprocessed_data = np.expand_dims(preprocessed_data, axis=0)

                # Get prediction
                pred_output = model.predict(preprocessed_data, verbose=0)

                # Extract probability (assuming binary classification)
                if pred_output.shape[-1] == 1:
                    # Single output neuron (sigmoid)
                    proba = float(pred_output[0][0])
                else:
                    # Multiple output neurons (softmax) - use class 1
                    proba = float(pred_output[0][1])

                prediction = bool(proba >= 0.5)

            # 4. Map probability to severity
            severity = self.severity_mapper.map_to_severity(proba)

            # 5. Calculate inference time
            inference_time_ms = int((time.perf_counter() - start_time) * 1000)

            # Check timeout (5 seconds)
            if inference_time_ms > 5000:
                raise InferenceTimeoutError(
                    f"Inference took {inference_time_ms}ms (>5000ms limit)"
                )

            # 6. Build result
            result = {
                'prediction': prediction,
                'severity': severity,
            }

            # Add P3 metadata if requested
            if include_metadata:
                result['confidence_score'] = float(proba)
                result['inference_time_ms'] = inference_time_ms

                # Model version from metadata
                if 'version' in metadata and 'trained_date' in metadata:
                    model_version = f"{model_name}_v{metadata['version']}_{metadata['trained_date'][:10]}"
                    result['model_version'] = model_version

            return result

        except (ModelNotFoundError, ModelLoadError, InferenceTimeoutError):
            # Re-raise specific errors
            raise

        except Exception as e:
            # Wrap unexpected errors
            from .exceptions import InferenceError
            raise InferenceError(f"Inference failed: {str(e)}")


class InputValidationService:
    """
    Service for validating and assessing input data quality (P3 feature).

    Checks for:
    - Missing values (NaN/Inf)
    - Out-of-range sensor values
    - Overall data quality assessment
    """

    @staticmethod
    def check_missing_values(data: np.ndarray) -> bool:
        """
        Check for NaN or Inf values in data.

        Args:
            data: Sensor data array

        Returns:
            True if missing/invalid values detected, False otherwise
        """
        return bool(np.any(np.isnan(data)) or np.any(np.isinf(data)))

    @staticmethod
    def check_out_of_range_values(data: np.ndarray) -> bool:
        """
        Check if sensor values are outside expected range.

        Typical range: -10 to +10
        Warning range: -50 to +50

        Args:
            data: Sensor data array

        Returns:
            True if values outside warning range, False otherwise
        """
        return bool(np.any(data < -10) or np.any(data > 10))

    @staticmethod
    def assess_overall_quality(missing_values: bool, out_of_range: bool) -> str:
        """
        Determine overall data quality rating.

        Args:
            missing_values: Whether missing/invalid values detected
            out_of_range: Whether out-of-range values detected

        Returns:
            'good', 'degraded', or 'poor'
        """
        if missing_values:
            return 'poor'
        elif out_of_range:
            return 'degraded'
        else:
            return 'good'

    @staticmethod
    def assess_data_quality(data: np.ndarray) -> Dict[str, Any]:
        """
        Assess input data quality.

        Args:
            data: Sensor data array

        Returns:
            Dictionary with data_quality, missing_values, out_of_range_values
        """
        missing = InputValidationService.check_missing_values(data)
        out_of_range = InputValidationService.check_out_of_range_values(data)
        quality = InputValidationService.assess_overall_quality(missing, out_of_range)

        return {
            'data_quality': quality,
            'missing_values': missing,
            'out_of_range_values': out_of_range
        }
