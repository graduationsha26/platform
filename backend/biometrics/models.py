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

    # Real-Time Pipeline (Feature 002) - ML prediction fields
    ml_prediction = models.JSONField(
        null=True,
        blank=True,
        help_text="ML model prediction results (severity, confidence)"
    )
    ml_predicted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when ML prediction was generated"
    )
    received_via_mqtt = models.BooleanField(
        default=False,
        help_text="True if session data arrived via MQTT real-time pipeline"
    )

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

        # Validate ml_prediction consistency
        if self.ml_prediction and not self.ml_predicted_at:
            raise ValidationError({
                'ml_predicted_at': 'ml_predicted_at must be set when ml_prediction is provided.'
            })

        # Validate ml_prediction JSON structure
        if self.ml_prediction:
            required_pred_keys = ['severity', 'confidence']
            missing_pred_keys = [key for key in required_pred_keys if key not in self.ml_prediction]
            if missing_pred_keys:
                raise ValidationError({
                    'ml_prediction': f'Missing required keys: {", ".join(missing_pred_keys)}'
                })

            # Validate severity value
            valid_severities = ['mild', 'moderate', 'severe']
            if self.ml_prediction.get('severity') not in valid_severities:
                raise ValidationError({
                    'ml_prediction': f'Severity must be one of: {", ".join(valid_severities)}'
                })

            # Validate confidence range
            confidence = self.ml_prediction.get('confidence')
            if confidence is not None and not (0.0 <= confidence <= 1.0):
                raise ValidationError({
                    'ml_prediction': 'Confidence must be between 0.0 and 1.0'
                })

        # Validate ml_predicted_at is after or equal to session_start
        if self.ml_predicted_at and self.session_start and self.ml_predicted_at < self.session_start:
            raise ValidationError({
                'ml_predicted_at': 'ML prediction timestamp cannot be before session start time.'
            })

    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation."""
        self.full_clean()
        super().save(*args, **kwargs)
