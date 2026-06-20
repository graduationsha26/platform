"""
PDF Report Generator Service

Feature 003: Analytics and Reporting
Business logic for generating PDF reports with tremor statistics and charts.
"""

import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from django.conf import settings

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfgen import canvas

from patients.models import Patient
from analytics.services.statistics import StatisticsService
from analytics.utils.charts import (
    create_tremor_amplitude_chart,
    create_tremor_reduction_chart,
    create_frequency_chart
)


class PDFReportGenerator:
    """
    Service for generating comprehensive PDF reports with tremor statistics.
    """

    MAX_FILE_SIZE_MB = 5.0  # Per spec SC-004

    def __init__(self, patient_id: int, start_date: Optional[datetime.date] = None,
                 end_date: Optional[datetime.date] = None,
                 include_charts: bool = True, include_ml_summary: bool = True):
        """
        Initialize PDF report generator.

        Args:
            patient_id: Patient ID to generate report for
            start_date: Report start date (inclusive)
            end_date: Report end date (inclusive)
            include_charts: Whether to include trend charts
            include_ml_summary: Whether to include ML prediction summary
        """
        self.patient_id = patient_id
        self.start_date = start_date
        self.end_date = end_date
        self.include_charts = include_charts
        self.include_ml_summary = include_ml_summary

        # Initialize statistics service
        self.stats_service = StatisticsService(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get patient information
        try:
            self.patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise ValueError(f"Patient with ID {patient_id} not found")

        # Styles
        self.styles = getSampleStyleSheet()
        self._configure_styles()

    def _configure_styles(self):
        """Configure custom paragraph styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c5aa0'),
            spaceBefore=15,
            spaceAfter=10
        ))

        # Patient info style
        self.styles.add(ParagraphStyle(
            name='PatientInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_LEFT
        ))

    def _create_patient_header(self) -> List:
        """
        T026: Create patient information header section.

        Returns:
            List of ReportLab flowables for patient header
        """
        elements = []

        # Report title
        title = Paragraph("Tremor Analysis Report", self.styles['ReportTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))

        # Patient information table
        patient_data = [
            ['Patient ID:', str(self.patient.id)],
            ['Patient Name:', self.patient.full_name],
            ['Date of Birth:', str(self.patient.date_of_birth) if self.patient.date_of_birth else 'N/A'],
            ['Report Period:', f"{self.start_date or 'All'} to {self.end_date or 'Present'}"],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ]

        patient_table = Table(patient_data, colWidths=[2 * inch, 4 * inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#212529')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        elements.append(patient_table)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _create_statistics_summary(self, statistics: List[Dict], baseline: Optional[Dict]) -> List:
        """
        T027: Create statistics summary table section.

        Args:
            statistics: List of TremorStatistics dicts
            baseline: Baseline dict or None

        Returns:
            List of ReportLab flowables for statistics summary
        """
        elements = []

        # Section heading
        heading = Paragraph("Statistics Summary", self.styles['SectionHeading'])
        elements.append(heading)

        if not statistics:
            no_data = Paragraph("No biometric sessions found for the specified period.", self.styles['Normal'])
            elements.append(no_data)
            return elements

        # Calculate summary metrics
        total_sessions = len(statistics)
        avg_amplitude = sum(s['avg_amplitude'] for s in statistics) / total_sessions
        avg_frequency = sum(s['dominant_frequency'] for s in statistics) / total_sessions

        # Build summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Sessions', str(total_sessions)],
            ['Average Tremor Amplitude', f"{avg_amplitude:.2f}"],
            ['Average Frequency', f"{avg_frequency:.1f} Hz"],
        ]

        if baseline:
            summary_data.append(['Baseline Amplitude', f"{baseline['baseline_amplitude']:.2f}"])
            baseline_sessions_count = len(baseline['baseline_sessions'])
            summary_data.append(['Baseline Sessions', str(baseline_sessions_count)])

        # Calculate average reduction if available
        reductions = [s['tremor_reduction_pct'] for s in statistics if s.get('tremor_reduction_pct') is not None]
        if reductions:
            avg_reduction = sum(reductions) / len(reductions)
            summary_data.append(['Average Tremor Reduction', f"{avg_reduction:.1f}%"])

        summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _embed_charts(self, statistics: List[Dict]) -> List:
        """
        T028: Create and embed matplotlib charts into PDF.

        Args:
            statistics: List of TremorStatistics dicts

        Returns:
            List of ReportLab flowables for charts
        """
        elements = []

        if not self.include_charts or not statistics:
            return elements

        # Section heading
        heading = Paragraph("Tremor Trends", self.styles['SectionHeading'])
        elements.append(heading)

        # Chart 1: Tremor Amplitude
        try:
            amp_chart_buffer = create_tremor_amplitude_chart(statistics)
            amp_chart = Image(amp_chart_buffer, width=6 * inch, height=3 * inch)
            elements.append(amp_chart)
            elements.append(Spacer(1, 0.2 * inch))
        except Exception as e:
            error_msg = Paragraph(f"Error generating amplitude chart: {str(e)}", self.styles['Normal'])
            elements.append(error_msg)

        # Chart 2: Tremor Reduction
        try:
            reduction_chart_buffer = create_tremor_reduction_chart(statistics)
            reduction_chart = Image(reduction_chart_buffer, width=6 * inch, height=3 * inch)
            elements.append(reduction_chart)
            elements.append(Spacer(1, 0.2 * inch))
        except Exception as e:
            error_msg = Paragraph(f"Error generating reduction chart: {str(e)}", self.styles['Normal'])
            elements.append(error_msg)

        return elements

    def _create_ml_summary(self, statistics: List[Dict]) -> List:
        """
        T029: Create ML severity distribution section.

        Args:
            statistics: List of TremorStatistics dicts

        Returns:
            List of ReportLab flowables for ML summary
        """
        elements = []

        if not self.include_ml_summary or not statistics:
            return elements

        # Aggregate ML predictions
        total_mild = 0
        total_moderate = 0
        total_severe = 0
        sessions_with_predictions = 0

        for stat in statistics:
            ml_summary = stat.get('ml_severity_summary')
            if ml_summary:
                total_mild += ml_summary.get('mild', 0)
                total_moderate += ml_summary.get('moderate', 0)
                total_severe += ml_summary.get('severe', 0)
                sessions_with_predictions += 1

        if sessions_with_predictions == 0:
            return elements

        # Section heading
        heading = Paragraph("ML Prediction Summary", self.styles['SectionHeading'])
        elements.append(heading)

        # ML summary table
        ml_data = [
            ['Severity Level', 'Session Count', 'Percentage'],
            ['Mild', str(total_mild), f"{(total_mild / (total_mild + total_moderate + total_severe) * 100):.1f}%"],
            ['Moderate', str(total_moderate), f"{(total_moderate / (total_mild + total_moderate + total_severe) * 100):.1f}%"],
            ['Severe', str(total_severe), f"{(total_severe / (total_mild + total_moderate + total_severe) * 100):.1f}%"],
        ]

        ml_table = Table(ml_data, colWidths=[2 * inch, 2 * inch, 2 * inch])
        ml_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(ml_table)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def generate_pdf(self) -> str:
        """
        T025: Generate complete PDF report.

        Returns:
            str: Absolute path to generated PDF file

        Raises:
            ValueError: If no data available or PDF exceeds size limit (T034)
        """
        # Get statistics data
        stats_data = self.stats_service.get_statistics(group_by='day')
        statistics = stats_data['results']
        baseline = stats_data['baseline']

        if not statistics:
            raise ValueError("No biometric sessions found for patient in specified date range")

        # Create temporary PDF file
        media_reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(media_reports_dir, exist_ok=True)

        filename = f"report_patient{self.patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(media_reports_dir, filename)

        # Build PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []

        # Add sections
        story.extend(self._create_patient_header())
        story.extend(self._create_statistics_summary(statistics, baseline))
        story.extend(self._embed_charts(statistics))
        story.extend(self._create_ml_summary(statistics))

        # Build PDF
        doc.build(story)

        # T034: Validate file size
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            os.remove(pdf_path)  # Clean up oversized file
            raise ValueError(
                f"Generated PDF exceeds maximum size of {self.MAX_FILE_SIZE_MB}MB. "
                f"Try reducing date range. (Generated: {file_size_mb:.2f}MB)"
            )

        return pdf_path
