"""
LSTM Model Training Script for Raw Feature Pipeline

Trains LSTM model using only 6 raw sensor features (aX, aY, aZ, gX, gY, gZ) with sequence input.
Model is saved to backend/dl_models/lstm.h5

Usage:
    python train_lstm.py --dataset Dataset.csv --output dl_models/lstm.h5

Input shape:
    (None, timesteps, 6) where timesteps is sequence length (default: 10)
"""

import argparse
import numpy as np
import os
import sys
from datetime import datetime

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
except ImportError:
    print("ERROR: TensorFlow is required for training DL models.")
    print("Install with: pip install tensorflow")
    sys.exit(1)

# Import feature utilities from ml directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from apps.ml.feature_utils import load_training_data, FEATURE_COLUMNS


def create_sequences(X, y, timesteps=10):
    """
    Convert flat feature array into sequences for LSTM input.

    Args:
        X (np.ndarray): Features array (n_samples, 6)
        y (np.ndarray): Labels array (n_samples,)
        timesteps (int): Number of timesteps per sequence

    Returns:
        tuple: (X_seq, y_seq) where X_seq has shape (n_sequences, timesteps, 6)
    """
    n_samples = len(X)
    n_sequences = n_samples - timesteps + 1

    X_seq = np.zeros((n_sequences, timesteps, 6))
    y_seq = np.zeros(n_sequences)

    for i in range(n_sequences):
        X_seq[i] = X[i:i+timesteps]
        y_seq[i] = y[i+timesteps-1]  # Label from last timestep

    return X_seq, y_seq


def build_lstm_model(timesteps, n_features=6, n_classes=2):
    """
    Build LSTM model with 6-feature input.

    Args:
        timesteps (int): Sequence length
        n_features (int): Number of features per timestep (default: 6)
        n_classes (int): Number of output classes

    Returns:
        keras.Model: Compiled LSTM model
    """
    model = keras.Sequential([
        layers.Input(shape=(timesteps, n_features)),
        layers.LSTM(64, return_sequences=True),
        layers.Dropout(0.3),
        layers.LSTM(32),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.2),
        layers.Dense(n_classes, activation='softmax' if n_classes > 2 else 'sigmoid')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy' if n_classes > 2 else 'binary_crossentropy',
        metrics=['accuracy']
    )

    return model


def train_lstm(X_train, y_train, X_val, y_val, timesteps=10, epochs=50):
    """
    Train LSTM model.

    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        timesteps (int): Sequence length
        epochs (int): Training epochs

    Returns:
        tuple: (model, history, metrics)
    """
    print("\n=== Training LSTM ===")
    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Features: {X_train.shape[2]} ({', '.join(FEATURE_COLUMNS)})")
    print(f"Timesteps: {timesteps}")
    print(f"Input shape: (None, {timesteps}, {X_train.shape[2]})")

    # Determine number of classes
    n_classes = len(np.unique(np.concatenate([y_train, y_val])))
    print(f"Classes: {n_classes}")

    # Build model
    model = build_lstm_model(timesteps, n_features=6, n_classes=n_classes)
    print("\nModel Architecture:")
    model.summary()

    # Callbacks
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-7
        )
    ]

    # Train
    print("\nTraining LSTM...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )

    # Evaluate
    train_loss, train_acc = model.evaluate(X_train, y_train, verbose=0)
    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)

    print("\n--- LSTM Results ---")
    print(f"Training Accuracy: {train_acc:.4f}")
    print(f"Validation Accuracy: {val_acc:.4f}")
    print(f"Validation Loss: {val_loss:.4f}")

    # Calculate F1 score
    from sklearn.metrics import f1_score
    y_pred = np.argmax(model.predict(X_val), axis=1)
    f1 = f1_score(y_val, y_pred, average='weighted')
    print(f"Validation F1 Score: {f1:.4f}")

    metrics = {
        'model_type': 'LSTM',
        'accuracy': float(val_acc),
        'f1_score': float(f1),
        'val_loss': float(val_loss),
        'input_shape': [None, timesteps, 6],
        'n_features': 6,
        'feature_names': FEATURE_COLUMNS,
        'timesteps': timesteps,
        'trained_date': datetime.utcnow().isoformat() + 'Z'
    }

    return model, history, metrics


def save_model(model, output_path, metrics):
    """Save trained LSTM model."""
    # Create output directory
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save model
    model.save(output_path)
    print(f"\n✓ Saved model to {output_path}")

    # Save metrics
    import json
    metrics_path = output_path.replace('.h5', '_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Saved metrics to {metrics_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Train LSTM model with 6-feature sequence input'
    )
    parser.add_argument('--dataset', type=str, default='Dataset.csv')
    parser.add_argument('--output', type=str, default='dl_models/lstm.h5')
    parser.add_argument('--timesteps', type=int, default=10, help='Sequence length')
    parser.add_argument('--epochs', type=int, default=50, help='Training epochs')
    parser.add_argument('--test-size', type=float, default=0.2, help='Validation split')

    args = parser.parse_args()

    try:
        # Load data
        print(f"Loading training data from {args.dataset}...")
        X, y = load_training_data(args.dataset)

        # Create sequences
        print(f"\nCreating sequences with timesteps={args.timesteps}...")
        X_seq, y_seq = create_sequences(X, y, args.timesteps)
        print(f"Sequences created: {X_seq.shape}")

        # Split train/validation
        from sklearn.model_selection import train_test_split
        X_train, X_val, y_train, y_val = train_test_split(
            X_seq, y_seq, test_size=args.test_size, random_state=42, stratify=y_seq
        )

        # Train
        model, history, metrics = train_lstm(
            X_train, y_train, X_val, y_val,
            timesteps=args.timesteps,
            epochs=args.epochs
        )

        # Save
        save_model(model, args.output, metrics)

        # Validation check
        print("\n" + "="*60)
        print("VALIDATION CHECK")
        print("="*60)
        min_f1 = 0.85
        if metrics['f1_score'] >= min_f1:
            print(f"✓ Model meets F1 score requirement (≥ {min_f1})")
        else:
            print(f"⚠ WARNING: Model below F1 score requirement")
            print(f"  F1 Score: {metrics['f1_score']:.4f} < {min_f1}")

        print("\n✓ Training complete!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
