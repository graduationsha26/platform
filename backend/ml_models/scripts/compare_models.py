"""
Model Comparison Script

Compares Random Forest and SVM classifiers side-by-side and generates
a comparison report showing performance metrics and training time.

Usage:
    python backend/ml_models/scripts/compare_models.py
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Compare trained ML models')
    parser.add_argument(
        '--models-dir',
        type=str,
        default='backend/ml_models/models',
        help='Directory containing trained models and metadata'
    )
    return parser.parse_args()


def load_model_metadata(models_dir: str, model_name: str) -> dict:
    """
    Load metadata for a specific model.

    Args:
        models_dir: Directory containing model files
        model_name: Base name of model (e.g., "random_forest", "svm_rbf")

    Returns:
        Metadata dictionary

    Raises:
        FileNotFoundError: If metadata file doesn't exist
    """
    metadata_path = os.path.join(models_dir, f"{model_name}.json")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    return metadata


def format_comparison_report(rf_metadata: dict, svm_metadata: dict) -> str:
    """
    Format comparison report from two model metadata dicts.

    Args:
        rf_metadata: Random Forest metadata
        svm_metadata: SVM metadata

    Returns:
        Formatted comparison report string
    """
    # Extract metrics
    rf_metrics = rf_metadata['performance_metrics']
    svm_metrics = svm_metadata['performance_metrics']
    rf_training_time = rf_metadata['training_info']['training_time_seconds']
    svm_training_time = svm_metadata['training_info']['training_time_seconds']

    # Determine best model
    if rf_metrics['accuracy'] > svm_metrics['accuracy']:
        best_model = f"Random Forest [{rf_metrics['accuracy']:.1%} accuracy]"
    elif svm_metrics['accuracy'] > rf_metrics['accuracy']:
        best_model = f"SVM (RBF kernel) [{svm_metrics['accuracy']:.1%} accuracy]"
    else:
        best_model = f"TIE [both {rf_metrics['accuracy']:.1%} accuracy]"

    # Build report
    report = f"""
{"="*70}
MODEL COMPARISON REPORT
{"="*70}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Random Forest Classifier:
  Accuracy:   {rf_metrics['accuracy']:.1%}
  Precision:  {rf_metrics['precision']:.1%}
  Recall:     {rf_metrics['recall']:.1%}
  F1-Score:   {rf_metrics['f1_score']:.1%}
  Training Time: {rf_training_time:.1f} seconds

SVM (RBF kernel):
  Accuracy:   {svm_metrics['accuracy']:.1%}
  Precision:  {svm_metrics['precision']:.1%}
  Recall:     {svm_metrics['recall']:.1%}
  F1-Score:   {svm_metrics['f1_score']:.1%}
  Training Time: {svm_training_time:.1f} seconds

Best Model: {best_model}

Recommendation:
"""

    # Add recommendation based on results
    if rf_metrics['accuracy'] > svm_metrics['accuracy']:
        report += "  Random Forest achieves higher accuracy. Recommended for deployment.\n"
    elif svm_metrics['accuracy'] > rf_metrics['accuracy']:
        report += "  SVM achieves higher accuracy with "
        if svm_training_time < rf_training_time:
            report += "faster training time. Recommended for deployment.\n"
        else:
            report += "longer training time. Consider trade-off between accuracy and training speed.\n"
    else:
        if svm_training_time < rf_training_time:
            report += "  Both models achieve equal accuracy. SVM trains faster - recommended for deployment.\n"
        else:
            report += "  Both models achieve equal accuracy. Random Forest trains faster - recommended for deployment.\n"

    # Add interpretability note
    report += "  Note: Consider Random Forest if model interpretability (feature importance) is needed.\n"

    report += "="*70 + "\n"

    return report


def main():
    """Main comparison function."""
    args = parse_arguments()

    logger.info("="*70)
    logger.info("Model Comparison Report Generator")
    logger.info("="*70)

    try:
        # Load metadata for both models
        logger.info("Loading Random Forest metadata...")
        rf_metadata = load_model_metadata(args.models_dir, "random_forest")
        logger.info("[OK] Random Forest metadata loaded")

        logger.info("Loading SVM metadata...")
        svm_metadata = load_model_metadata(args.models_dir, "svm_rbf")
        logger.info("[OK] SVM metadata loaded")

        # Generate comparison report
        logger.info("Generating comparison report...")
        report = format_comparison_report(rf_metadata, svm_metadata)

        # Display report
        print(report)

        # Save report to file
        report_path = os.path.join(args.models_dir, "comparison_report.txt")
        with open(report_path, 'w') as f:
            f.write(report)

        logger.info(f"Report saved to {report_path}")
        logger.info("="*70)

        return 0

    except FileNotFoundError as e:
        logger.error(f"[ERROR] {e}")
        logger.error("[ERROR] Please train both models first:")
        logger.error("[ERROR]   python backend/ml_models/scripts/train_random_forest.py")
        logger.error("[ERROR]   python backend/ml_models/scripts/train_svm.py")
        return 1

    except KeyError as e:
        logger.error(f"[ERROR] Missing metadata field: {e}")
        logger.error("[ERROR] Model metadata files may be corrupted or incomplete")
        return 1

    except Exception as e:
        logger.error(f"[ERROR] Comparison failed: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
