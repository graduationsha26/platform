"""
Model Evaluation Utilities

Functions for computing performance metrics and formatting results.
"""

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix as sk_confusion_matrix
from typing import Dict, Any


def evaluate_model(model: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
    """
    Evaluate trained model and compute performance metrics.

    Args:
        model: Trained Keras model
        X_test: Test sequences (N, timesteps, features)
        y_test: Test labels (N,)

    Returns:
        Dictionary containing:
        - accuracy: Overall classification accuracy
        - precision: Precision score (macro-averaged)
        - recall: Recall score (macro-averaged)
        - f1_score: F1 score (macro-averaged)
        - confusion_matrix: 2x2 confusion matrix as list [[TN, FP], [FN, TP]]
        - meets_threshold: Boolean indicating if accuracy >= 95%
    """
    # Make predictions
    y_pred_probs = model.predict(X_test, verbose=0)
    y_pred = (y_pred_probs > 0.5).astype(int).flatten()

    # Compute metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='macro', zero_division=0
    )
    cm = sk_confusion_matrix(y_test, y_pred)

    # Check threshold
    meets_threshold = accuracy >= 0.95

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": cm.tolist(),
        "meets_threshold": bool(meets_threshold)
    }


def format_metrics_string(metrics: Dict) -> str:
    """
    Format metrics dictionary into human-readable string for logging.

    Args:
        metrics: Metrics dictionary from evaluate_model()

    Returns:
        Formatted string with all metrics
    """
    cm = metrics['confusion_matrix']

    lines = [
        f"Test Accuracy: {metrics['accuracy']:.1%}",
        f"Test Precision: {metrics['precision']:.1%}",
        f"Test Recall: {metrics['recall']:.1%}",
        f"Test F1-Score: {metrics['f1_score']:.1%}",
        "Confusion Matrix:",
        "       Predicted",
        "       0    1",
        "Actual",
        f"0     {cm[0][0]:2d}   {cm[0][1]:2d}",
        f"1     {cm[1][0]:2d}   {cm[1][1]:2d}"
    ]

    return "\n".join(lines)
