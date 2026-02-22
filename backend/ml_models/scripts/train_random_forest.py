"""
Random Forest Classifier Training Script

Trains a Random Forest classifier for Parkinson's tremor detection using
GridSearchCV for hyperparameter tuning. Exports trained model and metadata.

Usage:
    python backend/ml_models/scripts/train_random_forest.py
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
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
    parser = argparse.ArgumentParser(description='Train Random Forest classifier for tremor detection')
    parser.add_argument(
        '--input-dir',
        type=str,
        default='backend/ml_data/processed',
        help='Directory containing train_features.csv and test_features.csv'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='backend/ml_models/models',
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
        X_train, y_train, X_test, y_test: Feature and label arrays

    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating input data...")

    # Check shapes
    if X_train.shape[1] != 30:
        raise ValueError(f"Expected 30 features, got {X_train.shape[1]}")
    if X_test.shape[1] != 30:
        raise ValueError(f"Expected 30 features in test set, got {X_test.shape[1]}")

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


def main():
    """Main training function."""
    args = parse_arguments()
    start_time = time.time()

    logger.info("="*70)
    logger.info("Random Forest Classifier Training")
    logger.info("="*70)

    try:
        # Step 1: Load data
        logger.info(f"Loading training data from {args.input_dir}/...")
        train_path = os.path.join(args.input_dir, 'train_features.csv')
        test_path = os.path.join(args.input_dir, 'test_features.csv')

        X_train, y_train, X_test, y_test = load_feature_data(train_path, test_path)
        logger.info(f"Train set: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        logger.info(f"Test set: {X_test.shape[0]} samples, {X_test.shape[1]} features")

        # Step 2: Validate data
        validate_data(X_train, y_train, X_test, y_test)

        # Step 3: Define hyperparameter search space
        logger.info("Defining hyperparameter search space...")
        param_grid = {
            'n_estimators': [50, 100, 200, 300],
            'max_depth': [10, 20, 30, None]
        }
        total_combinations = len(param_grid['n_estimators']) * len(param_grid['max_depth'])
        logger.info(f"Testing {total_combinations} parameter combinations")

        # Step 4: Setup GridSearchCV
        logger.info("Setting up GridSearchCV...")
        base_estimator = RandomForestClassifier(random_state=args.random_state)
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
        grid_search.fit(X_train, y_train)

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
        metrics = evaluate_model(best_model, X_test, y_test)

        # Log metrics
        logger.info(format_metrics_string(metrics))

        # Check threshold
        if metrics['meets_threshold']:
            logger.info("[OK] Model meets >=95% accuracy threshold")
        else:
            logger.warning(f"[WARNING] Model achieved {metrics['accuracy']:.1%}, below 95% threshold")

        # Step 8: Assemble metadata
        training_time = time.time() - start_time
        metadata = create_metadata(
            model_type="RandomForestClassifier",
            hyperparameters=best_params,
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
                "random_state": args.random_state,
                "data_source": f"{args.input_dir}/train_features.csv, {args.input_dir}/test_features.csv"
            }
        )

        # Step 9: Save model and metadata
        logger.info(f"Saving model to {args.output_dir}/...")
        model_path, metadata_path = save_model(
            model=best_model,
            metadata=metadata,
            output_dir=args.output_dir,
            model_name="random_forest"
        )
        logger.info(f"Model saved: {model_path}")
        logger.info(f"Metadata saved: {metadata_path}")

        # Step 10: Validate model loading
        logger.info("Validating model loading...")
        loaded_model, loaded_metadata = __import__('ml_models.scripts.utils.model_io', fromlist=['load_model']).load_model(model_path, metadata_path)

        # Test prediction on a small sample
        X_sample = X_test[:5]
        predictions = loaded_model.predict(X_sample)
        logger.info(f"Test predictions: {predictions}")
        logger.info("[OK] Model loading validation passed")

        # Summary
        logger.info("="*70)
        logger.info(f"Training completed in {training_time:.2f} seconds")
        logger.info(f"Random Forest model ready for deployment")
        logger.info("="*70)

        return 0

    except FileNotFoundError as e:
        logger.error(f"[ERROR] File not found: {e}")
        logger.error("[ERROR] Please ensure Feature 004 (ML/DL Data Preparation) is complete")
        logger.error("[ERROR] Expected files: train_features.csv, test_features.csv in backend/ml_data/processed/")
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
