"""
Report Formatter Utility

Formats comparison data into various output formats:
- Markdown tables and reports
- PDF documents (via ReportLab)
- Deployment recommendations
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

logger = logging.getLogger(__name__)


class ReportFormatter:
    """
    Formats model comparison data into reports and recommendations.

    Supports:
    - Markdown table formatting
    - Deployment recommendation generation
    - PDF export via ReportLab
    """

    @staticmethod
    def format_comparison_table(comparison_data: List[Dict[str, Any]]) -> str:
        """
        Generate Markdown comparison table from comparison data.

        Args:
            comparison_data: List of model comparison records

        Returns:
            Markdown-formatted comparison table string

        Example output:
            | Model | Type | Accuracy | Precision | Recall | F1 | Inference | Ranking |
            |-------|------|----------|-----------|--------|----|-----------| --------|
            | LSTM  | DL   | 96.5%    | 96.2%     | 96.8%  |96.5%| 48.3ms ±3.1| 1      |
        """
        # Header
        table = "| Model | Type | Accuracy | Precision | Recall | F1 | Inference | Ranking |\n"
        table += "|-------|------|----------|-----------|--------|----|-----------|---------|\n"

        # Rows
        for data in comparison_data:
            model_name = data['model_display_name']
            model_type = data['model_type']
            accuracy = f"{data['accuracy']*100:.1f}%"
            precision = f"{data['precision']*100:.1f}%"
            recall = f"{data['recall']*100:.1f}%"
            f1 = f"{data['f1_score']*100:.1f}%"
            inference = f"{data['inference_time_ms']:.1f}ms ±{data['inference_time_std']:.1f}"
            ranking = data.get('ranking', 'N/A')

            table += f"| {model_name} | {model_type} | {accuracy} | {precision} | {recall} | {f1} | {inference} | {ranking} |\n"

        return table

    @staticmethod
    def generate_recommendation(comparison_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate deployment recommendation based on threshold-based decision tree.

        Decision Logic:
        1. Filter models meeting 95% accuracy threshold
        2. If no models meet threshold: Recommend retraining
        3. Find highest accuracy model
        4. If tie (within 1%): Recommend faster model (latency tiebreaker)
        5. If perfect tie: Recommend both for ensemble

        Args:
            comparison_data: List of model comparison records

        Returns:
            Dictionary containing:
                - recommended_model: str (model name or "NONE")
                - rationale: str (explanation of recommendation)
                - alternatives: List[str] (other models considered)
                - deployment_ready: bool
                - alternative_actions: Optional[List[str]] (if no models qualify)
        """
        # Filter models meeting 95% accuracy threshold
        qualified = [d for d in comparison_data if d['accuracy'] >= 0.95]

        if len(qualified) == 0:
            logger.warning("No models meet ≥95% accuracy threshold")
            return {
                'recommended_model': 'NONE',
                'rationale': 'No models meet ≥95% accuracy threshold. Investigation required.',
                'deployment_ready': False,
                'alternative_actions': [
                    'Hyperparameter tuning',
                    'Data augmentation',
                    'Feature engineering',
                    'Increase training data',
                    'Review data quality and preprocessing'
                ],
                'alternatives': []
            }

        # Find highest accuracy
        max_accuracy = max(d['accuracy'] for d in qualified)

        # Models within 1% of highest accuracy (tie threshold)
        top_accurate = [d for d in qualified if d['accuracy'] >= max_accuracy - 0.01]

        if len(top_accurate) == 1:
            # Clear winner
            best = top_accurate[0]
            alternatives = [d['model_display_name'] for d in qualified if d != best]

            return {
                'recommended_model': best['model_display_name'],
                'rationale': f"{best['model_display_name']} achieves highest accuracy "
                           f"({best['accuracy']*100:.1f}%) among qualified models.",
                'deployment_ready': True,
                'alternatives': alternatives,
                'metrics': {
                    'accuracy': best['accuracy'],
                    'inference_time_ms': best['inference_time_ms']
                }
            }

        # Tie or near-tie - use latency tiebreaker
        fastest = min(top_accurate, key=lambda d: d['inference_time_ms'])

        # Check if latency is also tied (within 5ms)
        latency_range = max(d['inference_time_ms'] for d in top_accurate) - min(d['inference_time_ms'] for d in top_accurate)

        if latency_range < 5:
            # Perfect tie - recommend ensemble
            tied_models = [d['model_display_name'] for d in top_accurate]
            return {
                'recommended_model': ' + '.join(tied_models[:2]),  # Recommend top 2 for ensemble
                'rationale': f"Multiple models achieve similar accuracy (~{max_accuracy*100:.1f}%) "
                           f"and inference time. Recommend ensemble deployment combining "
                           f"{' and '.join(tied_models[:2])}.",
                'deployment_ready': True,
                'alternatives': tied_models[2:] if len(tied_models) > 2 else [],
                'ensemble': True
            }

        # Latency tiebreaker
        alternatives = [d['model_display_name'] for d in top_accurate if d != fastest]

        return {
            'recommended_model': fastest['model_display_name'],
            'rationale': f"Multiple models achieve similar accuracy (~{max_accuracy*100:.1f}%). "
                       f"{fastest['model_display_name']} recommended for fastest inference time "
                       f"({fastest['inference_time_ms']:.1f}ms vs {max([d['inference_time_ms'] for d in top_accurate]):.1f}ms).",
            'deployment_ready': True,
            'alternatives': alternatives,
            'metrics': {
                'accuracy': fastest['accuracy'],
                'inference_time_ms': fastest['inference_time_ms']
            }
        }

    @staticmethod
    def export_to_pdf(markdown_report_path: str, pdf_output_path: str,
                     chart_paths: Dict[str, str]) -> None:
        """
        Convert Markdown report to PDF using ReportLab.

        Args:
            markdown_report_path: Path to Markdown report file
            pdf_output_path: Path to save PDF output
            chart_paths: Dictionary mapping chart names to file paths

        Raises:
            Exception: If PDF generation fails
        """
        try:
            # Read Markdown report
            with open(markdown_report_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            # Create PDF document
            doc = SimpleDocTemplate(pdf_output_path, pagesize=letter,
                                  rightMargin=0.75*inch, leftMargin=0.75*inch,
                                  topMargin=0.75*inch, bottomMargin=0.75*inch)

            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=12,
                spaceBefore=12
            )
            body_style = styles['BodyText']
            body_style.fontSize = 10

            # Build story (PDF content)
            story = []

            # Title
            story.append(Paragraph("Model Comparison Report", title_style))
            story.append(Paragraph("TremoAI Tremor Detection Platform", heading_style))
            story.append(Spacer(1, 0.3*inch))

            # Generation date
            gen_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            story.append(Paragraph(f"<b>Generated:</b> {gen_date}", body_style))
            story.append(Spacer(1, 0.2*inch))

            # Extract sections from Markdown (simple parsing)
            lines = markdown_content.split('\n')
            current_section = []

            for line in lines:
                line = line.strip()

                if line.startswith('# ') and not line.startswith('## '):
                    # Main heading (already have title)
                    continue
                elif line.startswith('## '):
                    # Section heading
                    if current_section:
                        story.append(Paragraph('<br/>'.join(current_section), body_style))
                        story.append(Spacer(1, 0.2*inch))
                        current_section = []

                    section_title = line.replace('##', '').strip()
                    story.append(Paragraph(section_title, heading_style))

                elif line.startswith('|') and '|' in line[1:]:
                    # Table row - skip for now (ReportLab table handling is complex)
                    continue

                elif line.startswith('**') and line.endswith('**:'):
                    # Bold label
                    current_section.append(f"<b>{line.replace('**', '')}</b>")

                elif line and not line.startswith('-') and not line.startswith('*'):
                    # Regular paragraph text
                    current_section.append(line)

            # Add remaining section
            if current_section:
                story.append(Paragraph('<br/>'.join(current_section), body_style))

            # Embed charts
            story.append(PageBreak())
            story.append(Paragraph("Visualization Charts", heading_style))
            story.append(Spacer(1, 0.2*inch))

            for chart_name, chart_path in chart_paths.items():
                if os.path.exists(chart_path):
                    story.append(Paragraph(f"<b>{chart_name.replace('_', ' ').title()}</b>", body_style))
                    story.append(Spacer(1, 0.1*inch))

                    # Add image (resize to fit page)
                    img = Image(chart_path, width=6*inch, height=4*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.3*inch))

            # Build PDF
            doc.build(story)

            logger.info(f"✓ PDF report exported: {pdf_output_path}")

        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            raise
