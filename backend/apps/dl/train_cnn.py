"""
CNN Model Training Script for Raw Feature Pipeline

Trains 1D CNN model using only 6 raw sensor features (aX, aY, aZ, gX, gY, gZ).
Model is saved to backend/dl_models/cnn.h5

Usage:
    python train_cnn.py --dataset Dataset.csv --output dl_models/cnn.h5

Input shape:
    (None, 6, 1) - treating 6 features as a 1D sequence with 1 channel
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

# Import feature utilities
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from apps.ml.feature_utils import load_training_data, FEATURE_COLUMNS


def reshape_for_cnn(X):
    """
    Reshape features for 1D CNN input.

    Args:
        X (np.ndarray): Features array (n_samples, 6)

    Returns:
        np.ndarray: Reshaped array (n_samples, 6, 1)
    """
    return X.reshape(X.shape[0], X.shape[1], 1)


def build_cnn_model(n_features=6, n_classes=2):
    """
    Build 1D CNN model with 6-feature input.

    Args:
        n_features (int): Number of features (default: 6)
        n_classes (int): Number of output classes

    Returns:
        keras.Model: Compiled CNN model
    """
    model = keras.Sequential([
        layers.Input(shape=(n_features, 1)),

        # First conv block
        layers.Conv1D(64, kernel_size=3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=2),
        layers.Dropout(0.3),

        # Second conv block
        layers.Conv1D(32, kernel_size=3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.3),

        # Flatten and dense layers
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.4),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(n_classes, activation='softmax' if n_classes > 2 else 'sigmoid')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy' if n_classes > 2 else 'binary_crossentropy',
        metrics=['accuracy']
    )

    return model


def train_cnn(X_train, y_train, X_val, y_val, epochs=30):
    """
    Train CNN model.

    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        epochs (int): Training epochs

    Returns:
        tuple: (model, history, metrics)
    """
    print("\n=== Training CNN ===")
    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Features: {X_train.shape[1]} ({', '.join(FEATURE_COLUMNS)})")
    print(f"Input shape: {X_train.shape}")

    # Determine number of classes
    n_classes = len(np.unique(np.concatenate([y_train, y_val])))
    print(f"Classes: {n_classes}")

    # Build model
    model = build_cnn_model(n_features=6, n_classes=n_classes)
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
    print("\nTraining CNN...")
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

    print("\n--- CNN Results ---")
    print(f"Training Accuracy: {train_acc:.4f}")
    print(f"Validation Accuracy: {val_acc:.4f}")
    print(f"Validation Loss: {val_loss:.4f}")

    # Calculate F1 score
    from sklearn.metrics import f1_score
    y_pred = np.argmax(model.predict(X_val), axis=1) if n_classes > 2 else (model.predict(X_val) > 0.5).astype(int).flatten()
    f1 = f1_score(y_val, y_pred, average='weighted')
    print(f"Validation F1 Score: {f1:.4f}")

    metrics = {
        'model_type': 'CNN',
        'accuracy': float(val_acc),
        'f1_score': float(f1),
        'val_loss': float(val_loss),
        'input_shape': [None, 6, 1],
        'n_features': 6,
        'feature_names': FEATURE_COLUMNS,
        'trained_date': datetime.utcnow().isoformat() + 'Z'
    }

    return model, history, metrics


def save_model(model, output_path, metrics):
    """Save trained CNN model."""
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
        description='Train CNN model with 6-feature input'
    )
    parser.add_argument('--dataset', type=str, default='Dataset.csv')
    parser.add_argument('--output', type=str, default='dl_models/cnn.h5')
    parser.add_argument('--epochs', type=int, default=30, help='Training epochs')
    parser.add_argument('--test-size', type=float, default=0.2, help='Validation split')

    args = parser.parse_args()

    try:
        # Load data
        print(f"Loading training data from {args.dataset}...")
        X, y = load_training_data(args.dataset)

        # Reshape for CNN
        print("\nReshaping features for CNN (n_samples, 6, 1)...")
        X_cnn = reshape_for_cnn(X)
        print(f"Reshaped: {X_cnn.shape}")

        # Split train/validation
        from sklearn.model_selection import train_test_split
        X_train, X_val, y_train, y_val = train_test_split(
            X_cnn, y, test_size=args.test_size, random_state=42, stratify=y
        )

        # Train
        model, history, metrics = train_cnn(
            X_train, y_train, X_val, y_val,
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
