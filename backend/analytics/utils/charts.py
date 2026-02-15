"""
Chart Generation Utilities

Feature 003: Analytics and Reporting
Matplotlib chart generation for PDF reports with clinical styling.
"""

import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Tuple


# Clinical theme configuration
CLINICAL_THEME = {
    'figure_bgcolor': '#ffffff',
    'plot_bgcolor': '#f8f9fa',
    'primary_color': '#2c5aa0',  # Professional blue
    'secondary_color': '#6c757d',  # Gray
    'grid_color': '#dee2e6',
    'text_color': '#212529',
    'font_family': 'sans-serif',
    'title_fontsize': 14,
    'label_fontsize': 11,
    'tick_fontsize': 9,
    'line_width': 2.0,
    'marker_size': 6,
    'dpi': 96,  # Standard screen DPI for PDFs
}


def configure_clinical_style():
    """
    Configure matplotlib with clinical/professional styling.

    Applies blue/gray color palette with clear labels and grid lines
    suitable for medical documentation.
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'font.family': CLINICAL_THEME['font_family'],
        'font.size': CLINICAL_THEME['tick_fontsize'],
        'axes.labelsize': CLINICAL_THEME['label_fontsize'],
        'axes.titlesize': CLINICAL_THEME['title_fontsize'],
        'xtick.labelsize': CLINICAL_THEME['tick_fontsize'],
        'ytick.labelsize': CLINICAL_THEME['tick_fontsize'],
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': CLINICAL_THEME['grid_color'],
        'axes.facecolor': CLINICAL_THEME['plot_bgcolor'],
        'figure.facecolor': CLINICAL_THEME['figure_bgcolor'],
    })


def create_tremor_amplitude_chart(
    statistics: List[Dict],
    title: str = "Tremor Amplitude Over Time"
) -> io.BytesIO:
    """
    Generate line chart showing tremor amplitude trends.

    Args:
        statistics: List of TremorStatistics dicts with 'period_start' and 'avg_amplitude'
        title: Chart title

    Returns:
        BytesIO: PNG image buffer containing the chart
    """
    configure_clinical_style()

    # Extract data
    dates = [stat['period_start'] for stat in statistics]
    amplitudes = [stat['avg_amplitude'] for stat in statistics]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot line
    ax.plot(
        dates,
        amplitudes,
        color=CLINICAL_THEME['primary_color'],
        linewidth=CLINICAL_THEME['line_width'],
        marker='o',
        markersize=CLINICAL_THEME['marker_size'],
        label='Tremor Amplitude'
    )

    # Formatting
    ax.set_title(title, fontweight='bold', color=CLINICAL_THEME['text_color'])
    ax.set_xlabel('Date', fontweight='bold')
    ax.set_ylabel('Average Amplitude (0.0-1.0)', fontweight='bold')
    ax.set_ylim(0, 1.0)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha='right')

    # Add legend
    ax.legend(loc='upper right')

    # Tight layout
    plt.tight_layout()

    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=CLINICAL_THEME['dpi'], bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    return buffer


def create_tremor_reduction_chart(
    statistics: List[Dict],
    title: str = "Tremor Reduction vs Baseline"
) -> io.BytesIO:
    """
    Generate line chart showing tremor reduction percentage over time.

    Positive values = improvement, negative values = worsening.

    Args:
        statistics: List of TremorStatistics dicts with 'period_start' and 'tremor_reduction_pct'
        title: Chart title

    Returns:
        BytesIO: PNG image buffer containing the chart
    """
    configure_clinical_style()

    # Extract data (filter out None values)
    data_points = [
        (stat['period_start'], stat['tremor_reduction_pct'])
        for stat in statistics
        if stat.get('tremor_reduction_pct') is not None
    ]

    if not data_points:
        # Return empty chart with message
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'No baseline data available',
                ha='center', va='center', fontsize=12, color=CLINICAL_THEME['secondary_color'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=CLINICAL_THEME['dpi'], bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)
        return buffer

    dates = [dp[0] for dp in data_points]
    reductions = [dp[1] for dp in data_points]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot line
    ax.plot(
        dates,
        reductions,
        color=CLINICAL_THEME['primary_color'],
        linewidth=CLINICAL_THEME['line_width'],
        marker='o',
        markersize=CLINICAL_THEME['marker_size'],
        label='Tremor Reduction %'
    )

    # Add zero reference line
    ax.axhline(y=0, color=CLINICAL_THEME['secondary_color'], linestyle='--', linewidth=1, alpha=0.5)

    # Formatting
    ax.set_title(title, fontweight='bold', color=CLINICAL_THEME['text_color'])
    ax.set_xlabel('Date', fontweight='bold')
    ax.set_ylabel('Tremor Reduction (%)', fontweight='bold')

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha='right')

    # Add legend
    ax.legend(loc='upper right')

    # Tight layout
    plt.tight_layout()

    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=CLINICAL_THEME['dpi'], bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    return buffer


def create_frequency_chart(
    statistics: List[Dict],
    title: str = "Dominant Tremor Frequency"
) -> io.BytesIO:
    """
    Generate line chart showing dominant tremor frequency over time.

    Args:
        statistics: List of TremorStatistics dicts with 'period_start' and 'dominant_frequency'
        title: Chart title

    Returns:
        BytesIO: PNG image buffer containing the chart
    """
    configure_clinical_style()

    # Extract data
    dates = [stat['period_start'] for stat in statistics]
    frequencies = [stat['dominant_frequency'] for stat in statistics]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot line
    ax.plot(
        dates,
        frequencies,
        color=CLINICAL_THEME['secondary_color'],
        linewidth=CLINICAL_THEME['line_width'],
        marker='o',
        markersize=CLINICAL_THEME['marker_size'],
        label='Dominant Frequency'
    )

    # Formatting
    ax.set_title(title, fontweight='bold', color=CLINICAL_THEME['text_color'])
    ax.set_xlabel('Date', fontweight='bold')
    ax.set_ylabel('Frequency (Hz)', fontweight='bold')

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha='right')

    # Add legend
    ax.legend(loc='upper right')

    # Tight layout
    plt.tight_layout()

    # Save to buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=CLINICAL_THEME['dpi'], bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    return buffer
