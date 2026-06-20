"""
Chart Generator Utility

Generates visualization charts for model comparison using Matplotlib.
Includes accuracy comparison bar chart, confusion matrix heatmaps, and inference time comparison.
"""

import logging
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates visualization charts for model comparison.

    Charts:
    - Accuracy comparison bar chart (color-coded by threshold)
    - Confusion matrix heatmaps (2×2 layout for 4 models)
    - Inference time comparison bar chart (with error bars)
    """

    @staticmethod
    def generate_accuracy_chart(comparison_data: List[Dict[str, Any]],
                               output_path: str) -> None:
        """
        Generate accuracy comparison bar chart with color-coded bars.

        Color codes:
        - Green: accuracy ≥ 95% (meets threshold)
        - Yellow: 90% ≤ accuracy < 95% (near threshold)
        - Red: accuracy < 90% (below threshold)

        Args:
            comparison_data: List of model comparison records
            output_path: Path to save PNG chart (300 DPI)

        Raises:
            Exception: If chart generation fails
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            models = [d['model_display_name'] for d in comparison_data]
            accuracies = [d['accuracy'] * 100 for d in comparison_data]  # Convert to percentage

            # Color-code bars based on accuracy thresholds
            colors = []
            for acc in accuracies:
                if acc >= 95:
                    colors.append('#28a745')  # Green (Bootstrap success)
                elif acc >= 90:
                    colors.append('#ffc107')  # Yellow (Bootstrap warning)
                else:
                    colors.append('#dc3545')  # Red (Bootstrap danger)

            bars = ax.bar(models, accuracies, color=colors, alpha=0.8, edgecolor='black', linewidth=1.2)

            # Add 95% threshold reference line
            ax.axhline(y=95, color='black', linestyle='--', linewidth=1.5, label='95% Threshold')

            # Add percentage labels on top of bars
            for i, (bar, acc) in enumerate(zip(bars, accuracies)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                       f'{acc:.1f}%',
                       ha='center', va='bottom', fontsize=11, fontweight='bold')

            # Labels and title
            ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
            ax.set_title('Model Accuracy Comparison - TremoAI Tremor Detection',
                        fontsize=14, fontweight='bold', pad=20)
            ax.set_ylim([0, 105])  # Leave room for labels

            # Legend
            green_patch = mpatches.Patch(color='#28a745', label='≥95% (Meets Threshold)')
            yellow_patch = mpatches.Patch(color='#ffc107', label='90-95% (Near Threshold)')
            red_patch = mpatches.Patch(color='#dc3545', label='<90% (Below Threshold)')
            ax.legend(handles=[green_patch, yellow_patch, red_patch,
                             plt.Line2D([0], [0], color='black', linestyle='--', label='95% Threshold')],
                     loc='lower right', fontsize=10)

            # Grid for readability
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"✓ Accuracy comparison chart saved: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate accuracy chart: {e}")
            raise

    @staticmethod
    def generate_confusion_matrices(comparison_data: List[Dict[str, Any]],
                                    output_path: str) -> None:
        """
        Generate confusion matrix heatmaps in 2×2 layout for 4 models.

        Args:
            comparison_data: List of model comparison records (must have 4 models)
            output_path: Path to save PNG chart (300 DPI)

        Raises:
            ValueError: If not exactly 4 models provided
            Exception: If chart generation fails
        """
        try:
            if len(comparison_data) != 4:
                logger.warning(f"Expected 4 models for 2×2 layout, got {len(comparison_data)}. "
                             f"Adjusting layout...")

            # Create 2×2 subplot layout
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Confusion Matrices - TremoAI Tremor Detection Models',
                        fontsize=16, fontweight='bold', y=0.98)

            axes = axes.flatten()

            for idx, data in enumerate(comparison_data[:4]):  # Limit to 4 models
                ax = axes[idx]
                cm = data['confusion_matrix']

                # Create heatmap
                im = ax.imshow(cm, interpolation='nearest', cmap='Blues', alpha=0.8)
                ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

                # Labels
                classes = ['No Tremor (0)', 'Tremor (1)']
                tick_marks = np.arange(len(classes))
                ax.set_xticks(tick_marks)
                ax.set_yticks(tick_marks)
                ax.set_xticklabels(classes, rotation=45, ha='right')
                ax.set_yticklabels(classes)

                # Add text annotations with counts
                thresh = cm.max() / 2.
                for i in range(2):
                    for j in range(2):
                        text_color = "white" if cm[i, j] > thresh else "black"
                        ax.text(j, i, f'{int(cm[i, j])}',
                               ha="center", va="center", fontsize=14,
                               fontweight='bold', color=text_color)

                # Labels for axes
                ax.set_ylabel('True Label', fontsize=11, fontweight='bold')
                ax.set_xlabel('Predicted Label', fontsize=11, fontweight='bold')

                # Title with model name and accuracy
                accuracy = data['accuracy'] * 100
                ax.set_title(f"{data['model_display_name']} ({data['model_type']})\n"
                           f"Accuracy: {accuracy:.1f}%",
                           fontsize=12, fontweight='bold', pad=10)

            # Hide extra subplots if fewer than 4 models
            for idx in range(len(comparison_data), 4):
                axes[idx].axis('off')

            plt.tight_layout(rect=[0, 0, 1, 0.96])  # Leave room for suptitle
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"✓ Confusion matrix heatmaps saved: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate confusion matrices: {e}")
            raise

    @staticmethod
    def generate_inference_time_chart(comparison_data: List[Dict[str, Any]],
                                     output_path: str) -> None:
        """
        Generate inference time comparison bar chart with error bars (mean ± std dev).

        Args:
            comparison_data: List of model comparison records
            output_path: Path to save PNG chart (300 DPI)

        Raises:
            Exception: If chart generation fails
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            models = [d['model_display_name'] for d in comparison_data]
            inference_times = [d['inference_time_ms'] for d in comparison_data]
            std_devs = [d['inference_time_std'] for d in comparison_data]

            # Color-code by model type (ML vs DL)
            colors = []
            for d in comparison_data:
                if d['model_type'] == 'ML':
                    colors.append('#17a2b8')  # Blue (Bootstrap info)
                else:  # DL
                    colors.append('#6f42c1')  # Purple (Bootstrap purple)

            # Create bars with error bars
            bars = ax.bar(models, inference_times, yerr=std_devs, color=colors,
                         alpha=0.8, capsize=5, edgecolor='black', linewidth=1.2,
                         error_kw={'linewidth': 2, 'ecolor': 'black'})

            # Add time labels on top of bars
            for i, (bar, time, std) in enumerate(zip(bars, inference_times, std_devs)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height + std + 1,
                       f'{time:.1f}ms\n±{std:.1f}',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')

            # Labels and title
            ax.set_ylabel('Inference Time (milliseconds)', fontsize=12, fontweight='bold')
            ax.set_title('Model Inference Time Comparison - TremoAI Tremor Detection',
                        fontsize=14, fontweight='bold', pad=20)
            ax.set_ylim([0, max(inference_times) + max(std_devs) + 10])

            # Legend
            ml_patch = mpatches.Patch(color='#17a2b8', label='ML Models (scikit-learn)')
            dl_patch = mpatches.Patch(color='#6f42c1', label='DL Models (TensorFlow/Keras)')
            ax.legend(handles=[ml_patch, dl_patch], loc='upper left', fontsize=10)

            # Grid for readability
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"✓ Inference time comparison chart saved: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate inference time chart: {e}")
            raise

    @staticmethod
    def generate_all_charts(comparison_data: List[Dict[str, Any]],
                           charts_dir: str) -> Dict[str, str]:
        """
        Generate all comparison charts and return paths.

        Args:
            comparison_data: List of model comparison records
            charts_dir: Directory to save chart images

        Returns:
            Dictionary mapping chart names to file paths

        Raises:
            Exception: If any chart generation fails
        """
        os.makedirs(charts_dir, exist_ok=True)

        chart_paths = {
            'accuracy_comparison': os.path.join(charts_dir, 'accuracy_comparison.png'),
            'confusion_matrices': os.path.join(charts_dir, 'confusion_matrices.png'),
            'inference_time_comparison': os.path.join(charts_dir, 'inference_time_comparison.png')
        }

        try:
            ChartGenerator.generate_accuracy_chart(comparison_data, chart_paths['accuracy_comparison'])
            ChartGenerator.generate_confusion_matrices(comparison_data, chart_paths['confusion_matrices'])
            ChartGenerator.generate_inference_time_chart(comparison_data, chart_paths['inference_time_comparison'])

            logger.info("✓ All comparison charts generated successfully")
            return chart_paths

        except Exception as e:
            logger.error(f"Failed to generate all charts: {e}")
            raise
