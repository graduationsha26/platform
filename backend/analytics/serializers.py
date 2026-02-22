"""
Analytics Serializers

Feature 003: Analytics and Reporting
DRF serializers for tremor statistics and report requests.
"""

from rest_framework import serializers


class BaselineSerializer(serializers.Serializer):
    """
    Serializer for baseline tremor amplitude information.

    Baseline is calculated from the first 3 sessions (or all if < 3)
    to represent the patient's initial/untreated tremor state.
    """
    baseline_amplitude = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text="Average tremor amplitude from baseline sessions (0.0-1.0)"
    )
    baseline_sessions = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Session IDs used for baseline calculation"
    )
    baseline_period_start = serializers.DateTimeField(
        help_text="Timestamp of earliest baseline session"
    )
    baseline_period_end = serializers.DateTimeField(
        help_text="Timestamp of latest baseline session end"
    )


class MLSeveritySummarySerializer(serializers.Serializer):
    """
    Serializer for ML severity prediction distribution.

    Counts number of sessions with each severity level.
    """
    mild = serializers.IntegerField(
        min_value=0,
        help_text="Number of sessions with mild severity"
    )
    moderate = serializers.IntegerField(
        min_value=0,
        help_text="Number of sessions with moderate severity"
    )
    severe = serializers.IntegerField(
        min_value=0,
        help_text="Number of sessions with severe severity"
    )


class TremorStatisticsSerializer(serializers.Serializer):
    """
    Serializer for aggregated tremor statistics.

    Represents statistics for a time period (single session or day).
    """
    period = serializers.CharField(
        help_text="Period identifier: session ID (session level) or date YYYY-MM-DD (daily)"
    )
    period_start = serializers.DateTimeField(
        help_text="Start of period (ISO 8601)"
    )
    period_end = serializers.DateTimeField(
        help_text="End of period (ISO 8601)"
    )
    session_count = serializers.IntegerField(
        min_value=1,
        help_text="Number of sessions in this period"
    )
    avg_amplitude = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text="Average tremor amplitude (normalized 0.0-1.0)"
    )
    dominant_frequency = serializers.FloatField(
        min_value=0.0,
        help_text="Dominant tremor frequency in Hz"
    )
    tremor_reduction_pct = serializers.FloatField(
        allow_null=True,
        min_value=-100.0,
        max_value=100.0,
        help_text="Tremor reduction percentage vs baseline (negative = worsened)"
    )
    ml_severity_summary = MLSeveritySummarySerializer(
        allow_null=True,
        help_text="Distribution of ML severity predictions"
    )


class StatisticsResponseSerializer(serializers.Serializer):
    """
    Paginated response serializer for statistics queries.

    Follows Django REST Framework pagination structure.
    """
    count = serializers.IntegerField(
        help_text="Total number of data points (for pagination)"
    )
    next = serializers.URLField(
        allow_null=True,
        help_text="URL to next page (null if last page)"
    )
    previous = serializers.URLField(
        allow_null=True,
        help_text="URL to previous page (null if first page)"
    )
    baseline = BaselineSerializer(
        allow_null=True,
        help_text="Baseline tremor amplitude information (null if no data)"
    )
    results = TremorStatisticsSerializer(
        many=True,
        help_text="Array of statistics data points (ordered chronologically)"
    )


class TremorTrendPointSerializer(serializers.Serializer):
    """
    Serializer for a single daily tremor trend data point.

    Feature 032: Dashboard Overview Page
    """
    date = serializers.DateField(
        help_text="Calendar date (YYYY-MM-DD)"
    )
    avg_amplitude = serializers.FloatField(
        allow_null=True,
        help_text="Mean dominant tremor amplitude for this day; null if no data"
    )


class DashboardStatsSerializer(serializers.Serializer):
    """
    Response serializer for GET /api/analytics/dashboard/

    Feature 032: Dashboard Overview Page
    Returns system-wide summary statistics scoped to the logged-in doctor.
    """
    total_patients = serializers.IntegerField(
        min_value=0,
        help_text="Total patients assigned to the logged-in doctor"
    )
    active_devices = serializers.IntegerField(
        min_value=0,
        help_text="Devices with status='online' across the doctor's patients"
    )
    alerts_count = serializers.IntegerField(
        min_value=0,
        help_text="BiometricSessions with severe ML prediction in the last 24 hours"
    )
    tremor_trend = TremorTrendPointSerializer(
        many=True,
        help_text="7-day daily average tremor amplitude (always exactly 7 entries)"
    )


class ReportRequestSerializer(serializers.Serializer):
    """
    Request serializer for PDF report generation.

    User Story 2: PDF Report Generation
    """
    patient_id = serializers.IntegerField(
        required=True,
        help_text="Patient ID to generate report for"
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Report start date (inclusive), defaults to earliest session"
    )
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Report end date (inclusive), defaults to today"
    )
    include_charts = serializers.BooleanField(
        default=True,
        help_text="Include trend charts in PDF"
    )
    include_ml_summary = serializers.BooleanField(
        default=True,
        help_text="Include ML prediction summary in PDF"
    )

    def validate(self, attrs):
        """
        Validate that end_date >= start_date if both provided.
        """
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'end_date must be greater than or equal to start_date'
            })

        return attrs
