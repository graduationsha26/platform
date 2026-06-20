"""
Deployment Decision Documentation Script

Documents deployment decisions with rationale, selected models, and trade-off analysis.
Supports decision history tracking and PDF export.

Usage:
    # Interactive mode
    python backend/model_comparison/scripts/document_decision.py --interactive

    # CLI mode
    python backend/model_comparison/scripts/document_decision.py \
      --model lstm \
      --supervisor "Dr. Reem" \
      --rationale "Highest accuracy with acceptable latency" \
      --alternatives "cnn_1d:0.5% lower accuracy,rf:1.1% lower accuracy"
"""

import os
import sys
import json
import uuid
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from model_comparison.utils.report_formatter import ReportFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Document deployment decision')
    parser.add_argument('--model', type=str, help='Selected model name (e.g., lstm, rf)')
    parser.add_argument('--supervisor', type=str, help='Supervisor name (e.g., Dr. Reem)')
    parser.add_argument('--rationale', type=str, help='Decision rationale')
    parser.add_argument('--alternatives', type=str,
                       help='Rejected models (format: model1:reason1,model2:reason2)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--comparison-report', type=str,
                       default='backend/model_comparison/reports/comparison_data.json',
                       help='Path to comparison report JSON')
    parser.add_argument('--output-dir', type=str,
                       default='backend/model_comparison/decisions',
                       help='Directory to save decision documents')
    return parser.parse_args()


def load_comparison_report(report_path):
    """Load comparison report for context."""
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
        logger.info(f"✓ Loaded comparison report: {len(report['models_compared'])} models")
        return report
    except FileNotFoundError:
        logger.error(f"Comparison report not found: {report_path}")
        logger.error("Run compare_all_models.py first to generate comparison report.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load comparison report: {e}")
        sys.exit(1)


def generate_decision_id():
    """Generate unique decision ID."""
    return str(uuid.uuid4())


def interactive_decision():
    """Interactive mode for decision documentation."""
    print("\n" + "="*70)
    print("Interactive Deployment Decision Documentation")
    print("="*70 + "\n")

    model = input("Selected model (e.g., lstm, rf, svm, cnn_1d): ").strip()
    supervisor = input("Supervisor name (e.g., Dr. Reem): ").strip()

    print("\nRationale (multi-line, press Ctrl+D or Ctrl+Z when done):")
    rationale_lines = []
    try:
        while True:
            line = input()
            rationale_lines.append(line)
    except EOFError:
        pass
    rationale = '\n'.join(rationale_lines).strip()

    alternatives_input = input("\nAlternative models rejected (format: model1:reason1,model2:reason2): ").strip()

    return model, supervisor, rationale, alternatives_input


def parse_alternatives(alternatives_str):
    """Parse alternatives string into list of dicts."""
    if not alternatives_str:
        return []

    alternatives = []
    for item in alternatives_str.split(','):
        if ':' in item:
            model, reason = item.split(':', 1)
            alternatives.append({
                'model_name': model.strip(),
                'reason_rejected': reason.strip()
            })
    return alternatives


def create_decision_yaml_frontmatter(decision_id, selected_model, supervisor,
                                    accuracy_met, comparison_report):
    """Generate YAML front matter for decision document."""
    yaml = "---\n"
    yaml += f"decision_id: {decision_id}\n"
    yaml += f"timestamp: {datetime.now().isoformat()}\n"
    yaml += f"supervisor_name: {supervisor}\n"
    yaml += f"selected_models:\n"
    yaml += f"  - {selected_model}\n"
    yaml += f"approval_status: DRAFT\n"
    yaml += f"accuracy_threshold_met: {str(accuracy_met).lower()}\n"
    yaml += f"latency_consideration: tiebreaker\n"

    # Extract metrics for selected model
    for record in comparison_report['comparison_data']:
        if record['model_name'] == selected_model:
            yaml += "metrics_snapshot:\n"
            yaml += f"  accuracy: {record['accuracy']}\n"
            yaml += f"  precision: {record['precision']}\n"
            yaml += f"  recall: {record['recall']}\n"
            yaml += f"  f1_score: {record['f1_score']}\n"
            yaml += f"  inference_time_ms: {record['inference_time_ms']}\n"
            break

    yaml += "---\n\n"
    return yaml


