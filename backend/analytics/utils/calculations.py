"""
Analytics Calculation Utilities

Feature 003: Analytics and Reporting
Core statistical calculations for tremor analysis.
"""

import numpy as np
from typing import List, Dict, Optional
from biometrics.models import BiometricSession


def calculate_average_amplitude(sessions: List[BiometricSession]) -> float:
    """
    Calculate average tremor amplitude across multiple sessions.

    Flattens all tremor_intensity arrays from all sessions and computes the mean.
    Tremor intensity values are normalized floats in range [0.0, 1.0].

    Args:
        sessions: List of BiometricSession objects

    Returns:
        float: Average amplitude (0.0-1.0), rounded to 2 decimal places

    Raises:
        ValueError: If no sessions provided or no tremor data available
    """
    if not sessions:
        raise ValueError("Cannot calculate average amplitude: no sessions provided")

    all_intensities = []
    for session in sessions:
        if session.sensor_data and 'tremor_intensity' in session.sensor_data:
            intensities = session.sensor_data['tremor_intensity']
            if isinstance(intensities, list) and intensities:
                all_intensities.extend(intensities)

    if not all_intensities:
        raise ValueError("Cannot calculate average amplitude: no tremor data in sessions")

    avg_amplitude = float(np.mean(all_intensities))
    return round(avg_amplitude, 2)


def calculate_dominant_frequency(sessions: List[BiometricSession]) -> float:
    """
    Calculate dominant tremor frequency across multiple sessions.

    Averages the frequency values from all sessions.

    Args:
        sessions: List of BiometricSession objects

    Returns:
        float: Dominant frequency in Hz, rounded to 1 decimal place

    Raises:
        ValueError: If no sessions provided or no frequency data available
    """
    if not sessions:
        raise ValueError("Cannot calculate dominant frequency: no sessions provided")

    frequencies = []
    for session in sessions:
        if session.sensor_data and 'frequency' in session.sensor_data:
            freq = session.sensor_data['frequency']
            if freq is not None:
                frequencies.append(float(freq))

    if not frequencies:
        raise ValueError("Cannot calculate dominant frequency: no frequency data in sessions")

    dominant_freq = float(np.mean(frequencies))
    return round(dominant_freq, 1)


def calculate_baseline(patient_id: int) -> Dict[str, any]:
    """
    Calculate baseline tremor amplitude from first 3 sessions (or all if < 3).

    Per Feature 003 spec: Baseline uses the earliest sessions chronologically
    to represent the patient's untreated/initial tremor state.

    Args:
        patient_id: Patient ID to calculate baseline for

    Returns:
        dict: Baseline information containing:
            - baseline_amplitude (float): Average amplitude from baseline sessions
            - baseline_sessions (List[int]): Session IDs used for baseline
            - baseline_period_start (datetime): Earliest baseline session start
            - baseline_period_end (datetime): Latest baseline session end

    Returns None if insufficient data (< 1 session).
    """
    baseline_sessions = BiometricSession.objects.filter(
        patient_id=patient_id
    ).order_by('session_start')[:3]

    if not baseline_sessions:
        return None

    try:
        baseline_amplitude = calculate_average_amplitude(list(baseline_sessions))
    except ValueError:
        return None

    # Get time boundaries
    first_session = baseline_sessions[0]
    last_session = baseline_sessions[len(baseline_sessions) - 1]

    return {
        'baseline_amplitude': baseline_amplitude,
        'baseline_sessions': [s.id for s in baseline_sessions],
        'baseline_period_start': first_session.session_start,
        'baseline_period_end': last_session.session_start + last_session.session_duration,
    }


def calculate_tremor_reduction_percentage(
    current_amplitude: float,
    baseline_amplitude: float
) -> Optional[float]:
    """
    Calculate tremor reduction percentage vs baseline.

    Formula: ((baseline - current) / baseline) * 100

    Positive value = improvement (tremor decreased)
    Negative value = worsening (tremor increased)
    Zero = no change

    Args:
        current_amplitude: Current average amplitude (0.0-1.0)
        baseline_amplitude: Baseline average amplitude (0.0-1.0)

    Returns:
        float: Tremor reduction percentage, rounded to 1 decimal place
        None if baseline is 0 or None (cannot calculate)
    """
    if baseline_amplitude is None or baseline_amplitude == 0:
        return None

    reduction_pct = ((baseline_amplitude - current_amplitude) / baseline_amplitude) * 100
    return round(reduction_pct, 1)


def aggregate_ml_severity_summary(sessions: List[BiometricSession]) -> Optional[Dict[str, int]]:
    """
    Aggregate ML severity predictions across multiple sessions.

    Counts occurrences of each severity level (mild, moderate, severe).

    Args:
        sessions: List of BiometricSession objects

    Returns:
        dict: Severity distribution with keys 'mild', 'moderate', 'severe' (int counts)
        None if no sessions have ML predictions
    """
    if not sessions:
        return None

    severity_counts = {
        'mild': 0,
        'moderate': 0,
        'severe': 0
    }

    has_predictions = False
    for session in sessions:
        if session.ml_prediction and 'severity' in session.ml_prediction:
            severity = session.ml_prediction['severity'].lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
                has_predictions = True

    return severity_counts if has_predictions else None
