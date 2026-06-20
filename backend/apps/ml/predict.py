"""
ML Model Inference Script for Raw Feature Pipeline

Provides prediction functions for Random Forest and SVM models using 6-feature input.
Includes startup validation and normalization using params.json.

Usage:
    from apps.ml.predict import MLPredictor

    # Initialize predictor (validates models on startup)
    predictor = MLPredictor(
        model_dir='ml_models',
        params_path='ml_data/params.json'
    )

    # Predict from raw sensor data
    sensor_data = [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]  # 6 values
    result = predictor.predict(sensor_data, model_type='rf')
"""

import joblib
import numpy as np
import os
import sys
import time
from typing import Dict, List, Union

# Import utilities
try:
    from validate_models import validate_sklearn_model
    from normalize import load_params, normalize_features
    from feature_utils import FEATURE_COLUMNS
except ImportError:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    from apps.ml.validate_models import validate_sklearn_model
    from apps.ml.normalize import load_params, normalize_features
    from apps.ml.feature_utils import FEATURE_COLUMNS


class MLPredictor:
    """
    ML model predictor with automatic validation and normalization.

    Performs startup validation to ensure models expect 6 features,
    loads normalization parameters, and provides fast inference.
    """

    def __init__(self, model_dir='ml_models', params_path='ml_data/params.json'):
        """
        Initialize predictor with model validation.

        Args:
            model_dir (str): Directory containing .pkl model files
            params_path (str): Path to params.json normalization parameters

        Raises:
            ValueError: If model validation fails or params.json is invalid
            FileNotFoundError: If models or params not found
        """
        self.model_dir = model_dir
        self.params_path = params_path
        self.models = {}
        self.params = None

        print(f"Initializing ML Predictor...")
        print(f"  Model directory: {model_dir}")
        print(f"  Params file: {params_path}")

        # Load and validate normalization parameters
        self._load_params()

        # Load and validate models
        self._load_models()

        print(f"[OK] ML Predictor ready ({len(self.models)} models loaded)")

    def _load_params(self):
        """Load and validate normalization parameters."""
        print("\nLoading normalization parameters...")
        self.params = load_params(self.params_path)
        print(f"[OK] Loaded params: {len(self.params['features'])} features")

    def _load_models(self):
        """Load and validate all ML models."""
        print("\nValidating and loading models...")

        # Expected models
        model_files = {
            'rf': 'rf_model.pkl',
            'svm': 'svm_model.pkl'
        }

        for model_key, filename in model_files.items():
            model_path = os.path.join(self.model_dir, filename)

            if not os.path.exists(model_path):
                print(f"[WARN] Warning: {filename} not found, skipping")
                continue

            try:
                # Validate and load model (checks n_features_in_=6)
                model = validate_sklearn_model(model_path, expected_features=6)
                self.models[model_key] = model
                print(f"[OK] {model_key.upper()}: n_features_in_={model.n_features_in_}")
            except Exception as e:
                print(f"[ERROR] Failed to load {filename}: {e}")
                raise

        if not self.models:
            raise ValueError(
                f"No valid models found in {self.model_dir}. "
                f"Run training first: python apps/ml/train.py"
            )

    def predict(self, sensor_data: Union[np.ndarray, List[float]], model_type='rf') -> Dict:
        """
        Predict tremor severity from raw sensor data.

        Args:
            sensor_data: Raw sensor values [aX, aY, aZ, gX, gY, gZ] (6 values)
            model_type: Model to use ('rf' for Random Forest, 'svm' for SVM)

        Returns:
            dict: Prediction result with keys:
                - prediction: Class label
                - confidence: Confidence score (0-1)
                - model_type: Model used
                - latency_ms: Inference time in milliseconds

        Raises:
            ValueError: If input shape is incorrect or model not available
        """
        start_time = time.perf_counter()

        # Validate model type
        if model_type not in self.models:
            available = ', '.join(self.models.keys())
            raise ValueError(
                f"Model '{model_type}' not available. "
                f"Available models: {available}"
            )

        # Convert to numpy array
        if not isinstance(sensor_data, np.ndarray):
            sensor_data = np.array(sensor_data, dtype=np.float64)

        # Validate shape
        if sensor_data.shape != (6,):
            raise ValueError(
                f"Expected 6 sensor values, got {sensor_data.shape}. "
                f"Input should be [aX, aY, aZ, gX, gY, gZ]"
            )

        # NOTE: Current models were trained on RAW data (not normalized)
        # TODO: Retrain models with normalized data for better generalization
        # For now, pass raw data directly to match training pipeline

        # Reshape for sklearn (expects 2D: n_samples × n_features)
        X = sensor_data.reshape(1, -1)

        # Predict
        model = self.models[model_type]
        prediction = model.predict(X)[0]

        # Get confidence (probability)
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X)[0]
            confidence = float(probabilities[int(prediction)])
        else:
            # SVM without probability calibration
            confidence = 1.0  # Placeholder

        # Calculate latency
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        result = {
            'prediction': int(prediction),
            'confidence': confidence,
            'model_type': model_type.upper(),
            'latency_ms': round(latency_ms, 2)
        }

        return result

    def predict_batch(self, sensor_batch: np.ndarray, model_type='rf') -> List[Dict]:
        """
        Predict on multiple sensor readings at once.

        Args:
            sensor_batch: Array of shape (n_samples, 6)
            model_type: Model to use

        Returns:
            list: List of prediction results
        """
        if sensor_batch.ndim != 2 or sensor_batch.shape[1] != 6:
            raise ValueError(
                f"Expected shape (n_samples, 6), got {sensor_batch.shape}"
            )

        results = []
        for sensor_data in sensor_batch:
            result = self.predict(sensor_data, model_type)
            results.append(result)

        return results