def format_decision_markdown_body(selected_model, rationale, alternatives,
                                  comparison_report, supervisor):
    """Generate Markdown body for decision document."""
    # Find selected model display name
    display_name = selected_model.upper()
    for record in comparison_report['comparison_data']:
        if record['model_name'] == selected_model:
            display_name = record['model_display_name']
            break

    body = f"# Deployment Decision: {display_name}\n\n"

    # Decision Summary
    body += "## Decision Summary\n\n"
    body += f"Selected **{display_name}** for deployment based on comprehensive model comparison.\n\n"

    # Metrics Snapshot
    body += "## Metrics Snapshot\n\n"
    for record in comparison_report['comparison_data']:
        if record['model_name'] == selected_model:
            body += f"- **Accuracy**: {record['accuracy']*100:.1f}%\n"
            body += f"- **Precision**: {record['precision']*100:.1f}%\n"
            body += f"- **Recall**: {record['recall']*100:.1f}%\n"
            body += f"- **F1-Score**: {record['f1_score']*100:.1f}%\n"
            body += f"- **Inference Time**: {record['inference_time_ms']:.1f}ms ±{record['inference_time_std']:.1f}ms\n\n"
            break

    # Alternative Models
    if alternatives:
        body += "## Alternative Models Considered\n\n"
        for idx, alt in enumerate(alternatives, 1):
            body += f"{idx}. **{alt['model_name'].upper()}**: {alt['reason_rejected']}\n"
        body += "\n"

    # Rationale
    body += "## Rationale\n\n"
    body += f"{rationale}\n\n"

    # Approval
    body += "## Approval\n\n"
    body += f"**Supervisor**: {supervisor}\n"
    body += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
    body += f"**Status**: DRAFT (pending supervisor approval)\n\n"

    # Change History
    body += "## Change History\n\n"
    body += f"- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - CREATED - Initial decision recorded\n"

    return body


def save_decision_file(yaml_frontmatter, markdown_body, output_dir):
    """Save decision as Markdown with YAML front matter."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"decision_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)

    content = yaml_frontmatter + markdown_body

    with open(filepath, 'w') as f:
        f.write(content)

    logger.info(f"✓ Decision document saved: {filepath}")
    return filepath


def export_decision_to_pdf(markdown_path, pdf_path):
    """Export decision Markdown to PDF (simplified)."""
    try:
        # For now, just log - full PDF export would require ReportLab template
        logger.info(f"✓ Decision PDF export: {pdf_path} (placeholder)")
        # In production: Use ReportFormatter.export_to_pdf() with custom template
    except Exception as e:
        logger.warning(f"PDF export failed: {e}")


def main():
    """Main decision documentation workflow."""
    args = parse_arguments()

    logger.info("="*70)
    logger.info("Deployment Decision Documentation")
    logger.info("="*70)

    # Load comparison report for context
    logger.info("Loading comparison report...")
    comparison_report = load_comparison_report(args.comparison_report)

    # Get decision details (interactive or CLI)
    if args.interactive:
        model, supervisor, rationale, alternatives_str = interactive_decision()
    else:
        if not all([args.model, args.supervisor, args.rationale]):
            logger.error("Error: --model, --supervisor, and --rationale are required in non-interactive mode")
            logger.error("Use --interactive for interactive mode")
            sys.exit(1)

        model = args.model
        supervisor = args.supervisor
        rationale = args.rationale
        alternatives_str = args.alternatives

    # Validate selected model exists in comparison
    if model not in comparison_report['models_compared']:
        logger.error(f"Error: Model '{model}' not found in comparison report")
        logger.error(f"Available models: {', '.join(comparison_report['models_compared'])}")
        sys.exit(1)

    # Parse alternatives
    alternatives = parse_alternatives(alternatives_str)

    # Generate decision ID
    decision_id = generate_decision_id()

    # Check if selected model meets accuracy threshold
    accuracy_met = False
    for record in comparison_report['comparison_data']:
        if record['model_name'] == model:
            accuracy_met = record['meets_threshold_95']
            break

    # Generate decision document
    logger.info("Generating decision document...")

    yaml_frontmatter = create_decision_yaml_frontmatter(
        decision_id, model, supervisor, accuracy_met, comparison_report
    )

    markdown_body = format_decision_markdown_body(
        model, rationale, alternatives, comparison_report, supervisor
    )

    # Save decision file
    decision_path = save_decision_file(yaml_frontmatter, markdown_body, args.output_dir)

    # Export to PDF (simplified)
    pdf_path = decision_path.replace('.md', '.pdf')
    export_decision_to_pdf(decision_path, pdf_path)

    logger.info("")
    logger.info("="*70)
    logger.info("Decision documented successfully!")
    logger.info("="*70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
