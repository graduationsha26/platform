"""
ML Model Training Script for Raw Feature Pipeline

Trains Random Forest and SVM models using only 6 raw sensor features (aX, aY, aZ, gX, gY, gZ).
Models are saved to backend/ml_models/ directory.

Usage:
    python train.py --dataset Dataset.csv --output ml_models/

Models trained:
    - Random Forest (random_forest.pkl)
    - SVM (svm.pkl)
"""

import argparse
import joblib
import numpy as np
import os
import sys
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, accuracy_score

# Import feature utilities
try:
    from feature_utils import load_training_data, FEATURE_COLUMNS
except ImportError:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    from apps.ml.feature_utils import load_training_data, FEATURE_COLUMNS


def train_random_forest(X_train, y_train, X_test, y_test):
    """
    Train Random Forest classifier with 6-feature input.

    Args:
        X_train (np.ndarray): Training features (n_samples, 6)
        y_train (np.ndarray): Training labels
        X_test (np.ndarray): Test features
        y_test (np.ndarray): Test labels

    Returns:
        tuple: (model, metrics_dict)
    """
    print("\n=== Training Random Forest ===")
    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_train.shape[1]} ({', '.join(FEATURE_COLUMNS)})")

    # Initialize Random Forest
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=10,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,  # Use all CPUs
        verbose=1
    )

    # Train
    print("\nTraining Random Forest...")
    rf.fit(X_train, y_train)

    # Evaluate
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')

    print("\n--- Random Forest Results ---")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print(f"n_features_in_: {rf.n_features_in_}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Feature importance
    importance = rf.feature_importances_
    print("\nFeature Importance:")
    for feature, imp in zip(FEATURE_COLUMNS, importance):
        print(f"  {feature}: {imp:.4f}")

    metrics = {
        'model_type': 'Random Forest',
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'n_features': int(rf.n_features_in_),
        'feature_names': FEATURE_COLUMNS,
        'feature_importance': dict(zip(FEATURE_COLUMNS, [float(x) for x in importance])),
        'trained_date': datetime.utcnow().isoformat() + 'Z'
    }

    return rf, metrics


def train_svm(X_train, y_train, X_test, y_test):
    """
    Train SVM classifier with 6-feature input.

    Args:
        X_train (np.ndarray): Training features (n_samples, 6)
        y_train (np.ndarray): Training labels
        X_test (np.ndarray): Test features
        y_test (np.ndarray): Test labels

    Returns:
        tuple: (model, metrics_dict)
    """
    print("\n=== Training SVM ===")
    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_train.shape[1]} ({', '.join(FEATURE_COLUMNS)})")

    # Initialize SVM with RBF kernel
    svm = SVC(
        kernel='rbf',
        C=1.0,
        gamma='scale',
        random_state=42,
        verbose=True
    )

    # Train
    print("\nTraining SVM...")
    svm.fit(X_train, y_train)

    # Evaluate
    y_pred = svm.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')

    print("\n--- SVM Results ---")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print(f"n_features_in_: {svm.n_features_in_}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    metrics = {
        'model_type': 'SVM',
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'n_features': int(svm.n_features_in_),
        'feature_names': FEATURE_COLUMNS,
        'kernel': svm.kernel,
        'trained_date': datetime.utcnow().isoformat() + 'Z'
    }

    return svm, metrics


def save_model(model, model_name, output_dir, metrics):
    """
    Save trained model to pickle file.

    Args:
        model: Trained sklearn model
        model_name (str): Model filename (e.g., 'random_forest.pkl')
        output_dir (str): Output directory path
        metrics (dict): Model performance metrics
    """
    # Create output directory if needed
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # Save model
    model_path = os.path.join(output_dir, model_name)
    joblib.dump(model, model_path)
    print(f"\n✓ Saved model to {model_path}")

    # Save metrics
    metrics_path = model_path.replace('.pkl', '_metrics.json')
    import json
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Saved metrics to {metrics_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Train ML models (Random Forest, SVM) with 6-feature input'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='Dataset.csv',
        help='Path to training dataset (default: Dataset.csv)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ml_models',
        help='Output directory for trained models (default: ml_models)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size as fraction of dataset (default: 0.2)'
    )
    parser.add_argument(
        '--models',
        nargs='+',
        choices=['rf', 'svm', 'all'],
        default=['all'],
        help='Which models to train: rf, svm, or all (default: all)'
    )

    args = parser.parse_args()

    try:
        # Load training data
        print(f"Loading training data from {args.dataset}...")
        X, y = load_training_data(args.dataset)

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=42, stratify=y
        )

        print(f"\nDataset split:")
        print(f"  Training: {len(X_train)} samples")
        print(f"  Test: {len(X_test)} samples")
        print(f"  Features: {X_train.shape[1]}")

        # Determine which models to train
        train_rf = 'all' in args.models or 'rf' in args.models
        train_svm_model = 'all' in args.models or 'svm' in args.models

        all_metrics = []

        # Train Random Forest
        if train_rf:
            rf_model, rf_metrics = train_random_forest(X_train, y_train, X_test, y_test)
            save_model(rf_model, 'random_forest.pkl', args.output, rf_metrics)
            all_metrics.append(rf_metrics)

        # Train SVM
        if train_svm_model:
            svm_model, svm_metrics = train_svm(X_train, y_train, X_test, y_test)
            save_model(svm_model, 'svm.pkl', args.output, svm_metrics)
            all_metrics.append(svm_metrics)

        # Summary
        print("\n" + "="*60)
        print("TRAINING SUMMARY")
        print("="*60)
        for metrics in all_metrics:
            print(f"\n{metrics['model_type']}:")
            print(f"  F1 Score: {metrics['f1_score']:.4f}")
            print(f"  Accuracy: {metrics['accuracy']:.4f}")
            print(f"  Features: {metrics['n_features']}")

        # Validation check
        print("\n" + "="*60)
        print("VALIDATION CHECK")
        print("="*60)
        min_f1 = 0.85
        passed = all(m['f1_score'] >= min_f1 for m in all_metrics)
        if passed:
            print(f"✓ All models meet F1 score requirement (≥ {min_f1})")
        else:
            print(f"⚠ WARNING: Some models below F1 score requirement (≥ {min_f1})")
            for metrics in all_metrics:
                if metrics['f1_score'] < min_f1:
                    print(f"  {metrics['model_type']}: {metrics['f1_score']:.4f} < {min_f1}")

        print("\n✓ Training complete!")

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