# Singleton predictor instance (lazy loaded)
_predictor_instance = None


def get_predictor(model_dir='ml_models', params_path='ml_data/params.json'):
    """
    Get or create singleton predictor instance.

    This ensures models are loaded only once for efficiency.
    """
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MLPredictor(model_dir, params_path)
    return _predictor_instance


def predict(sensor_data, model_type='rf', model_dir='ml_models', params_path='ml_data/params.json'):
    """
    Convenience function for single predictions.

    Args:
        sensor_data: Raw sensor values [aX, aY, aZ, gX, gY, gZ]
        model_type: 'rf' or 'svm'
        model_dir: Path to model directory
        params_path: Path to params.json

    Returns:
        dict: Prediction result

    Example:
        >>> result = predict([0.5, -0.3, 10.2, 0.05, -0.02, 0.01], model_type='rf')
        >>> print(f"Prediction: {result['prediction']}, Confidence: {result['confidence']:.2f}")
    """
    predictor = get_predictor(model_dir, params_path)
    return predictor.predict(sensor_data, model_type)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test ML inference with 6-feature input')
    parser.add_argument('--model-dir', default='ml_models', help='Model directory')
    parser.add_argument('--params', default='ml_data/params.json', help='Params file')
    parser.add_argument('--model-type', default='rf', choices=['rf', 'svm'], help='Model type')
    parser.add_argument('--test-data', help='Test sensor data (6 values comma-separated)')

    args = parser.parse_args()

    try:
        # Initialize predictor
        predictor = MLPredictor(args.model_dir, args.params)

        # Test with sample data
        if args.test_data:
            sensor_data = [float(x) for x in args.test_data.split(',')]
        else:
            # Default test sample
            sensor_data = [0.5, -0.3, 10.2, 0.05, -0.02, 0.01]

        print(f"\nTest sensor data: {sensor_data}")
        print(f"Model: {args.model_type.upper()}")

        # Predict
        result = predictor.predict(sensor_data, args.model_type)

        print("\n--- Prediction Result ---")
        print(f"Prediction: {result['prediction']}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Latency: {result['latency_ms']:.2f} ms")

        # Check latency requirement
        if result['latency_ms'] < 70:
            print(f"[OK] Latency within requirement (<70ms)")
        else:
            print(f"[WARN] Latency exceeds requirement: {result['latency_ms']:.2f} ms > 70 ms")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
