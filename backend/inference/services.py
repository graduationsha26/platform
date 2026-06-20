"""Business logic services for inference (Feature 051 — LightGBM 3-class).

Cleaned up during the LGBM migration: the legacy RF/SVM, v1/v2, gravity-filter, and
StandardScaler code paths were removed. The classical-ML path now serves a single 3-class
LightGBM model (`lgbm`) using the shared 66-feature pipeline (no scaler). Deep-learning
models (lstm/cnn_1d) remain loadable for the DL path.
"""

import joblib
import json
import logging
import os
import time
import warnings
from pathlib import Path
from typing import Dict, Tuple, Any, Optional

import numpy as np

from django.conf import settings

# LightGBM stores positional names (Column_0..) when fit on a NumPy array; predicting on a
# NumPy array is positional and correct, so this cosmetic sklearn warning is silenced.
warnings.filterwarnings(
    "ignore", message="X does not have valid feature names", category=UserWarning
)

from .exceptions import ModelNotFoundError, ModelLoadError, InferenceTimeoutError

logger = logging.getLogger(__name__)

# Shared 66-feature pipeline — same module used by training and the live validator.
try:
    from ml_models.features_lgbm import extract_features_66, get_feature_names_66, process_window
    _FEATURE_EXTRACTOR_AVAILABLE = True
except ImportError:
    _FEATURE_EXTRACTOR_AVAILABLE = False
    logger.warning(
        'ml_models.features_lgbm not importable. LightGBM feature extraction unavailable.'
    )

AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
CLASS_NAMES = {0: 'Non-Tremor', 1: 'Tremor', 2: 'Voluntary'}


class ModelCache:
    """Singleton lazy cache for loaded models: {name: (model, metadata)}."""

    _instance = None
    _models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self, model_name: str) -> Tuple[Any, Dict]:
        if model_name in self._models:
            return self._models[model_name]

        loader = ModelLoader()
        model_path = loader._get_model_path(model_name)
        metadata_path = loader._get_metadata_path(model_name)

        if not os.path.exists(model_path):
            raise ModelNotFoundError(
                f'Model file not found: {model_name}. Train the model first '
                f'(python backend/ml_models/train.py).'
            )
        if not os.path.exists(metadata_path):
            raise ModelNotFoundError(
                f'Model metadata not found: {model_name}. Expected at {metadata_path}'
            )

        model_obj = loader.load_model(model_path)
        metadata = loader.load_metadata(metadata_path)

        self._models[model_name] = (model_obj, metadata)
        return model_obj, metadata

    def clear_cache(self):
        self._models.clear()


class ModelLoader:
    """Loads models (.pkl via joblib, .h5/.keras via tf.keras) and JSON metadata."""

    @staticmethod
    def load_model(model_path: str):
        try:
            ext = Path(model_path).suffix.lower()
            if ext == '.pkl':
                return joblib.load(model_path)
            elif ext in ['.h5', '.keras']:
                import tensorflow as tf
                return tf.keras.models.load_model(model_path)
            raise ValueError(f'Unsupported model file extension: {ext}')
        except Exception as e:
            raise ModelLoadError(f'Failed to load model from {model_path}: {e}')

    @staticmethod
    def load_metadata(metadata_path: str) -> Dict:
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ModelLoadError(f'Failed to load metadata from {metadata_path}: {e}')

    @staticmethod
    def detect_model_type(model_path: str) -> str:
        ext = Path(model_path).suffix.lower()
        if ext == '.pkl':
            return 'ml'
        elif ext in ['.h5', '.keras']:
            return 'dl'
        raise ValueError(f'Cannot detect model type from extension: {ext}')

    def _get_model_path(self, model_name: str) -> str:
        model_map = {
            'lgbm':   settings.ML_MODELS_DIR / 'lgbm_tremor_model.pkl',
            'lstm':   settings.DL_MODELS_DIR / 'lstm_model.h5',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.h5',
        }
        if model_name not in model_map:
            raise ModelNotFoundError(
                f'Unknown model name: {model_name}. Valid options: {list(model_map.keys())}'
            )
        return str(model_map[model_name])

    def _get_metadata_path(self, model_name: str) -> str:
        metadata_map = {
            'lgbm':   settings.ML_MODELS_DIR / 'lgbm_tremor_model.json',
            'lstm':   settings.DL_MODELS_DIR / 'lstm_model.json',
            'cnn_1d': settings.DL_MODELS_DIR / 'cnn_1d_model.json',
        }
        if model_name not in metadata_map:
            raise ModelNotFoundError(f'Unknown model name: {model_name}')
        return str(metadata_map[model_name])


