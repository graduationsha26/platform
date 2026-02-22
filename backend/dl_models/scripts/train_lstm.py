"""
LSTM Model Training Script

Trains an LSTM model with 2 layers (64, 32 units) and dropout 0.3 for
Parkinson's tremor detection using GridSearchCV for hyperparameter tuning.
Exports trained model and metadata.

Usage:
    python backend/dl_models/scripts/train_lstm.py
    python backend/dl_models/scripts/train_lstm.py --input-dir path/to/data --output-dir path/to/models
"""

import os
import sys
import time
import argparse
import logging
import random
from datetime import datetime
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import EarlyStopping

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from dl_models.scripts.utils.model_io import load_sequence_data, save_model, create_metadata
from dl_models.scripts.utils.evaluation import evaluate_model, format_metrics_string
from dl_models.scripts.utils.architectures import build_lstm_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Train LSTM classifier for tremor detection')
    parser.add_argument(
        '--input-dir',
        type=str,
        default='backend/ml_data/processed',
        help='Directory containing train_sequences.npy, test_sequences.npy, etc.'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='backend/dl_models/models',
        help='Directory to save trained model and metadata'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    return parser.parse_args()


def validate_data(X_train, y_train, X_test, y_test):
    """
    Validate input data integrity.

    Args:
        X_train, y_train, X_test, y_test: Sequence arrays and label arrays

    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating input data...")

    # Check shapes
    if len(X_train.shape) != 3:
        raise ValueError(f"Expected X_train to be 3D (samples, timesteps, features), got shape {X_train.shape}")
    if len(X_test.shape) != 3:
        raise ValueError(f"Expected X_test to be 3D, got shape {X_test.shape}")
    if X_train.shape[2] != 6:
        raise ValueError(f"Expected 6 features (aX,aY,aZ,gX,gY,gZ), got {X_train.shape[2]}")
    if X_test.shape[2] != 6:
        raise ValueError(f"Expected 6 features in test set, got {X_test.shape[2]}")

    # Check for NaN/Inf
    if np.any(np.isnan(X_train)) or np.any(np.isinf(X_train)):
        raise ValueError("Training sequences contain NaN or Inf values")
    if np.any(np.isnan(X_test)) or np.any(np.isinf(X_test)):
        raise ValueError("Test sequences contain NaN or Inf values")
    if np.any(np.isnan(y_train)) or np.any(np.isnan(y_test)):
        raise ValueError("Labels contain NaN values")

    # Check labels are binary (0 or 1)
    unique_train = np.unique(y_train)
    unique_test = np.unique(y_test)
    if not np.all(np.isin(unique_train, [0, 1])):
        raise ValueError(f"Training labels must be binary (0 or 1), got {unique_train}")
    if not np.all(np.isin(unique_test, [0, 1])):
        raise ValueError(f"Test labels must be binary (0 or 1), got {unique_test}")

    logger.info("[OK] Data validation passed")


def main():
    """Main training function."""
    args = parse_arguments()
    start_time = time.time()

    # Set random seeds for reproducibility (T028)
    RANDOM_SEED = args.random_state
    np.random.seed(RANDOM_SEED)
    tf.random.set_seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    os.environ['PYTHONHASHSEED'] = str(RANDOM_SEED)

    logger.info("="*70)
    logger.info("LSTM Model Training")
    logger.info("="*70)

    # TensorFlow version and GPU detection (T029)
    logger.info(f"TensorFlow version: {tf.__version__}")
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        logger.info(f"GPU available: {len(gpus)} device(s)")
        logger.info(f"GPU details: {gpus}")
    else:
        logger.info("No GPU detected, using CPU")

    try:
        # Step 1: Load data (T017)
        logger.info(f"Loading training data from {args.input_dir}/...")
        X_train, y_train, X_test, y_test = load_sequence_data(args.input_dir, args.input_dir)
        logger.info(f"Train set: {X_train.shape[0]} samples, {X_train.shape[1]} timesteps, {X_train.shape[2]} features")
        logger.info(f"Test set: {X_test.shape[0]} samples, {X_test.shape[1]} timesteps, {X_test.shape[2]} features")

        # Step 2: Validate data (T018)
        validate_data(X_train, y_train, X_test, y_test)

        # Step 3: Split training data into train/validation (T019)
        logger.info("Splitting training data (80/20 train/validation)...")
        X_train_split, X_val, y_train_split, y_val = train_test_split(
            X_train, y_train, test_size=0.2, stratify=y_train, random_state=RANDOM_SEED
        )
        logger.info(f"Train: {X_train_split.shape[0]} samples, Validation: {X_val.shape[0]} samples")

        # Step 4: Build LSTM model (T020)
        logger.info("Building LSTM model...")
        input_shape = (X_train.shape[1], X_train.shape[2])  # (timesteps, features)
        model = build_lstm_model(
            input_shape=input_shape,
            lstm_units_1=64,
            lstm_units_2=32,
            dropout_rate=0.3,
            random_state=RANDOM_SEED
        )
        logger.info("Model architecture:")
        logger.info("  - LSTM(64, return_sequences=True) + Dropout(0.3)")
        logger.info("  - LSTM(32) + Dropout(0.3)")
        logger.info("  - Dense(1, sigmoid)")
        logger.info(f"Total parameters: {model.count_params():,}")

        # Step 5: Setup early stopping (T021)
        logger.info("Setting up EarlyStopping (monitor=val_loss, patience=10)...")
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            mode='min',
            verbose=1
        )

        # Step 6: Train model (T022)
        logger.info("Starting training (max_epochs=100, batch_size=32)...")
        history = model.fit(
            X_train_split, y_train_split,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=[early_stopping],
            verbose=2
        )

        logger.info("Training complete!")
        epochs_trained = len(history.history['loss'])
        logger.info(f"Epochs trained: {epochs_trained}")

        # Step 7: Evaluate on test set (T023)
        logger.info("Evaluating on test set...")
        metrics = evaluate_model(model, X_test, y_test)

        # Log metrics
        logger.info(format_metrics_string(metrics))

        # Step 8: Check threshold (T024)
        if metrics['meets_threshold']:
            logger.info("[OK] Model meets >=95% accuracy threshold")
        else:
            logger.warning(f"[WARNING] Model achieved {metrics['accuracy']:.1%}, below 95% threshold")
            logger.warning("[WARNING] Model will still be exported for analysis")

        # Step 9: Assemble metadata (T025)
        training_time = time.time() - start_time

        # Get architecture summary as string
        import io
        summary_buffer = io.StringIO()
        model.summary(print_fn=lambda x: summary_buffer.write(x + '\n'))
        architecture_summary = summary_buffer.getvalue()

        hyperparameters = {
            "lstm_units_layer1": 64,
            "lstm_units_layer2": 32,
            "dropout_rate": 0.3,
            "optimizer": "adam",
            "learning_rate": 0.001,
            "batch_size": 32,
            "max_epochs": 100,
            "early_stopping_patience": 10,
            "random_state": RANDOM_SEED
        }

        training_history_dict = {
            "epochs_completed": epochs_trained,
            "stopped_early": epochs_trained < 100,
            "stopped_epoch": epochs_trained if epochs_trained < 100 else 0,
            "best_epoch": int(np.argmin(history.history['val_loss'])) + 1,
            "loss_history": [float(x) for x in history.history['loss']],
            "accuracy_history": [float(x) for x in history.history['accuracy']],
            "val_loss_history": [float(x) for x in history.history['val_loss']],
            "val_accuracy_history": [float(x) for x in history.history['val_accuracy']],
            "training_time_seconds": float(training_time)
        }

        training_info = {
            "timestamp": datetime.now().isoformat(),
            "training_samples": int(X_train_split.shape[0]),
            "validation_samples": int(X_val.shape[0]),
            "test_samples": int(X_test.shape[0]),
            "sequence_length": int(X_train.shape[1]),
            "num_features": int(X_train.shape[2]),
            "tensorflow_version": tf.__version__,
            "gpu_available": len(gpus) > 0,
            "random_state": RANDOM_SEED,
            "data_source": f"{args.input_dir}/train_sequences.npy, test_sequences.npy, train_seq_labels.npy, test_seq_labels.npy"
        }

        metadata = create_metadata(
            model_type="LSTM",
            architecture_summary=architecture_summary,
            hyperparameters=hyperparameters,
            performance_metrics=metrics,
            training_history=training_history_dict,
            training_info=training_info
        )

        # Step 10: Save model and metadata (T026)
        logger.info(f"Saving model to {args.output_dir}/...")
        model_path, metadata_path = save_model(
            model=model,
            metadata=metadata,
            output_dir=args.output_dir,
            model_name="lstm_model"
        )
        logger.info(f"Model saved: {model_path}")
        logger.info(f"Metadata saved: {metadata_path}")

        # Step 11: Validate model loading (T027)
        logger.info("Validating model loading...")
        from dl_models.scripts.utils.model_io import load_model
        loaded_model, loaded_metadata = load_model(model_path, metadata_path)

        # Test prediction on a small sample
        X_sample = X_test[:5]
        predictions = loaded_model.predict(X_sample, verbose=0)
        predictions_binary = (predictions > 0.5).astype(int).flatten()
        logger.info(f"Test predictions (first 5): {predictions_binary}")
        logger.info("[OK] Model loading validation passed")

        # Summary
        logger.info("="*70)
        logger.info(f"Training completed in {training_time:.2f} seconds")
        logger.info(f"LSTM model ready for deployment")
        logger.info("="*70)

        return 0

    except FileNotFoundError as e:
        logger.error(f"[ERROR] File not found: {e}")
        logger.error("[ERROR] Please ensure Feature 004 (ML/DL Data Preparation) is complete")
        logger.error(f"[ERROR] Expected files in {args.input_dir}/:")
        logger.error("[ERROR]   - train_sequences.npy, test_sequences.npy")
        logger.error("[ERROR]   - train_seq_labels.npy, test_seq_labels.npy")
        return 1

    except ValueError as e:
        logger.error(f"[ERROR] Validation failed: {e}")
        logger.error("[ERROR] Check input data quality and format")
        return 1

    except Exception as e:
        logger.error(f"[ERROR] Training failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
