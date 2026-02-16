"""
Model Validation Utility for Raw Feature Pipeline

This module provides startup validation to ensure ML/DL models expect exactly 6 input features.
Prevents dimension mismatch errors during inference by failing fast at application startup.

Usage:
    from apps.ml.validate_models import validate_sklearn_model, validate_keras_model

    model = validate_sklearn_model('ml_models/random_forest.pkl', expected_features=6)
    model = validate_keras_model('dl_models/lstm.h5', expected_features=6)
"""

import joblib
import os


def validate_sklearn_model(model_path, expected_features=6):
    """
    Validate that a scikit-learn model expects the correct number of input features.

    Args:
        model_path (str): Path to .pkl model file (relative or absolute)
        expected_features (int): Expected number of features (default: 6)

    Returns:
        model: Loaded scikit-learn model if validation passes

    Raises:
        ValueError: If model expects different number of features than expected
        FileNotFoundError: If model file doesn't exist
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Load model
    model = joblib.load(model_path)

    # Check n_features_in_ attribute (set during fit())
    if hasattr(model, 'n_features_in_'):
        if model.n_features_in_ != expected_features:
            raise ValueError(
                f"Model input mismatch in {model_path}: "
                f"model expects {model.n_features_in_} features, "
                f"but pipeline provides {expected_features} features"
            )
    else:
        # Warn if model doesn't have n_features_in_ attribute (older sklearn versions)
        print(f"WARNING: Model {model_path} doesn't have n_features_in_ attribute. "
              f"Cannot validate input shape automatically.")

    return model


def validate_keras_model(model_path, expected_features=6):
    """
    Validate that a TensorFlow/Keras model expects the correct number of input features.

    Args:
        model_path (str): Path to .h5 model file (relative or absolute)
        expected_features (int): Expected number of features in last dimension (default: 6)

    Returns:
        model: Loaded Keras model if validation passes

    Raises:
        ValueError: If model expects different number of features than expected
        FileNotFoundError: If model file doesn't exist
        ImportError: If tensorflow is not installed
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    try:
        import tensorflow as tf
    except ImportError:
        raise ImportError(
            "TensorFlow is required to validate Keras models. "
            "Install with: pip install tensorflow"
        )

    # Load model
    model = tf.keras.models.load_model(model_path)

    # Check input shape (None, features) for Dense or (None, timesteps, features) for LSTM
    input_shape = model.input_shape

    # Last dimension should match expected_features
    if input_shape[-1] != expected_features:
        raise ValueError(
            f"Model input mismatch in {model_path}: "
            f"model expects {input_shape[-1]} features in last dimension, "
            f"but pipeline provides {expected_features} features. "
            f"Full input shape: {input_shape}"
        )

    return model


def validate_all_models(ml_model_dir='ml_models', dl_model_dir='dl_models', expected_features=6):
    """
    Validate all models in the specified directories for correct input dimensions.

    Args:
        ml_model_dir (str): Directory containing .pkl models (default: 'ml_models')
        dl_model_dir (str): Directory containing .h5 models (default: 'dl_models')
        expected_features (int): Expected number of input features (default: 6)

    Returns:
        dict: Results with 'passed' (list) and 'failed' (list) model names

    This function is useful for startup validation to check all models at once.
    """
    results = {'passed': [], 'failed': []}

    # Validate ML models (.pkl)
    if os.path.exists(ml_model_dir):
        for filename in os.listdir(ml_model_dir):
            if filename.endswith('.pkl'):
                model_path = os.path.join(ml_model_dir, filename)
                try:
                    validate_sklearn_model(model_path, expected_features)
                    results['passed'].append(filename)
                    print(f"✓ {filename}: Input shape validated (n_features={expected_features})")
                except Exception as e:
                    results['failed'].append((filename, str(e)))
                    print(f"✗ {filename}: Validation failed - {e}")

    # Validate DL models (.h5)
    if os.path.exists(dl_model_dir):
        for filename in os.listdir(dl_model_dir):
            if filename.endswith('.h5'):
                model_path = os.path.join(dl_model_dir, filename)
                try:
                    validate_keras_model(model_path, expected_features)
                    results['passed'].append(filename)
                    print(f"✓ {filename}: Input shape validated (features={expected_features})")
                except Exception as e:
                    results['failed'].append((filename, str(e)))
                    print(f"✗ {filename}: Validation failed - {e}")

    # Summary
    print(f"\nValidation Summary: {len(results['passed'])} passed, {len(results['failed'])} failed")

    if results['failed']:
        print("\nFailed models:")
        for model_name, error in results['failed']:
            print(f"  - {model_name}: {error}")
        raise ValueError(
            f"Model validation failed for {len(results['failed'])} model(s). "
            f"Please retrain models with 6-feature input."
        )

    return results


if __name__ == '__main__':
    # Test validation when run as script
    import sys

    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        expected = int(sys.argv[2]) if len(sys.argv) > 2 else 6

        if model_path.endswith('.pkl'):
            model = validate_sklearn_model(model_path, expected)
            print(f"✓ Model validated: n_features_in_ = {model.n_features_in_}")
        elif model_path.endswith('.h5'):
            model = validate_keras_model(model_path, expected)
            print(f"✓ Model validated: input_shape = {model.input_shape}")
        else:
            print("ERROR: Unsupported model format. Use .pkl for sklearn or .h5 for Keras.")
            sys.exit(1)
    else:
        # Validate all models in default directories
        print("Validating all models...")
        validate_all_models()
