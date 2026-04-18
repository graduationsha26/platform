"""
Random Forest Classifier Training Script — v3 Pipeline

Trains a Random Forest classifier for Parkinson's tremor detection using
GridSearchCV for hyperparameter tuning. Loads pre-extracted feature matrices
(X_features.npy, y_labels.npy) produced by 5_aggregate_and_extract.py.

Saves v3 artifacts:
  backend/ml_models/models/rf_model_v3.pkl        — trained RandomForestClassifier
  backend/ml_models/models/rf_model_v3_scaler.pkl — fitted StandardScaler
  backend/ml_models/models/rf_model_v3.json        — metadata (feature order, pipeline params)
  backend/ml_models/rf_model_metrics_v3.json       — detailed metrics

Usage:
    py backend/ml_models/scripts/train_random_forest.py
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

# Resolve backend/ directory from this script's location
# Script: backend/ml_models/scripts/train_random_forest.py
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from ml_data.utils.feature_extractors import get_feature_names
from ml_models.scripts.utils.evaluation import evaluate_model, format_metrics_string

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
MODEL_VERSION = 3


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Train Random Forest v2 for tremor detection'
    )
    parser.add_argument(
        '--x-input',
        type=str,
        default=str(_BACKEND_DIR / 'ml_data' / 'processed' / 'X_features.npy'),
        help='Path to X_features.npy'
    )
    parser.add_argument(
        '--y-input',
        type=str,
        default=str(_BACKEND_DIR / 'ml_data' / 'processed' / 'y_labels.npy'),
        help='Path to y_labels.npy'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    return parser.parse_args()


def validate_data(X_train, y_train, X_test, y_test):
    logger.info('Validating input data...')

    if X_train.shape[1] != 42:
        raise ValueError(f'Expected 42 features, got {X_train.shape[1]}')
    if X_test.shape[1] != 42:
        raise ValueError(f'Expected 42 features in test set, got {X_test.shape[1]}')

    for name, arr in [('X_train', X_train), ('X_test', X_test)]:
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            raise ValueError(f'{name} contains NaN or Inf values')

    if np.any(np.isnan(y_train)) or np.any(np.isnan(y_test)):
        raise ValueError('Labels contain NaN values')

    if not np.all(np.isin(y_train, [0, 1])):
        raise ValueError('Training labels must be binary (0 or 1)')
    if not np.all(np.isin(y_test, [0, 1])):
        raise ValueError('Test labels must be binary (0 or 1)')

    logger.info('[OK] Data validation passed')


def main():
    args = parse_arguments()
    start_time = time.time()

    logger.info('=' * 70)
    logger.info(f'Random Forest Classifier Training — v{MODEL_VERSION}')
    logger.info('=' * 70)

    # -----------------------------------------------------------------------
    # Step 1: Load .npy feature matrices
    # -----------------------------------------------------------------------
    logger.info(f'Loading X from {args.x_input}...')
    logger.info(f'Loading y from {args.y_input}...')

    for path in (args.x_input, args.y_input):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f'Input file not found: {path}\n'
                'Run 5_aggregate_and_extract.py first.'
            )

    X = np.load(args.x_input)
    y = np.load(args.y_input)

    logger.info(f'Dataset: {X.shape[0]} windows, {X.shape[1]} features')
    logger.info(f'Label distribution: Normal(0)={int((y == 0).sum())}  Parkinson(1)={int((y == 1).sum())}')

    # -----------------------------------------------------------------------
    # Step 2: Train/test split
    # -----------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=args.random_state, stratify=y
    )
    logger.info(f'Train set: {X_train.shape[0]} samples')
    logger.info(f'Test set : {X_test.shape[0]} samples')

    validate_data(X_train, y_train, X_test, y_test)

    # -----------------------------------------------------------------------
    # Step 3: Fit StandardScaler on train split only
    # -----------------------------------------------------------------------
    logger.info('Fitting StandardScaler on training data...')
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)
    logger.info('[OK] Scaler fitted')

    # -----------------------------------------------------------------------
    # Step 4: GridSearchCV
    # -----------------------------------------------------------------------
    param_grid = {
        'n_estimators': [50, 100, 200, 300],
        'max_depth': [10, 20, 30, None],
    }
    total_combos = len(param_grid['n_estimators']) * len(param_grid['max_depth'])
    logger.info(f'Starting GridSearchCV ({total_combos} combinations, 5-fold CV)...')

    base_estimator = RandomForestClassifier(random_state=args.random_state)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.random_state)
    grid_search = GridSearchCV(
        estimator=base_estimator,
        param_grid=param_grid,
        cv=cv,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1,
        return_train_score=False,
    )
    grid_search.fit(X_train_scaled, y_train)

    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_cv_score = float(grid_search.best_score_)

    logger.info(f'Best parameters : {best_params}')
    logger.info(f'Best CV score   : {best_cv_score:.4f}')

    # -----------------------------------------------------------------------
    # Step 5: Evaluate on test set
    # -----------------------------------------------------------------------
    logger.info('Evaluating on test set...')
    metrics = evaluate_model(best_model, X_test_scaled, y_test)
    logger.info(format_metrics_string(metrics))

    if metrics['accuracy'] >= 0.80:
        logger.info('[OK] Model meets ≥80% accuracy threshold')
    else:
        logger.warning(
            f'[WARNING] Model achieved {metrics["accuracy"]:.1%}, below 80% threshold'
        )

    # -----------------------------------------------------------------------
    # Step 6: Assemble metadata
    # -----------------------------------------------------------------------
    training_time = time.time() - start_time
    feature_names = get_feature_names(AXIS_NAMES)

    # Retrieve per-fold CV scores for best index
    best_idx = grid_search.best_index_
    n_splits = cv.get_n_splits()
    cv_scores = [
        float(grid_search.cv_results_[f'split{i}_test_score'][best_idx])
        for i in range(n_splits)
    ]

    metadata = {
        'model_type': 'RandomForestClassifier',
        'version': MODEL_VERSION,
        'feature_names': feature_names,
        'pipeline_params': {
            'window_size': 100,
            'stride': 15,
            'mpu6050_accel_sensitivity': 16384.0,
            'mpu6050_gyro_sensitivity': 131.0,
            'accel_to_ms2': True,
            'training_sampling_rate_hz': 250.0,
            'fft_tremor_band_low_hz': 3.0,
            'fft_tremor_band_high_hz': 12.0,
        },
        'scaler_file': f'rf_model_v{MODEL_VERSION}_scaler.pkl',
        'hyperparameters': best_params,
        'performance_metrics': metrics,
        'cross_validation': {
            'cv_scores': cv_scores,
            'cv_mean': best_cv_score,
            'cv_std': float(np.std(cv_scores)),
        },
        'training_info': {
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': float(training_time),
            'training_samples': int(X_train.shape[0]),
            'test_samples': int(X_test.shape[0]),
            'feature_count': int(X_train.shape[1]),
            'data_source': 'Data v2 (Normal + Parkinson) — raw ADC converted to physical units',
            'random_state': args.random_state,
        },
    }

    # -----------------------------------------------------------------------
    # Step 7: Save artifacts
    # -----------------------------------------------------------------------
    output_dir = _BACKEND_DIR / 'ml_models' / 'models'
    os.makedirs(output_dir, exist_ok=True)

    model_path  = output_dir / f'rf_model_v{MODEL_VERSION}.pkl'
    scaler_path = output_dir / f'rf_model_v{MODEL_VERSION}_scaler.pkl'
    meta_path   = output_dir / f'rf_model_v{MODEL_VERSION}.json'
    metrics_path = _BACKEND_DIR / 'ml_models' / f'rf_model_metrics_v{MODEL_VERSION}.json'

    joblib.dump(best_model, model_path)
    logger.info(f'Model saved  → {model_path}')

    joblib.dump(scaler, scaler_path)
    logger.info(f'Scaler saved → {scaler_path}')

    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f'Metadata saved → {meta_path}')

    with open(metrics_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f'Metrics saved  → {metrics_path}')

    # -----------------------------------------------------------------------
    # Step 8: Validate loading
    # -----------------------------------------------------------------------
    logger.info('Validating saved artifacts...')
    loaded_model  = joblib.load(model_path)
    loaded_scaler = joblib.load(scaler_path)

    X_sample = X_test[:5]
    X_sample_scaled = loaded_scaler.transform(X_sample)
    preds = loaded_model.predict(X_sample_scaled)
    logger.info(f'Test predictions (5 samples): {preds}')
    logger.info('[OK] Artifact loading validation passed')

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    logger.info('=' * 70)
    logger.info(f'Training completed in {training_time:.2f} seconds')
    logger.info(f'Accuracy: {metrics["accuracy"]:.4f}')
    logger.info(f'v2 artifacts ready in {output_dir}/')
    logger.info('=' * 70)
    logger.info('Next step: py backend/live_glove_test.py')

    return 0


if __name__ == '__main__':
    sys.exit(main())
