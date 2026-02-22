"""
Model Evaluation Utilities

Functions for computing performance metrics on trained models.
"""

from typing import Dict, Tuple
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix as sk_confusion_matrix
)


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
    """
    Evaluate a trained model on test data and compute all metrics.

    Args:
        model: Trained scikit-learn model with predict() method
        X_test: Test features, shape (n_samples, n_features)
        y_test: Test labels, shape (n_samples,)

    Returns:
        Dict containing:
        - accuracy: Overall accuracy (float)
        - precision: Precision score (float, macro average)
        - recall: Recall score (float, macro average)
        - f1_score: F1 score (float, macro average)
        - confusion_matrix: 2×2 confusion matrix (list of lists)
        - meets_threshold: Boolean indicating if accuracy ≥ 0.95

    Raises:
        ValueError: If predictions fail or shapes don't match
    """
    # Make predictions
    y_pred = model.predict(X_test)

    # Validate shapes
    if y_pred.shape != y_test.shape:
        raise ValueError(f"Prediction shape {y_pred.shape} doesn't match test labels shape {y_test.shape}")

    # Compute accuracy
    accuracy = accuracy_score(y_test, y_pred)

    # Compute precision, recall, F1-score (macro average for multi-class, but we have binary)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='macro', zero_division=0
    )

    # Compute confusion matrix
    cm = sk_confusion_matrix(y_test, y_pred)

    # Check if accuracy meets threshold (≥95%)
    meets_threshold = accuracy >= 0.95

    # Assemble results
    results = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": cm.tolist(),  # Convert numpy array to list for JSON serialization
        "meets_threshold": bool(meets_threshold)
    }

    return results


def format_metrics_string(metrics: Dict) -> str:
    """
    Format metrics dictionary into a readable string.

    Args:
        metrics: Dict from evaluate_model()

    Returns:
        Formatted string with all metrics
    """
    cm = metrics['confusion_matrix']
    meets_threshold_str = "[OK] Meets >=95% threshold" if metrics['meets_threshold'] else "[WARNING] Below 95% threshold"

    output = f"""
Performance Metrics:
  Accuracy:   {metrics['accuracy']:.3f} ({metrics['accuracy']*100:.1f}%)
  Precision:  {metrics['precision']:.3f}
  Recall:     {metrics['recall']:.3f}
  F1-Score:   {metrics['f1_score']:.3f}
  Threshold:  {meets_threshold_str}

Confusion Matrix:
  [[TN={cm[0][0]}, FP={cm[0][1]}],
   [FN={cm[1][0]}, TP={cm[1][1]}]]
"""
    return output
