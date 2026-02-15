"""
Biometric data models for TremoAI platform.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class BiometricSession(models.Model):
    """Sensor data recording session from glove device."""

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='biometric_sessions'
    )
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.PROTECT,
        related_name='biometric_sessions'
    )
    session_start = models.DateTimeField()
    session_duration = models.DurationField()
    sensor_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'biometric_sessions'
        ordering = ['-session_start']
        verbose_name = 'Biometric Session'
        verbose_name_plural = 'Biometric Sessions'
        indexes = [
            models.Index(fields=['patient', 'session_start']),
            models.Index(fields=['device', 'session_start']),
        ]

    def __str__(self):
        return f"Session for {self.patient.full_name} on {self.session_start.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate session_start is not in future
        if self.session_start and self.session_start > timezone.now():
            raise ValidationError({'session_start': 'Session start time cannot be in the future.'})

        # Validate session_duration is positive
        if self.session_duration and self.session_duration.total_seconds() <= 0:
            raise ValidationError({'session_duration': 'Session duration must be positive.'})

        # Validate device is paired to patient
        if self.device and self.patient and self.device.patient_id != self.patient_id:
            raise ValidationError({
                'device': f'Device {self.device.serial_number} is not paired to patient {self.patient.full_name}.'
            })

        # Validate sensor_data JSON structure
        if self.sensor_data:
            required_keys = ['tremor_intensity', 'timestamps', 'frequency']
            missing_keys = [key for key in required_keys if key not in self.sensor_data]
            if missing_keys:
                raise ValidationError({
                    'sensor_data': f'Missing required keys: {", ".join(missing_keys)}'
                })

    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation."""
        self.full_clean()
        super().save(*args, **kwargs)
