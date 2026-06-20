"""
Unit tests for ML prediction service.

Tests ML model loading, feature extraction, and prediction generation.
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
import numpy as np

from realtime.ml_service import MLPredictionService


class MLFeatureExtractionTest(TestCase):
    """Test ML feature extraction from sensor data."""

    def setUp(self):
        """Set up ML service instance."""
        self.ml_service = MLPredictionService()

    def test_extract_features_from_valid_sensor_data(self):
        """Test feature extraction from valid sensor data."""
        sensor_data = {
            'tremor_intensity': [0.25, 0.30, 0.28, 0.32],
            'frequency': 4.5,
            'timestamps': ['2024-02-15T10:30:00Z', '2024-02-15T10:30:01Z', '2024-02-15T10:30:02Z', '2024-02-15T10:30:03Z']
        }

        features = self.ml_service._extract_features(sensor_data)

        assert features is not None
        assert features.shape == (1, 4)
        # Features should be: [avg, max, std, frequency]
        assert features[0][3] == 4.5  # Frequency

    def test_extract_features_returns_none_for_invalid_data(self):
        """Test feature extraction returns None for invalid data."""
        invalid_sensor_data = {
            'tremor_intensity': [],  # Empty array
            'frequency': 0.0,
            'timestamps': []
        }

        features = self.ml_service._extract_features(invalid_sensor_data)
        assert features is None

    @patch('joblib.load')
    def test_prediction_with_sklearn_model(self, mock_joblib_load):
        """Test prediction generation with sklearn model."""
        # Mock sklearn model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1])  # moderate
        mock_model.predict_proba.return_value = np.array([[0.1, 0.8, 0.1]])  # 80% confidence
        mock_joblib_load.return_value = mock_model

        # Create new service instance to trigger model loading
        ml_service = MLPredictionService()
        ml_service.sklearn_model = mock_model

        sensor_data = {
            'tremor_intensity': [0.45, 0.50, 0.48, 0.52],
            'frequency': 5.2,
            'timestamps': ['2024-02-15T10:30:00Z'] * 4
        }

        prediction = ml_service.predict_severity(sensor_data)

        assert prediction is not None
        assert prediction['severity'] == 'moderate'
        assert prediction['confidence'] == pytest.approx(0.8, rel=0.01)

    def test_prediction_returns_none_when_no_model_available(self):
        """Test prediction returns None when ML models are not loaded."""
        ml_service = MLPredictionService()
        ml_service.sklearn_model = None
        ml_service.keras_model = None

        sensor_data = {
            'tremor_intensity': [0.25, 0.30, 0.28, 0.32],
            'frequency': 4.5,
            'timestamps': ['2024-02-15T10:30:00Z'] * 4
        }

        prediction = ml_service.predict_severity(sensor_data)
        assert prediction is None


# TODO: Add tests for:
# - Singleton pattern enforcement
# - Thread-safety of model loading
# - Keras model prediction
# - Error handling for model loading failures
# - Feature normalization (if implemented)
