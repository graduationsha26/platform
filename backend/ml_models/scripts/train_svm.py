"""
SVM Classifier Training Script

Trains an SVM classifier with RBF kernel for Parkinson's tremor detection using
GridSearchCV for hyperparameter tuning. Exports trained model and metadata.

Usage:
    python backend/ml_models/scripts/train_svm.py
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

# Resolve backend/ directory from this script's location so paths work
# regardless of which directory the script is invoked from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

# Add parent directory to path for imports
sys.path.insert(0, str(_BACKEND_DIR))
from ml_models.scripts.utils.model_io import load_feature_data, save_model, create_metadata
from ml_models.scripts.utils.evaluation import evaluate_model, format_metrics_string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Train SVM classifier for tremor detection')
    parser.add_argument(
        '--input',
        type=str,
        default=str(_BACKEND_DIR / 'ml_data' / 'processed' / 'ready_for_training_features.csv'),
        help='Path to ready_for_training_features.csv (42 features + label)'
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
        X_train, y_train, X_test, y_test: Feature and label arrays

    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating input data...")

    # Check shapes
    if X_train.shape[1] != 42:
        raise ValueError(f"Expected 42 features, got {X_train.shape[1]}")
    if X_test.shape[1] != 42:
        raise ValueError(f"Expected 42 features in test set, got {X_test.shape[1]}")

    # Check for NaN/Inf
    if np.any(np.isnan(X_train)) or np.any(np.isinf(X_train)):
        raise ValueError("Training features contain NaN or Inf values")
    if np.any(np.isnan(X_test)) or np.any(np.isinf(X_test)):
        raise ValueError("Test features contain NaN or Inf values")
    if np.any(np.isnan(y_train)) or np.any(np.isnan(y_test)):
        raise ValueError("Labels contain NaN values")

    # Check labels are binary (0 or 1)
    if not np.all(np.isin(y_train, [0, 1])):
        raise ValueError("Training labels must be binary (0 or 1)")
    if not np.all(np.isin(y_test, [0, 1])):
        raise ValueError("Test labels must be binary (0 or 1)")

    logger.info("[OK] Data validation passed")


def cleanup_old_svm_files():
    """Delete superseded SVM model and metrics files after successful training."""
    models_dir_files = [
        "svm_model.pkl", "svm_model.json",
        "svm_rbf.pkl", "svm_rbf.json",
    ]
    root_files = [
        "svm_model.pkl", "svm_model.json",
        "svm_rbf.pkl", "svm_rbf.json",
        "svm_model_metrics.json",
    ]
    for fname in models_dir_files:
        path = _BACKEND_DIR / 'ml_models' / 'models' / fname
        if path.exists():
            path.unlink()
            logger.info(f"Removed: {path}")
    for fname in root_files:
        path = _BACKEND_DIR / 'ml_models' / fname
        if path.exists():
            path.unlink()
            logger.info(f"Removed: {path}")
    logger.info("[OK] Old SVM files cleaned up")


def main():
    """Main training function."""
    args = parse_arguments()
    start_time = time.time()

    logger.info("="*70)
    logger.info("SVM Classifier Training (RBF Kernel)")
    logger.info("="*70)

    try:
        # Step 1: Load data
        logger.info(f"Loading data from {args.input}...")
        if not os.path.exists(args.input):
            raise FileNotFoundError(f"Input file not found: {args.input}")
        df = pd.read_csv(args.input)
        if len(df.columns) != 43:
            raise ValueError(f"Expected 43 columns (42 features + label), got {len(df.columns)}")
        if 'label' not in df.columns:
            raise ValueError("Input CSV missing 'label' column")
        logger.info(f"Dataset: {len(df)} total samples, {len(df.columns)-1} features")

        X = df.drop('label', axis=1).values
        y = df['label'].values
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=args.random_state, stratify=y
        )
        logger.info(f"Train set: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        logger.info(f"Test set: {X_test.shape[0]} samples, {X_test.shape[1]} features")
        logger.info(f"Label distribution — Train: Control={int((y_train==0).sum())}, Parkinson={int((y_train==1).sum())} | Test: {int((y_test==0).sum())}, {int((y_test==1).sum())}")

        # Step 1b: Scale features (SVM with RBF kernel is sensitive to feature scale)
        logger.info("Applying StandardScaler (fit on train only)...")
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        logger.info("[OK] Features scaled")

        # Step 2: Validate data
        validate_data(X_train, y_train, X_test, y_test)

        # Step 3: Define hyperparameter search space
        logger.info("Defining hyperparameter search space...")
        param_grid = {
            'C': [0.1, 1, 10, 100],
            'gamma': [0.001, 0.01, 0.1, 1]
        }
        total_combinations = len(param_grid['C']) * len(param_grid['gamma'])
        logger.info(f"Testing {total_combinations} parameter combinations")
        logger.info(f"Kernel: RBF (fixed)")

        # Step 4: Setup GridSearchCV
        logger.info("Setting up GridSearchCV...")
        base_estimator = SVC(kernel='rbf', random_state=args.random_state)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.random_state)
        grid_search = GridSearchCV(
            estimator=base_estimator,
            param_grid=param_grid,
            cv=cv,
            scoring='accuracy',
            n_jobs=-1,  # Use all CPU cores
            verbose=2,  # Show progress
            return_train_score=False
        )

        # Step 5: Execute GridSearchCV
        logger.info("Starting GridSearchCV (this may take several minutes)...")
        grid_search.fit(X_train_scaled, y_train)

        # Step 6: Extract best model and parameters
        logger.info("GridSearchCV complete!")
        best_model = grid_search.best_estimator_
        best_params = grid_search.best_params_
        best_cv_score = grid_search.best_score_

        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best CV score: {best_cv_score:.4f}")

        # Get all CV scores for the best model
        best_index = grid_search.best_index_
        cv_scores = grid_search.cv_results_['split0_test_score'][best_index:best_index+5]

        # Step 7: Evaluate on test set
        logger.info("Evaluating on test set...")
        metrics = evaluate_model(best_model, X_test_scaled, y_test)

        # Log metrics
        logger.info(format_metrics_string(metrics))

        # Check threshold
        if metrics['meets_threshold']:
            logger.info("[OK] Model meets >=95% accuracy threshold")
        else:
            logger.warning(f"[WARNING] Model achieved {metrics['accuracy']:.1%}, below 95% threshold")

        # Step 8: Assemble metadata
        training_time = time.time() - start_time

        # Add kernel to hyperparameters
        full_hyperparameters = dict(best_params)
        full_hyperparameters['kernel'] = 'rbf'
        full_hyperparameters['random_state'] = args.random_state

        metadata = create_metadata(
            model_type="SVC",
            hyperparameters=full_hyperparameters,
            performance_metrics=metrics,
            cross_validation={
                "cv_scores": [float(s) for s in cv_scores] if hasattr(cv_scores, '__iter__') else [float(best_cv_score)],
                "cv_mean": float(best_cv_score),
                "cv_std": float(np.std(cv_scores)) if hasattr(cv_scores, '__iter__') else 0.0
            },
            training_info={
                "timestamp": datetime.now().isoformat(),
                "training_time_seconds": float(training_time),
                "training_samples": int(X_train.shape[0]),
                "test_samples": int(X_test.shape[0]),
                "feature_count": int(X_train.shape[1]),
                "dataset_source": os.path.basename(args.input),
                "random_state": args.random_state,
                "scaled": True,
            }
        )

        # Step 8b: Embed gravity filter parameters in metadata.
        # The inference service reads filter_params from the model metadata to apply
        # the identical preprocessing to live sensor data (FR-005, FR-008).
        filter_params_path = str(_BACKEND_DIR / 'ml_data' / 'processed' / 'filter_params.json')
        if os.path.exists(filter_params_path):
            with open(filter_params_path) as _fp:
                metadata["filter_params"] = json.load(_fp)
            logger.info("[OK] Gravity filter parameters embedded in metadata")
        else:
            logger.warning(
                f"[WARNING] filter_params.json not found at {filter_params_path}. "
                "Run 4_psmad_pipeline.py first. Metadata saved WITHOUT filter_params."
            )

        # Step 9: Save model and metadata
        output_dir = str(_BACKEND_DIR / 'ml_models' / 'models')
        logger.info(f"Saving model to {output_dir}/...")
        model_path, _ = save_model(
            model=best_model,
            metadata=metadata,
            output_dir=output_dir,
            model_name="svm_model_v1"
        )
        logger.info(f"Model saved: {model_path}")

        metrics_path = str(_BACKEND_DIR / 'ml_models' / 'svm_model_metrics_v1.json')
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
        with open(metrics_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metrics saved: {metrics_path}")

        # Step 9b: Clean up superseded SVM files
        cleanup_old_svm_files()

        # Step 10: Validate model loading
        logger.info("Validating model loading...")
        import joblib
        loaded_model = joblib.load(model_path)

        # Test prediction on a small sample (use scaled test data)
        X_sample = X_test_scaled[:5]
        predictions = loaded_model.predict(X_sample)
        logger.info(f"Test predictions: {predictions}")
        logger.info("[OK] Model loading validation passed")

        # Summary
        logger.info("="*70)
        logger.info(f"Training completed in {training_time:.2f} seconds")
        logger.info(f"SVM (RBF kernel) model ready for deployment")
        logger.info("="*70)

        return 0

    except FileNotFoundError as e:
        logger.error(f"[ERROR] File not found: {e}")
        logger.error("[ERROR] Please ensure Feature 036 (PSMAD preprocessing) is complete")
        logger.error("[ERROR] Expected file: backend/ml_data/processed/ready_for_training_features.csv")
        return 1

    except ValueError as e:
        logger.error(f"[ERROR] Validation failed: {e}")
        logger.error("[ERROR] Check input data quality and format")
        return 1

    except Exception as e:
        logger.error(f"[ERROR] Training failed: {e}")
        logger.error("[ERROR] Check logs for details")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
