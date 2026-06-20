"""
Model Architecture Builders

Functions for building and compiling deep learning model architectures.
"""

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Conv1D, BatchNormalization, MaxPooling1D, Flatten
from tensorflow.keras.optimizers import Adam
from typing import Tuple, List


def build_lstm_model(
    input_shape: Tuple[int, int],
    lstm_units_1: int = 64,
    lstm_units_2: int = 32,
    dropout_rate: float = 0.3,
    random_state: int = 42
) -> Sequential:
    """
    Build and compile LSTM model for binary classification.

    Architecture:
    - LSTM layer 1 (return_sequences=True)
    - Dropout
    - LSTM layer 2 (return_sequences=False)
    - Dropout
    - Dense output (sigmoid activation)

    Args:
        input_shape: Tuple of (timesteps, features)
        lstm_units_1: Number of units in first LSTM layer (default: 64)
        lstm_units_2: Number of units in second LSTM layer (default: 32)
        dropout_rate: Dropout rate after each LSTM layer (default: 0.3)
        random_state: Random seed for reproducibility (default: 42)

    Returns:
        Compiled Keras Sequential model
    """
    # Set random seeds for reproducibility
    tf.random.set_seed(random_state)

    model = Sequential([
        # First LSTM layer with return_sequences=True
        LSTM(lstm_units_1, return_sequences=True, input_shape=input_shape),
        Dropout(dropout_rate),

        # Second LSTM layer with return_sequences=False (output final state)
        LSTM(lstm_units_2, return_sequences=False),
        Dropout(dropout_rate),

        # Output layer with sigmoid for binary classification
        Dense(1, activation='sigmoid')
    ])

    # Compile model
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return model


def build_cnn_1d_model(
    input_shape: Tuple[int, int],
    filters: List[int] = [64, 128, 256],
    kernel_size: int = 3,
    pool_size: int = 2,
    dense_units: int = 128,
    dropout_rate: float = 0.5,
    random_state: int = 42
) -> Sequential:
    """
    Build and compile 1D-CNN model for binary classification.

    Architecture:
    - Conv1D layer 1 + BatchNorm + MaxPool
    - Conv1D layer 2 + BatchNorm + MaxPool
    - Conv1D layer 3 + BatchNorm + MaxPool
    - Flatten
    - Dense (hidden layer)
    - Dropout
    - Dense output (sigmoid activation)

    Args:
        input_shape: Tuple of (timesteps, features)
        filters: List of filter counts for each Conv1D layer (default: [64, 128, 256])
        kernel_size: Kernel size for Conv1D layers (default: 3)
        pool_size: Pool size for MaxPooling1D layers (default: 2)
        dense_units: Number of units in dense hidden layer (default: 128)
        dropout_rate: Dropout rate before output layer (default: 0.5)
        random_state: Random seed for reproducibility (default: 42)

    Returns:
        Compiled Keras Sequential model
    """
    # Set random seeds for reproducibility
    tf.random.set_seed(random_state)

    layers = []

    # Add Conv1D blocks
    for i, num_filters in enumerate(filters):
        if i == 0:
            # First layer needs input_shape
            layers.append(Conv1D(num_filters, kernel_size, activation='relu', input_shape=input_shape))
        else:
            layers.append(Conv1D(num_filters, kernel_size, activation='relu'))

        layers.append(BatchNormalization())
        layers.append(MaxPooling1D(pool_size=pool_size))

    # Flatten and dense layers
    layers.extend([
        Flatten(),
        Dense(dense_units, activation='relu'),
        Dropout(dropout_rate),
        Dense(1, activation='sigmoid')
    ])

    model = Sequential(layers)

    # Compile model
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return model