class PreprocessingService:
    """Turns a raw sensor window into model-ready features."""

    def preprocess(self, data: np.ndarray, model_type: str, metadata: Dict) -> np.ndarray:
        if model_type == 'ml':
            return self._preprocess_lgbm(data)
        elif model_type == 'dl':
            return self._preprocess_dl(data, metadata)
        raise ValueError(f'Unknown model type: {model_type}')

    def _preprocess_lgbm(self, data: np.ndarray) -> np.ndarray:
        """Band-pass the raw (window_size, 6) window and extract the 66 features. No scaler.

        Feature 052: the model is trained on band-passed windows, so the REST path must apply
        the SAME causal band-pass (process_window) before feature extraction — otherwise it
        would feed unfiltered features to a filter-trained model. Send ~128-sample windows
        (1.28 s at 100 Hz) to match the training window length.
        """
        if not _FEATURE_EXTRACTOR_AVAILABLE:
            raise RuntimeError('ml_models.features_lgbm unavailable; cannot preprocess.')

        data = np.asarray(data, dtype=np.float64)
        if data.ndim != 2 or data.shape[1] != 6:
            raise ValueError(
                f'LightGBM model expects a window of shape (window_size, 6), got {data.shape}. '
                'Provide a full sensor window, not a single reading.'
            )
        feature_vector = process_window(data)            # band-pass -> (66,)
        return feature_vector.reshape(1, -1)             # (1, 66)

    def _preprocess_dl(self, data: np.ndarray, metadata: Dict) -> np.ndarray:
        data = np.array(data)
        norm = metadata.get('preprocessing', {}).get('normalization')
        if norm and 'mean' in norm and 'std' in norm:
            data = (data - np.array(norm['mean'])) / np.array(norm['std'])
        return data


class SeverityMapper:
    """Maps a tremor probability to a coarse severity bucket (0-3). Retained for DL/log use."""

    @staticmethod
    def map_to_severity(probability: float) -> int:
        if probability < 0.3:
            return 0
        elif probability < 0.5:
            return 1
        elif probability < 0.7:
            return 2
        return 3


class InferenceService:
    """Orchestrates load -> preprocess -> predict for the 3-class LightGBM model (and DL)."""

    def __init__(self):
        self.model_cache = ModelCache()
        self.model_loader = ModelLoader()
        self.preprocessing_service = PreprocessingService()
        self.severity_mapper = SeverityMapper()

    def predict(
        self,
        model_name: str,
        sensor_data: np.ndarray,
        include_metadata: bool = False,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        try:
            model, metadata = self.model_cache.get_model(model_name)
            model_path = self.model_loader._get_model_path(model_name)
            model_type = self.model_loader.detect_model_type(model_path)

            features = self.preprocessing_service.preprocess(sensor_data, model_type, metadata)

            if model_type == 'ml':
                proba = model.predict_proba(features)[0]          # (3,)
            else:  # dl
                if features.ndim == 2:
                    features = np.expand_dims(features, axis=0)
                proba = model.predict(features, verbose=0)[0]
                proba = np.asarray(proba, dtype=np.float64)

            class_index = int(np.argmax(proba))
            predicted_class = CLASS_NAMES.get(class_index, str(class_index))
            confidence = float(proba[class_index])

            inference_time_ms = int((time.perf_counter() - start_time) * 1000)
            if inference_time_ms > 5000:
                raise InferenceTimeoutError(
                    f'Inference took {inference_time_ms}ms (>5000ms limit)'
                )

            # 3-class probability breakdown (defensive against <3 outputs)
            probs = {
                'non_tremor': float(proba[0]) if len(proba) > 0 else 0.0,
                'tremor': float(proba[1]) if len(proba) > 1 else 0.0,
                'voluntary': float(proba[2]) if len(proba) > 2 else 0.0,
            }

            result = {
                'prediction': class_index,                  # 0 / 1 / 2
                'predicted_class': predicted_class,         # label string
                'probabilities': probs,
                'is_tremor': class_index == 1,              # for the boolean audit field
            }
            if include_metadata:
                result['confidence_score'] = confidence
                result['inference_time_ms'] = inference_time_ms
                if 'trained_at' in metadata:
                    result['model_version'] = f'{model_name}@{metadata["trained_at"]}'
            return result

        except (ModelNotFoundError, ModelLoadError, InferenceTimeoutError):
            raise
        except Exception as e:
            from .exceptions import InferenceError
            raise InferenceError(f'Inference failed: {str(e)}')


class InputValidationService:
    """Validates input data quality."""

    @staticmethod
    def check_missing_values(data: np.ndarray) -> bool:
        return bool(np.any(np.isnan(data)) or np.any(np.isinf(data)))

    @staticmethod
    def check_out_of_range_values(data: np.ndarray) -> bool:
        return bool(np.any(data < -50) or np.any(data > 50))

    @staticmethod
    def assess_overall_quality(missing_values: bool, out_of_range: bool) -> str:
        if missing_values:
            return 'poor'
        elif out_of_range:
            return 'degraded'
        return 'good'

    @staticmethod
    def assess_data_quality(data: np.ndarray) -> Dict[str, Any]:
        missing = InputValidationService.check_missing_values(data)
        out_of_range = InputValidationService.check_out_of_range_values(data)
        quality = InputValidationService.assess_overall_quality(missing, out_of_range)
        return {
            'data_quality': quality,
            'missing_values': missing,
            'out_of_range_values': out_of_range,
        }
