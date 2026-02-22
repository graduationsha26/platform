"""
Dashboard Service

Feature 032: Dashboard Overview Page
Computes system-wide summary statistics scoped to a doctor's patient cohort.
"""

from datetime import timedelta

from django.db.models import Avg
from django.db.models.functions import TruncDate
from django.utils import timezone

from biometrics.models import BiometricSession, TremorMetrics
from devices.models import Device
from patients.models import Patient


class DashboardService:
    """
    Computes the four dashboard metrics for a given doctor:
    - total_patients: patients assigned via DoctorPatientAssignment
    - active_devices: devices with status='online' across the doctor's patients
    - alerts_count: BiometricSessions with severe ML prediction in last 24h
    - tremor_trend: 7-day daily avg of dominant_amplitude across the doctor's patients
    """

    def get_dashboard_stats(self, doctor):
        """
        Return dashboard statistics dict for the given doctor user.

        Args:
            doctor: CustomUser instance with role='doctor'

        Returns:
            dict with keys: total_patients, active_devices, alerts_count, tremor_trend
        """
        # All patients assigned to this doctor via DoctorPatientAssignment
        patients = Patient.objects.filter(doctor_assignments__doctor=doctor)

        total_patients = patients.count()

        active_devices = Device.objects.filter(
            patient__in=patients,
            status='online',
        ).count()

        cutoff = timezone.now() - timedelta(hours=24)
        alerts_count = BiometricSession.objects.filter(
            patient__in=patients,
            session_start__gte=cutoff,
            ml_prediction__severity='severe',
        ).count()

        tremor_trend = self._build_tremor_trend(patients)

        return {
            'total_patients': total_patients,
            'active_devices': active_devices,
            'alerts_count': alerts_count,
            'tremor_trend': tremor_trend,
        }

    def _build_tremor_trend(self, patients):
        """
        Build a 7-entry list of daily avg tremor amplitude for the past 7 days.
        Days without data have avg_amplitude=None.

        Returns:
            list of dicts: [{'date': 'YYYY-MM-DD', 'avg_amplitude': float|None}, ...]
            Always exactly 7 entries, ordered from D-6 to today.
        """
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=6)

        trend_qs = (
            TremorMetrics.objects
            .filter(patient__in=patients, window_start__date__gte=seven_days_ago)
            .annotate(day=TruncDate('window_start'))
            .values('day')
            .annotate(avg_amplitude=Avg('dominant_amplitude'))
            .order_by('day')
        )

        trend_map = {item['day']: item['avg_amplitude'] for item in trend_qs}

        trend = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            trend.append({
                'date': day.isoformat(),
                'avg_amplitude': trend_map.get(day),
            })

        return trend
