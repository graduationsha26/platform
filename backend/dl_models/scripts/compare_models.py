"""
Model Comparison Script

Compares LSTM and 1D-CNN classifiers side-by-side and generates
a comparison report showing performance metrics and training time.

Usage:
    python backend/dl_models/scripts/compare_models.py
    python backend/dl_models/scripts/compare_models.py --models-dir path/to/models
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
    parser = argparse.ArgumentParser(description='Compare trained deep learning models')
    parser.add_argument(
        '--models-dir',
        type=str,
        default='backend/dl_models/models',
        help='Directory containing trained models and metadata'
    )
    return parser.parse_args()


def load_model_metadata(models_dir: str, model_name: str) -> dict:
    """
    Load metadata for a specific model.

    Args:
        models_dir: Directory containing model files
        model_name: Base name of model (e.g., "lstm_model", "cnn_1d_model")

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


def format_comparison_report(lstm_metadata: dict, cnn_metadata: dict) -> str:
    """
    Format comparison report from two model metadata dicts.

    Args:
        lstm_metadata: LSTM metadata
        cnn_metadata: 1D-CNN metadata

    Returns:
        Formatted comparison report string
    """
    # Extract metrics
    lstm_metrics = lstm_metadata['performance_metrics']
    cnn_metrics = cnn_metadata['performance_metrics']
    lstm_training_time = lstm_metadata['training_history']['training_time_seconds']
    cnn_training_time = cnn_metadata['training_history']['training_time_seconds']

    # Determine best model
    if lstm_metrics['accuracy'] > cnn_metrics['accuracy']:
        best_model = f"LSTM [{lstm_metrics['accuracy']:.1%} accuracy]"
    elif cnn_metrics['accuracy'] > lstm_metrics['accuracy']:
        best_model = f"1D-CNN [{cnn_metrics['accuracy']:.1%} accuracy]"
    else:
        best_model = f"TIE [both {lstm_metrics['accuracy']:.1%} accuracy]"

    # Build report
    report = f"""
{"="*70}
MODEL COMPARISON REPORT
{"="*70}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

LSTM Model:
  Accuracy:   {lstm_metrics['accuracy']:.1%}
  Precision:  {lstm_metrics['precision']:.1%}
  Recall:     {lstm_metrics['recall']:.1%}
  F1-Score:   {lstm_metrics['f1_score']:.1%}
  Training Time: {lstm_training_time:.1f} seconds

1D-CNN Model:
  Accuracy:   {cnn_metrics['accuracy']:.1%}
  Precision:  {cnn_metrics['precision']:.1%}
  Recall:     {cnn_metrics['recall']:.1%}
  F1-Score:   {cnn_metrics['f1_score']:.1%}
  Training Time: {cnn_training_time:.1f} seconds

Best Model: {best_model}

Recommendation:
"""

    # Add recommendation based on results
    if lstm_metrics['accuracy'] > cnn_metrics['accuracy']:
        report += "  LSTM achieves higher accuracy. Recommended for deployment.\n"
    elif cnn_metrics['accuracy'] > lstm_metrics['accuracy']:
        report += "  1D-CNN achieves higher accuracy"
        if cnn_training_time < lstm_training_time:
            report += " with faster training time. Recommended for deployment.\n"
        else:
            report += ". Consider trade-off between accuracy and training speed.\n"
    else:
        if cnn_training_time < lstm_training_time:
            report += "  Both models achieve equal accuracy. 1D-CNN trains faster - recommended for deployment.\n"
        else:
            report += "  Both models achieve equal accuracy. LSTM trains faster - recommended for deployment.\n"

    # Add interpretability note
    report += "  Note: Consider LSTM if model interpretability (attention weights) is needed.\n"
    report += "  Note: Consider 1D-CNN if faster inference is critical.\n"

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
        logger.info("Loading LSTM metadata...")
        lstm_metadata = load_model_metadata(args.models_dir, "lstm_model")
        logger.info("[OK] LSTM metadata loaded")

        logger.info("Loading 1D-CNN metadata...")
        cnn_metadata = load_model_metadata(args.models_dir, "cnn_1d_model")
        logger.info("[OK] 1D-CNN metadata loaded")

        # Generate comparison report
        logger.info("Generating comparison report...")
        report = format_comparison_report(lstm_metadata, cnn_metadata)

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
        logger.error("[ERROR]   python backend/dl_models/scripts/train_lstm.py")
        logger.error("[ERROR]   python backend/dl_models/scripts/train_cnn_1d.py")
        return 1

    except KeyError as e:
        logger.error(f"[ERROR] Missing metadata field: {e}")
        logger.error("[ERROR] Model metadata files may be corrupted or incomplete")
        return 1

    except Exception as e:
        logger.error(f"[ERROR] Comparison failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
