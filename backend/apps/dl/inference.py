"""
DL Model Inference Script for Raw Feature Pipeline

Provides prediction functions for LSTM and CNN models using 6-feature input.
Includes startup validation and normalization using params.json.

Usage:
    from apps.dl.inference import DLPredictor

    # Initialize predictor (validates models on startup)
    predictor = DLPredictor(
        model_dir='dl_models',
        params_path='ml_data/params.json'
    )

    # Predict from raw sensor sequences
    sensor_sequence = np.random.randn(10, 6)  # 10 timesteps, 6 features
    result = predictor.predict(sensor_sequence, model_type='lstm')
"""

import numpy as np
import os
import sys
import time
from typing import Dict, List, Union

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError:
    print("ERROR: TensorFlow is required for DL inference.")
    print("Install with: pip install tensorflow")
    sys.exit(1)

# Import utilities from ml directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from apps.ml.validate_models import validate_keras_model
from apps.ml.normalize import load_params, normalize_features
from apps.ml.feature_utils import FEATURE_COLUMNS


class DLPredictor:
    """
    Deep learning model predictor with automatic validation and normalization.

    Supports LSTM (sequence input) and CNN (1D convolution) models.
    """

    def __init__(self, model_dir='dl_models', params_path='ml_data/params.json'):
        """
        Initialize DL predictor with model validation.

        Args:
            model_dir (str): Directory containing .h5 model files
            params_path (str): Path to params.json normalization parameters

        Raises:
            ValueError: If model validation fails
            FileNotFoundError: If models or params not found
        """
        self.model_dir = model_dir
        self.params_path = params_path
        self.models = {}
        self.params = None

        print(f"Initializing DL Predictor...")
        print(f"  Model directory: {model_dir}")
        print(f"  Params file: {params_path}")

        # Load normalization parameters
        self._load_params()

        # Load and validate models
        self._load_models()

        print(f"✓ DL Predictor ready ({len(self.models)} models loaded)")

    def _load_params(self):
        """Load normalization parameters."""
        print("\nLoading normalization parameters...")
        self.params = load_params(self.params_path)
        print(f"✓ Loaded params: {len(self.params['features'])} features")

    def _load_models(self):
        """Load and validate all DL models."""
        print("\nValidating and loading models...")

        # Expected models
        model_files = {
            'lstm': 'lstm.h5',
            'cnn': 'cnn.h5'
        }

        for model_key, filename in model_files.items():
            model_path = os.path.join(self.model_dir, filename)

            if not os.path.exists(model_path):
                print(f"⚠ Warning: {filename} not found, skipping")
                continue

            try:
                # Validate and load model (checks input_shape[-1]=6)
                model = validate_keras_model(model_path, expected_features=6)
                self.models[model_key] = model
                print(f"✓ {model_key.upper()}: input_shape={model.input_shape}")
            except Exception as e:
                print(f"✗ Failed to load {filename}: {e}")
                raise

        if not self.models:
            print(f"⚠ Warning: No DL models found in {self.model_dir}")
            print(f"  Run training: python apps/dl/train_lstm.py or python apps/dl/train_cnn.py")

    def predict_lstm(self, sensor_sequence: np.ndarray) -> Dict:
        """
        Predict using LSTM model.

        Args:
            sensor_sequence: Array of shape (timesteps, 6) or (1, timesteps, 6)

        Returns:
            dict: Prediction result
        """
        if 'lstm' not in self.models:
            raise ValueError("LSTM model not loaded")

        start_time = time.perf_counter()

        # Handle shape
        if sensor_sequence.ndim == 2:
            # (timesteps, 6) → (1, timesteps, 6)
            if sensor_sequence.shape[1] != 6:
                raise ValueError(
                    f"Expected shape (timesteps, 6), got {sensor_sequence.shape}"
                )
            X = sensor_sequence.reshape(1, sensor_sequence.shape[0], 6)
        elif sensor_sequence.ndim == 3:
            # Already (batch, timesteps, 6)
            if sensor_sequence.shape[2] != 6:
                raise ValueError(
                    f"Expected 6 features in last dimension, got {sensor_sequence.shape}"
                )
            X = sensor_sequence
        else:
            raise ValueError(f"Invalid input shape: {sensor_sequence.shape}")

        # Normalize each timestep
        normalized = np.zeros_like(X)
        for i in range(X.shape[0]):  # For each sample in batch
            for t in range(X.shape[1]):  # For each timestep
                normalized[i, t] = normalize_features(X[i, t], self.params)

        # Predict
        model = self.models['lstm']
        probabilities = model.predict(normalized, verbose=0)
        prediction = np.argmax(probabilities, axis=1)[0]
        confidence = float(probabilities[0, int(prediction)])

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            'prediction': int(prediction),
            'confidence': confidence,
            'model_type': 'LSTM',
            'latency_ms': round(latency_ms, 2),
            'input_shape': list(X.shape)
        }

    def predict_cnn(self, sensor_data: np.ndarray) -> Dict:
        """
        Predict using CNN model.

        Args:
            sensor_data: Array of shape (6,) or (1, 6) or (1, 6, 1)

        Returns:
            dict: Prediction result
        """
        if 'cnn' not in self.models:
            raise ValueError("CNN model not loaded")

        start_time = time.perf_counter()

        # Convert to numpy
        if not isinstance(sensor_data, np.ndarray):
            sensor_data = np.array(sensor_data, dtype=np.float64)

        # Handle different input shapes
        if sensor_data.shape == (6,):
            # (6,) → (1, 6, 1)
            X = sensor_data.reshape(1, 6, 1)
        elif sensor_data.shape == (1, 6):
            # (1, 6) → (1, 6, 1)
            X = sensor_data.reshape(1, 6, 1)
        elif sensor_data.shape == (1, 6, 1):
            # Already correct shape
            X = sensor_data
        else:
            raise ValueError(
                f"Expected shape (6,) or (1, 6) or (1, 6, 1), got {sensor_data.shape}"
            )

        # Normalize (flatten, normalize, reshape)
        flat = X.reshape(1, 6)
        normalized_flat = normalize_features(flat[0], self.params)
        normalized = normalized_flat.reshape(1, 6, 1)

        # Predict
        model = self.models['cnn']
        probabilities = model.predict(normalized, verbose=0)
        prediction = np.argmax(probabilities, axis=1)[0]
        confidence = float(probabilities[0, int(prediction)])

        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            'prediction': int(prediction),
            'confidence': confidence,
            'model_type': 'CNN',
            'latency_ms': round(latency_ms, 2),
            'input_shape': list(X.shape)
        }

    def predict(self, sensor_data: np.ndarray, model_type='lstm') -> Dict:
        """
        Predict using specified model type.

        Args:
            sensor_data: Sensor data (shape depends on model)
                - LSTM: (timesteps, 6)
                - CNN: (6,)
            model_type: 'lstm' or 'cnn'

        Returns:
            dict: Prediction result
        """
        if model_type == 'lstm':
            return self.predict_lstm(sensor_data)
        elif model_type == 'cnn':
            return self.predict_cnn(sensor_data)
        else:
            available = ', '.join(self.models.keys())
            raise ValueError(
                f"Unknown model type '{model_type}'. Available: {available}"
            )


