"""
Dashboard Service

Feature 032: Dashboard Overview Page
Computes system-wide summary statistics scoped to a doctor's patient cohort.
"""

from datetime import timedelta

from django.db.models.functions import TruncDate
from django.utils import timezone

from biometrics.models import BiometricSession
from devices.models import Device
from patients.models import Patient


class DashboardService:
    """
    Computes dashboard metrics for a given doctor:
    - total_patients: patients assigned via DoctorPatientAssignment
    - active_devices: devices with status='online' across the doctor's patients
    """

    def get_dashboard_stats(self, doctor):
        """
        Return dashboard statistics dict for the given doctor user.

        Args:
            doctor: CustomUser instance with role='doctor'

        Returns:
            dict with keys: total_patients, active_devices
        """
        # All patients assigned to this doctor via DoctorPatientAssignment
        patients = Patient.objects.filter(doctor_assignments__doctor=doctor)

        total_patients = patients.count()

        active_devices = Device.objects.filter(
            patient__in=patients,
            status='online',
        ).count()

        return {
            'total_patients': total_patients,
            'active_devices': active_devices,
        }

    def get_critical_alerts_count(self, doctor):
        """
        Count patients with at least one severe BiometricSession on all 5 consecutive
        calendar days ending today. Returns 0 if no patients qualify.

        Args:
            doctor: CustomUser instance with role='doctor'

        Returns:
            int: count of patients meeting the 5-consecutive-severe-day threshold
        """
        today = timezone.now().date()
        five_days_ago = today - timedelta(days=4)
        patients = Patient.objects.filter(doctor_assignments__doctor=doctor)

        severe_days_qs = (
            BiometricSession.objects
            .filter(
                patient__in=patients,
                session_start__date__gte=five_days_ago,
                session_start__date__lte=today,
                ml_prediction__severity='severe',
            )
            .annotate(day=TruncDate('session_start'))
            .values('patient_id', 'day')
            .distinct()
        )

        patient_severe_days = {}
        for entry in severe_days_qs:
            pid = entry['patient_id']
            patient_severe_days.setdefault(pid, set()).add(entry['day'])

        required_days = {today - timedelta(days=i) for i in range(5)}
        return sum(
            1 for days in patient_severe_days.values()
            if required_days.issubset(days)
        )

