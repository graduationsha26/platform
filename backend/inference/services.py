"""Business logic services for inference."""

import joblib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Tuple, Any, Optional

import numpy as np

from django.conf import settings

from .exceptions import ModelNotFoundError, ModelLoadError, InferenceTimeoutError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gravity filter — still used by v1 models (backward compatibility)
# ---------------------------------------------------------------------------
try:
    from ml_data.utils.gravity_filter import apply_gravity_filter  # noqa: F401
    _GRAVITY_FILTER_AVAILABLE = True
except ImportError:
    _GRAVITY_FILTER_AVAILABLE = False
    logger.warning(
        'ml_data.utils.gravity_filter not importable. '
        'Gravity filtering will be skipped for v1 models.'
    )

# ---------------------------------------------------------------------------
# Shared feature extraction — v2 pipeline
# ---------------------------------------------------------------------------
try:
    from ml_data.utils.feature_extractors import extract_window_features
    _FEATURE_EXTRACTOR_AVAILABLE = True
except ImportError:
    _FEATURE_EXTRACTOR_AVAILABLE = False
    logger.warning(
        'ml_data.utils.feature_extractors not importable. '
        'v2 feature extraction will be unavailable.'
    )

AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']


class ModelCache:
    """
    Singleton cache for loaded ML/DL models.

    Implements lazy loading: models are loaded on first access and cached in memory
    for subsequent requests. This eliminates 500ms-2s load time per request.

    Cache stores: (model_object, metadata_dict, scaler_or_None)
    Thread-safe for concurrent predictions (models are read-only after loading).
    """

    _instance = None
    _models = {}  # {model_name: (model_object, metadata_dict, scaler_or_None)}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self, model_name: str) -> Tuple[Any, Dict, Optional[Any]]:
        """
        Get model from cache or load if not cached.

        Args:
            model_name: Model identifier (rf, svm, lstm, cnn_1d)

        Returns:
            Tuple of (model_object, metadata_dict, scaler_or_None)

        Raises:
            ModelNotFoundError: If model file doesn't exist
            ModelLoadError: If model loading fails
        """
        if model_name in self._models:
            return self._models[model_name]

        model_loader = ModelLoader()
        model_path = model_loader._get_model_path(model_name)
        metadata_path = model_loader._get_metadata_path(model_name)

        if not os.path.exists(model_path):
            raise ModelNotFoundError(
                f'Model file not found: {model_name}. '
                f'Please train the model first.'
            )

        if not os.path.exists(metadata_path):
            raise ModelNotFoundError(
                f'Model metadata not found: {model_name}. '
                f'Expected metadata file at {metadata_path}'
            )

        model_obj = model_loader.load_model(model_path)
        metadata = model_loader.load_metadata(metadata_path)

        # Pre-parse gravity filter SOS coefficients for v1 models
        if 'filter_params' in metadata and 'sos_coefficients' in metadata['filter_params']:
            metadata['filter_params']['_sos_array'] = np.array(
                metadata['filter_params']['sos_coefficients'],
                dtype=np.float64,
            )

        # Load StandardScaler for v2 models (scaler_file key present in metadata)
        scaler = None
        if 'scaler_file' in metadata:
            scaler_filename = metadata['scaler_file']
            scaler_path = str(Path(model_path).parent / scaler_filename)
            if os.path.exists(scaler_path):
                try:
                    scaler = joblib.load(scaler_path)
                    logger.info(f'Scaler loaded: {scaler_path}')
                except Exception as e:
                    raise ModelLoadError(
                        f'Failed to load scaler from {scaler_path}: {e}'
                    )
            else:
                raise ModelNotFoundError(
                    f'Scaler file not found: {scaler_path}. '
                    f'Run train_random_forest.py to regenerate v2 artifacts.'
                )

        self._models[model_name] = (model_obj, metadata, scaler)
        return model_obj, metadata, scaler

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
        try:
            file_ext = Path(model_path).suffix.lower()

            if file_ext == '.pkl':
                return joblib.load(model_path)

            elif file_ext in ['.h5', '.keras']:
                import tensorflow as tf
                return tf.keras.models.load_model(model_path)

            else:
                raise ValueError(f'Unsupported model file extension: {file_ext}')

        except Exception as e:
            raise ModelLoadError(f'Failed to load model from {model_path}: {str(e)}')

    @staticmethod
    def load_metadata(metadata_path: str) -> Dict:
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ModelLoadError(f'Failed to load metadata from {metadata_path}: {str(e)}')

    @staticmethod
    def detect_model_type(model_path: str) -> str:
        file_ext = Path(model_path).suffix.lower()
        if file_ext == '.pkl':
            return 'ml'
        elif file_ext in ['.h5', '.keras']:
            return 'dl'
        else:
            raise ValueError(f'Cannot detect model type from extension: {file_ext}')

    def _get_model_path(self, model_name: str) -> str:
        model_map = {
            'rf':     settings.ML_MODELS_DIR / 'rf_model_v3.pkl',
            'svm':    settings.ML_MODELS_DIR / 'svm_model.pkl',
            'lstm':   settings.DL_MODELS_DIR / 'lstm_model.h5',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.h5',
        }

        if model_name not in model_map:
            raise ModelNotFoundError(
                f'Unknown model name: {model_name}. '
                f'Valid options: {list(model_map.keys())}'
            )

        return str(model_map[model_name])

    def _get_metadata_path(self, model_name: str) -> str:
        metadata_map = {
            'rf':     settings.ML_MODELS_DIR / 'rf_model_v3.json',
            'svm':    settings.ML_MODELS_DIR / 'svm_model.json',
            'lstm':   settings.DL_MODELS_DIR / 'lstm_model.json',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.json',
        }

        if model_name not in metadata_map:
            raise ModelNotFoundError(f'Unknown model name: {model_name}')

        return str(metadata_map[model_name])


