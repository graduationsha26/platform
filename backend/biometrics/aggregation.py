"""
Aggregation utility functions for biometric data.
"""
from django.db.models import Count, Sum, Avg, Min, Max
from django.db.models.functions import Cast
from django.db.models import FloatField
from .models import BiometricSession


def compute_session_count(queryset):
    """
    Count total number of sessions in queryset.

    Args:
        queryset: BiometricSession queryset

    Returns:
        int: Number of sessions
    """
    return queryset.count()


def compute_total_duration(queryset):
    """
    Sum total duration of all sessions in queryset.

    Args:
        queryset: BiometricSession queryset

    Returns:
        float: Total duration in seconds
    """
    result = queryset.aggregate(
        total=Sum('session_duration')
    )
    total_duration = result.get('total')
    if total_duration:
        return total_duration.total_seconds()
    return 0.0


def compute_average_tremor_intensity(queryset):
    """
    Compute average tremor intensity across all sessions.

    Extracts tremor_intensity arrays from sensor_data JSON,
    computes mean of all values.

    Args:
        queryset: BiometricSession queryset

    Returns:
        float: Average tremor intensity (0-1 scale)
    """
    sessions = queryset.values_list('sensor_data', flat=True)
    all_intensities = []

    for sensor_data in sessions:
        tremor_data = sensor_data.get('tremor_intensity', [])
        if isinstance(tremor_data, list):
            all_intensities.extend(tremor_data)

    if all_intensities:
        return sum(all_intensities) / len(all_intensities)
    return 0.0


def compute_min_max_tremor(queryset):
    """
    Compute minimum and maximum tremor intensity values.

    Args:
        queryset: BiometricSession queryset

    Returns:
        dict: {'min': float, 'max': float}
    """
    sessions = queryset.values_list('sensor_data', flat=True)
    all_intensities = []

    for sensor_data in sessions:
        tremor_data = sensor_data.get('tremor_intensity', [])
        if isinstance(tremor_data, list):
            all_intensities.extend(tremor_data)

    if all_intensities:
        return {
            'min': min(all_intensities),
            'max': max(all_intensities)
        }
    return {'min': 0.0, 'max': 0.0}


def aggregate_biometric_data(patient_id, start_date=None, end_date=None):
    """
    Compute all aggregation metrics for a patient within date range.

    Args:
        patient_id: Patient ID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        dict: Aggregation results with all metrics
    """
    queryset = BiometricSession.objects.filter(patient_id=patient_id)

    if start_date:
        queryset = queryset.filter(session_start__gte=start_date)
    if end_date:
        queryset = queryset.filter(session_start__lte=end_date)

    session_count = compute_session_count(queryset)
    total_duration = compute_total_duration(queryset)
    avg_tremor = compute_average_tremor_intensity(queryset)
    min_max_tremor = compute_min_max_tremor(queryset)

    return {
        'patient_id': patient_id,
        'start_date': start_date,
        'end_date': end_date,
        'session_count': session_count,
        'total_duration': total_duration,
        'average_tremor': avg_tremor,
        'min_tremor': min_max_tremor['min'],
        'max_tremor': min_max_tremor['max']
    }
