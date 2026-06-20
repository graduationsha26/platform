"""
Metrics Extractor Utility

Extracts and processes performance metrics from model metadata JSON files.
Handles both ML (scikit-learn) and DL (TensorFlow/Keras) model metadata formats.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MetricsExtractor:
    """
    Extracts performance metrics from model metadata files.

    Parses JSON metadata to extract:
    - Classification metrics: accuracy, precision, recall, F1-score
    - Confusion matrix (2×2 for binary classification)
    - Training information: timestamp, samples, epochs, training time
    - Model configuration: hyperparameters, architecture details
    """

    @staticmethod
    def extract_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract performance metrics from metadata dictionary.

        Args:
            metadata: Model metadata loaded from JSON file

        Returns:
            Dictionary containing extracted metrics:
                - accuracy: float (0.0 to 1.0)
                - precision: float (0.0 to 1.0)
                - recall: float (0.0 to 1.0)
                - f1_score: float (0.0 to 1.0)
                - confusion_matrix: 2×2 numpy array [[TN, FP], [FN, TP]]
                - meets_threshold_95: bool (True if accuracy ≥ 0.95)
                - training_timestamp: str (ISO 8601)
                - test_samples_count: int
                - training_time_seconds: float

        Raises:
            KeyError: If required metadata fields are missing
            ValueError: If metric values are invalid
        """
        try:
            # Extract performance metrics
            perf_metrics = metadata.get('performance_metrics', {})

            accuracy = float(perf_metrics['accuracy'])
            precision = float(perf_metrics['precision'])
            recall = float(perf_metrics['recall'])
            f1_score = float(perf_metrics['f1_score'])

            # Validate metric ranges
            if not all(0.0 <= m <= 1.0 for m in [accuracy, precision, recall, f1_score]):
                raise ValueError("Metrics must be in range [0.0, 1.0]")

            # Extract confusion matrix
            cm_raw = perf_metrics['confusion_matrix']
            if isinstance(cm_raw, list):
                confusion_matrix = np.array(cm_raw)
            else:
                confusion_matrix = cm_raw

            # Ensure 2×2 matrix
            if confusion_matrix.shape != (2, 2):
                raise ValueError(f"Expected 2×2 confusion matrix, got shape {confusion_matrix.shape}")

            # Extract training information
            training_info = metadata.get('training_info', {})
            training_timestamp = training_info.get('timestamp', 'Unknown')
            test_samples_count = int(training_info.get('test_samples', 0))

            # Extract training time (handle different metadata formats)
            training_history = metadata.get('training_history', {})
            training_time_seconds = float(training_history.get('training_time_seconds', 0.0))

            # Check accuracy threshold
            meets_threshold_95 = accuracy >= 0.95

            extracted = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'confusion_matrix': confusion_matrix,
                'meets_threshold_95': meets_threshold_95,
                'training_timestamp': training_timestamp,
                'test_samples_count': test_samples_count,
                'training_time_seconds': training_time_seconds
            }

            logger.debug(f"Extracted metrics: accuracy={accuracy:.1%}, "
                        f"precision={precision:.1%}, recall={recall:.1%}, F1={f1_score:.1%}")

            return extracted

        except KeyError as e:
            logger.error(f"Missing required metadata field: {e}")
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid metric value in metadata: {e}")
            raise

    @staticmethod
    def extract_all_from_models(models_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract metrics from multiple models.

        Args:
            models_metadata: Dictionary mapping model names to their metadata
                Example: {'rf': {...}, 'svm': {...}, 'lstm': {...}, 'cnn_1d': {...}}

        Returns:
            Dictionary mapping model names to extracted metrics

        Raises:
            Exception: If extraction fails for any model
        """
        all_metrics = {}

        for model_name, metadata in models_metadata.items():
            try:
                metrics = MetricsExtractor.extract_from_metadata(metadata)
                all_metrics[model_name] = metrics
                logger.info(f"✓ Extracted metrics for {model_name.upper()}: "
                          f"accuracy={metrics['accuracy']:.1%}")
            except Exception as e:
                logger.error(f"Failed to extract metrics for {model_name}: {e}")
                raise

        return all_metrics

    @staticmethod
    def compute_derived_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute additional derived metrics from confusion matrix.

        Args:
            metrics: Dictionary containing at least 'confusion_matrix' key

        Returns:
            Dictionary with additional metrics:
                - true_positives: int
                - true_negatives: int
                - false_positives: int
                - false_negatives: int
                - sensitivity: float (same as recall)
                - specificity: float
                - positive_predictive_value: float (same as precision)
                - negative_predictive_value: float
        """
        cm = metrics['confusion_matrix']
        tn, fp = cm[0]
        fn, tp = cm[1]

        derived = {
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'sensitivity': metrics['recall'],  # Same as recall
            'specificity': float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
            'positive_predictive_value': metrics['precision'],  # Same as precision
            'negative_predictive_value': float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0
        }

        return derived

    @staticmethod
    def validate_metrics_consistency(all_metrics: Dict[str, Dict[str, Any]]) -> bool:
        """
        Validate that all models were evaluated on the same test dataset.

        Args:
            all_metrics: Dictionary mapping model names to extracted metrics

        Returns:
            True if all models have same test_samples_count, False otherwise

        Raises:
            ValueError: If test set sizes differ across models
        """
        test_sample_counts = [m['test_samples_count'] for m in all_metrics.values()]

        if len(set(test_sample_counts)) > 1:
            # Different test set sizes detected
            logger.error("Test dataset size mismatch detected:")
            for model_name, metrics in all_metrics.items():
                logger.error(f"  {model_name.upper()}: {metrics['test_samples_count']} samples")

            raise ValueError("All models must be evaluated on identical test datasets for valid comparison.")

        logger.info(f"✓ All models evaluated on same test set: {test_sample_counts[0]} samples")
        return True