class PreprocessingService:
    """
    Service for preprocessing sensor data before inference.

    v2 models (identified by 'pipeline_params' in metadata):
      - Expect input as a 2-D array (window_size, 6) in physical units
      - Extract 42 features via shared extract_window_features()
      - Apply saved StandardScaler via scaler.transform()
      - No gravity filter (FFT handles frequency separation)

    v1 models (legacy, no 'pipeline_params'):
      - Expect a 1-D array of 6 raw sensor values
      - Apply gravity filter (if filter_params in metadata)
      - Apply scaler params embedded in metadata JSON
    """

    def preprocess(
        self,
        data: np.ndarray,
        model_type: str,
        metadata: Dict,
        scaler=None,
    ) -> np.ndarray:
        """
        Preprocess data based on model version and type.

        Args:
            data: Sensor data — (window_size, 6) array for v2 ML models,
                  or 1-D (6,) array for v1 ML models, or (128, 6) for DL models.
            model_type: 'ml' or 'dl'
            metadata: Model metadata dict
            scaler: Loaded StandardScaler for v2 models (or None for v1)

        Returns:
            Preprocessed feature vector ready for model inference
        """
        is_v2 = 'pipeline_params' in metadata

        if model_type == 'ml':
            if is_v2:
                return self._preprocess_ml_v2(data, metadata, scaler)
            else:
                # v1 legacy path
                data = self._apply_gravity_filter(data, model_type, metadata)
                return self._preprocess_ml_v1(data, metadata)
        elif model_type == 'dl':
            return self._preprocess_dl(data, metadata)
        else:
            raise ValueError(f'Unknown model type: {model_type}')

    # -----------------------------------------------------------------------
    # v2 preprocessing (new pipeline)
    # -----------------------------------------------------------------------

    def _preprocess_ml_v2(
        self,
        data: np.ndarray,
        metadata: Dict,
        scaler,
    ) -> np.ndarray:
        """
        v2 ML preprocessing:
          1. Validate input shape: must be (window_size, 6)
          2. Extract 42 features via extract_window_features()
          3. Scale via StandardScaler.transform()

        Args:
            data: 2-D array of shape (window_size, 6) in physical units
            metadata: Model metadata with pipeline_params
            scaler: Fitted StandardScaler loaded from scaler .pkl

        Returns:
            Scaled 42-feature vector, shape (1, 42)
        """
        if not _FEATURE_EXTRACTOR_AVAILABLE:
            raise RuntimeError(
                'ml_data.utils.feature_extractors is not importable. '
                'Cannot perform v2 preprocessing.'
            )

        data = np.asarray(data, dtype=np.float64)

        if data.ndim != 2 or data.shape[1] != 6:
            raise ValueError(
                f'v2 ML model expects input shape (window_size, 6), got {data.shape}. '
                'Provide a full sensor window, not a single reading.'
            )

        pipeline_params = metadata['pipeline_params']
        sampling_rate_hz = float(pipeline_params.get('training_sampling_rate_hz', 30.0))
        low_hz  = float(pipeline_params.get('fft_tremor_band_low_hz', 3.0))
        high_hz = float(pipeline_params.get('fft_tremor_band_high_hz', 12.0))

        # Extract 42 features — identical function used during training
        feature_vector = extract_window_features(
            data, AXIS_NAMES, sampling_rate_hz, low_hz, high_hz
        )  # shape: (42,)

        if scaler is None:
            raise RuntimeError(
                'v2 model requires a StandardScaler but none was provided. '
                'Ensure the scaler .pkl was loaded alongside the model.'
            )

        # Scale and return 2-D for sklearn predict
        return scaler.transform(feature_vector.reshape(1, -1))  # shape: (1, 42)

    # -----------------------------------------------------------------------
    # v1 legacy preprocessing (kept for backward compatibility)
    # -----------------------------------------------------------------------

    def _apply_gravity_filter(
        self, data: np.ndarray, model_type: str, metadata: Dict
    ) -> np.ndarray:
        """Apply gravity high-pass filter to accelerometer channels (v1 models only)."""
        if not _GRAVITY_FILTER_AVAILABLE:
            return data

        filter_params = metadata.get('filter_params')
        if not filter_params:
            return data

        if '_sos_array' in filter_params:
            sos = filter_params['_sos_array']
        elif 'sos_coefficients' in filter_params:
            sos = np.array(filter_params['sos_coefficients'], dtype=np.float64)
        else:
            logger.warning('filter_params present but sos_coefficients missing — skipping')
            return data

        data = np.asarray(data, dtype=np.float64)

        if model_type == 'ml':
            was_1d = data.ndim == 1
            if was_1d:
                data = data[np.newaxis, :]
            data = apply_gravity_filter(data, sos)
            if was_1d:
                data = data[0]
        elif model_type == 'dl':
            if data.ndim == 2:
                data = apply_gravity_filter(data, sos)

        return data

    def _preprocess_ml_v1(self, data: np.ndarray, metadata: Dict) -> np.ndarray:
        """v1 ML preprocessing: apply embedded scaler params from metadata JSON."""
        data = np.array(data)

        if 'preprocessing' in metadata and 'scaler_params' in metadata['preprocessing']:
            scaler_params = metadata['preprocessing']['scaler_params']
            if 'mean' in scaler_params and 'std' in scaler_params:
                mean = np.array(scaler_params['mean'])
                std = np.array(scaler_params['std'])
                data = (data - mean) / std

        return data

    def _preprocess_dl(self, data: np.ndarray, metadata: Dict) -> np.ndarray:
        """DL model preprocessing: apply normalization params from metadata."""
        data = np.array(data)

        if 'preprocessing' in metadata and 'normalization' in metadata['preprocessing']:
            norm_params = metadata['preprocessing']['normalization']
            if 'mean' in norm_params and 'std' in norm_params:
                mean = np.array(norm_params['mean'])
                std = np.array(norm_params['std'])
                data = (data - mean) / std

        return data


