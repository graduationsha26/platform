"""Input validation functions for inference."""

import numpy as np
from typing import Tuple

from .exceptions import InvalidInputError


def validate_ml_input_shape(data: np.ndarray, expected_features: int = 6):
    """
    Validate input shape for ML models (RF, SVM).

    Args:
        data: Input data array
        expected_features: Expected number of features (default: 6)

    Raises:
        InvalidInputError: If shape doesn't match expected format
    """
    data = np.array(data)

    # ML models expect 1D array with 6 features [aX, aY, aZ, gX, gY, gZ] (or 2D with shape (1, 6))
    if data.ndim == 1:
        if len(data) != expected_features:
            raise InvalidInputError(
                f"Invalid input shape for ML model: expected {expected_features} features, "
                f"got {len(data)}"
            )
    elif data.ndim == 2:
        if data.shape[1] != expected_features:
            raise InvalidInputError(
                f"Invalid input shape for ML model: expected (N, {expected_features}), "
                f"got {data.shape}"
            )
    else:
        raise InvalidInputError(
            f"Invalid input dimensions for ML model: expected 1D or 2D, got {data.ndim}D"
        )


def validate_dl_input_shape(data: np.ndarray, expected_shape: Tuple[int, int] = (128, 6)):
    """
    Validate input shape for DL models (LSTM, CNN).

    Args:
        data: Input data array
        expected_shape: Expected shape (timesteps, axes), default: (128, 6)

    Raises:
        InvalidInputError: If shape doesn't match expected format
    """
    data = np.array(data)

    expected_timesteps, expected_axes = expected_shape

    # DL models expect 2D array (timesteps, axes) or 3D (batch, timesteps, axes)
    if data.ndim == 2:
        if data.shape != expected_shape:
            raise InvalidInputError(
                f"Invalid input shape for DL model: expected {expected_shape}, "
                f"got {data.shape}"
            )
    elif data.ndim == 3:
        if data.shape[1:] != expected_shape:
            raise InvalidInputError(
                f"Invalid input shape for DL model: expected (N, {expected_timesteps}, {expected_axes}), "
                f"got {data.shape}"
            )
    else:
        raise InvalidInputError(
            f"Invalid input dimensions for DL model: expected 2D or 3D, got {data.ndim}D"
        )


def validate_sensor_values(data: np.ndarray):
    """
    Validate sensor value ranges and detect invalid values.

    Checks for:
    - NaN (not a number)
    - Inf (infinity)
    - Extreme out-of-range values (outside -50 to +50)

    Args:
        data: Sensor data array

    Raises:
        InvalidInputError: If NaN/Inf detected or values extremely out of range
    """
    data = np.array(data)

    # Check for NaN values
    if np.any(np.isnan(data)):
        raise InvalidInputError(
            "Invalid sensor values detected: NaN (not a number) values found. "
            "Please ensure all sensor readings are valid numbers."
        )

    # Check for Inf values
    if np.any(np.isinf(data)):
        raise InvalidInputError(
            "Invalid sensor values detected: Inf (infinity) values found. "
            "Please ensure all sensor readings are finite."
        )

    # Check for extreme out-of-range values
    # Sensor readings typically range from -10 to +10, warn if outside -50 to +50
    if np.any(data < -50) or np.any(data > 50):
        raise InvalidInputError(
            f"Sensor values out of valid range: values must be between -50 and +50. "
            f"Found min: {np.min(data):.2f}, max: {np.max(data):.2f}"
        )