# Singleton predictor instance
_dl_predictor_instance = None


def get_predictor(model_dir='dl_models', params_path='ml_data/params.json'):
    """Get or create singleton DL predictor instance."""
    global _dl_predictor_instance
    if _dl_predictor_instance is None:
        _dl_predictor_instance = DLPredictor(model_dir, params_path)
    return _dl_predictor_instance


def predict_dl(sensor_data, model_type='lstm', model_dir='dl_models', params_path='ml_data/params.json'):
    """
    Convenience function for DL predictions.

    Args:
        sensor_data: Input data (shape depends on model)
        model_type: 'lstm' or 'cnn'
        model_dir: Model directory
        params_path: Params file

    Returns:
        dict: Prediction result
    """
    predictor = get_predictor(model_dir, params_path)
    return predictor.predict(sensor_data, model_type)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test DL inference with 6-feature input')
    parser.add_argument('--model-dir', default='dl_models')
    parser.add_argument('--params', default='ml_data/params.json')
    parser.add_argument('--model-type', default='lstm', choices=['lstm', 'cnn'])
    parser.add_argument('--timesteps', type=int, default=10, help='For LSTM: sequence length')

    args = parser.parse_args()

    try:
        # Initialize predictor
        predictor = DLPredictor(args.model_dir, args.params)

        if args.model_type == 'lstm':
            # Test LSTM with random sequence
            sensor_sequence = np.random.randn(args.timesteps, 6)
            print(f"\nTest LSTM with sequence: {sensor_sequence.shape}")
            result = predictor.predict_lstm(sensor_sequence)

        else:  # cnn
            # Test CNN with single reading
            sensor_data = np.random.randn(6)
            print(f"\nTest CNN with data: {sensor_data.shape}")
            result = predictor.predict_cnn(sensor_data)

        print("\n--- Prediction Result ---")
        print(f"Model: {result['model_type']}")
        print(f"Prediction: {result['prediction']}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Latency: {result['latency_ms']:.2f} ms")
        print(f"Input shape: {result['input_shape']}")

        # Check latency
        if result['latency_ms'] < 70:
            print(f"✓ Latency within requirement (<70ms)")
        else:
            print(f"⚠ Latency exceeds requirement: {result['latency_ms']:.2f} ms > 70 ms")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