class SeverityMapper:
    """
    Maps model prediction probabilities to severity levels (0-3).

    Thresholds:
    - 0 (none): probability < 0.3
    - 1 (mild): probability 0.3-0.5
    - 2 (moderate): probability 0.5-0.7
    - 3 (severe): probability > 0.7
    """

    @staticmethod
    def map_to_severity(probability: float) -> int:
        if probability < 0.3:
            return 0
        elif probability < 0.5:
            return 1
        elif probability < 0.7:
            return 2
        else:
            return 3


class InferenceService:
    """
    Main inference service that orchestrates the inference workflow.

    Workflow:
    1. Load model (with caching) — returns (model, metadata, scaler)
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
            sensor_data: For v2 RF: 2-D array (window_size, 6) in physical units.
                         For v1 models: 1-D (6,) raw sensor values.
                         For DL: (128, 6) sequence.
            include_metadata: Whether to include confidence/timing in response

        Returns:
            Dictionary with prediction, severity, and optional metadata

        Raises:
            ModelNotFoundError, ModelLoadError, InferenceTimeoutError
        """
        start_time = time.perf_counter()

        try:
            # 1. Load model (with caching) — now returns 3-tuple
            model, metadata, scaler = self.model_cache.get_model(model_name)

            # 2. Detect model type and preprocess
            model_path = self.model_loader._get_model_path(model_name)
            model_type = self.model_loader.detect_model_type(model_path)

            preprocessed_data = self.preprocessing_service.preprocess(
                sensor_data, model_type, metadata, scaler=scaler
            )

            # 3. Execute model prediction
            if model_type == 'ml':
                if preprocessed_data.ndim == 1:
                    preprocessed_data = preprocessed_data.reshape(1, -1)

                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(preprocessed_data)[0][1]
                else:
                    pred = model.predict(preprocessed_data)[0]
                    proba = float(pred)

                prediction = bool(proba >= 0.5)

            elif model_type == 'dl':
                if preprocessed_data.ndim == 2:
                    preprocessed_data = np.expand_dims(preprocessed_data, axis=0)

                pred_output = model.predict(preprocessed_data, verbose=0)

                if pred_output.shape[-1] == 1:
                    proba = float(pred_output[0][0])
                else:
                    proba = float(pred_output[0][1])

                prediction = bool(proba >= 0.5)

            # 4. Map probability to severity
            severity = self.severity_mapper.map_to_severity(proba)

            # 5. Calculate inference time
            inference_time_ms = int((time.perf_counter() - start_time) * 1000)

            if inference_time_ms > 5000:
                raise InferenceTimeoutError(
                    f'Inference took {inference_time_ms}ms (>5000ms limit)'
                )

            # 6. Build result
            result = {
                'prediction': prediction,
                'severity': severity,
            }

            if include_metadata:
                result['confidence_score'] = float(proba)
                result['inference_time_ms'] = inference_time_ms

                if 'version' in metadata:
                    result['model_version'] = f'{model_name}_v{metadata["version"]}'

            return result

        except (ModelNotFoundError, ModelLoadError, InferenceTimeoutError):
            raise

        except Exception as e:
            from .exceptions import InferenceError
            raise InferenceError(f'Inference failed: {str(e)}')


class InputValidationService:
    """
    Service for validating and assessing input data quality.

    Checks for:
    - Missing values (NaN/Inf)
    - Out-of-range sensor values
    - Overall data quality assessment
    """

    @staticmethod
    def check_missing_values(data: np.ndarray) -> bool:
        return bool(np.any(np.isnan(data)) or np.any(np.isinf(data)))

    @staticmethod
    def check_out_of_range_values(data: np.ndarray) -> bool:
        return bool(np.any(data < -10) or np.any(data > 10))

    @staticmethod
    def assess_overall_quality(missing_values: bool, out_of_range: bool) -> str:
        if missing_values:
            return 'poor'
        elif out_of_range:
            return 'degraded'
        else:
            return 'good'

    @staticmethod
    def assess_data_quality(data: np.ndarray) -> Dict[str, Any]:
        missing = InputValidationService.check_missing_values(data)
        out_of_range = InputValidationService.check_out_of_range_values(data)
        quality = InputValidationService.assess_overall_quality(missing, out_of_range)

        return {
            'data_quality': quality,
            'missing_values': missing,
            'out_of_range_values': out_of_range
        }
