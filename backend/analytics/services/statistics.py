"""
Analytics Statistics Service

Feature 003: Analytics and Reporting
Business logic for calculating tremor statistics aggregations.
"""

from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
from django.db.models import QuerySet
from biometrics.models import BiometricSession
from analytics.utils.calculations import (
    calculate_average_amplitude,
    calculate_dominant_frequency,
    calculate_baseline,
    calculate_tremor_reduction_percentage,
    aggregate_ml_severity_summary
)


class StatisticsService:
    """
    Service for calculating tremor statistics with various grouping levels.
    """

    def __init__(self, patient_id: int, start_date: Optional[datetime.date] = None,
                 end_date: Optional[datetime.date] = None):
        """
        Initialize statistics service for a patient.

        Args:
            patient_id: Patient ID to query statistics for
            start_date: Start date (inclusive), None = no start filter
            end_date: End date (inclusive), None = no end filter
        """
        self.patient_id = patient_id
        self.start_date = start_date
        self.end_date = end_date
        self._baseline = None  # Cached baseline

    def get_baseline(self) -> Optional[Dict]:
        """
        Get baseline tremor amplitude for the patient.

        Cached after first calculation to avoid redundant queries.

        Returns:
            dict: Baseline information (amplitude, sessions, period)
            None if insufficient data (< 1 session)
        """
        if self._baseline is None:
            self._baseline = calculate_baseline(self.patient_id)
        return self._baseline

    def _get_sessions_queryset(self) -> QuerySet:
        """
        Get filtered BiometricSession queryset for the patient and date range.

        Returns:
            QuerySet: Filtered sessions ordered by session_start
        """
        queryset = BiometricSession.objects.filter(patient_id=self.patient_id)

        if self.start_date:
            start_datetime = datetime.combine(self.start_date, time.min)
            queryset = queryset.filter(session_start__gte=start_datetime)

        if self.end_date:
            end_datetime = datetime.combine(self.end_date, time.max)
            queryset = queryset.filter(session_start__lte=end_datetime)

        return queryset.order_by('session_start')

    def get_session_level_statistics(self) -> List[Dict]:
        """
        Calculate statistics for each individual session.

        Each session becomes one data point in the results.

        Returns:
            List[dict]: List of TremorStatistics dicts, one per session
        """
        sessions = self._get_sessions_queryset()
        baseline = self.get_baseline()
        baseline_amplitude = baseline['baseline_amplitude'] if baseline else None

        results = []
        for session in sessions:
            try:
                # Calculate statistics for this single session
                avg_amplitude = calculate_average_amplitude([session])
                dominant_frequency = calculate_dominant_frequency([session])

                # Calculate tremor reduction vs baseline
                tremor_reduction_pct = None
                if baseline_amplitude is not None:
                    tremor_reduction_pct = calculate_tremor_reduction_percentage(
                        avg_amplitude, baseline_amplitude
                    )

                # ML severity (single session)
                ml_severity = aggregate_ml_severity_summary([session])

                # Build result
                results.append({
                    'period': str(session.id),  # Session ID as period identifier
                    'period_start': session.session_start,
                    'period_end': session.session_start + session.session_duration,
                    'session_count': 1,
                    'avg_amplitude': avg_amplitude,
                    'dominant_frequency': dominant_frequency,
                    'tremor_reduction_pct': tremor_reduction_pct,
                    'ml_severity_summary': ml_severity
                })

            except ValueError:
                # Skip sessions with insufficient data
                continue

        return results

    def get_daily_statistics(self) -> List[Dict]:
        """
        Calculate statistics aggregated by day.

        All sessions on the same calendar day are combined into one data point.

        Returns:
            List[dict]: List of TremorStatistics dicts, one per day with sessions
        """
        sessions = list(self._get_sessions_queryset())
        baseline = self.get_baseline()
        baseline_amplitude = baseline['baseline_amplitude'] if baseline else None

        # Group sessions by date
        sessions_by_date = {}
        for session in sessions:
            date = session.session_start.date()
            if date not in sessions_by_date:
                sessions_by_date[date] = []
            sessions_by_date[date].append(session)

        # Calculate statistics for each day
        results = []
        for date in sorted(sessions_by_date.keys()):
            day_sessions = sessions_by_date[date]

            try:
                # Calculate statistics for all sessions on this day
                avg_amplitude = calculate_average_amplitude(day_sessions)
                dominant_frequency = calculate_dominant_frequency(day_sessions)

                # Calculate tremor reduction vs baseline
                tremor_reduction_pct = None
                if baseline_amplitude is not None:
                    tremor_reduction_pct = calculate_tremor_reduction_percentage(
                        avg_amplitude, baseline_amplitude
                    )

                # ML severity (aggregated across day)
                ml_severity = aggregate_ml_severity_summary(day_sessions)

                # Build result
                results.append({
                    'period': str(date),  # Date in YYYY-MM-DD format
                    'period_start': datetime.combine(date, time.min),
                    'period_end': datetime.combine(date, time.max),
                    'session_count': len(day_sessions),
                    'avg_amplitude': avg_amplitude,
                    'dominant_frequency': dominant_frequency,
                    'tremor_reduction_pct': tremor_reduction_pct,
                    'ml_severity_summary': ml_severity
                })

            except ValueError:
                # Skip days with insufficient data
                continue

        return results

    def get_statistics(self, group_by: str = 'day') -> Dict:
        """
        Get statistics with specified grouping level.

        Args:
            group_by: Grouping level ('session' or 'day')

        Returns:
            dict: Statistics response with baseline and results

        Raises:
            ValueError: If group_by is invalid
        """
        if group_by == 'session':
            results = self.get_session_level_statistics()
        elif group_by == 'day':
            results = self.get_daily_statistics()
        else:
            raise ValueError(f"Invalid group_by value: {group_by}. Must be 'session' or 'day'")

        return {
            'baseline': self.get_baseline(),
            'results': results
        }
