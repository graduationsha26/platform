"""
Device models for TremoAI platform.
"""
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class Device(models.Model):
    """Physical glove hardware device model."""

    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    serial_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                r'^[A-Z0-9]{8,20}$',
                'Serial number must be 8-20 alphanumeric uppercase characters.'
            )
        ]
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='offline'
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices'
    )
    registered_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.PROTECT,
        related_name='registered_devices'
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'devices'
        ordering = ['-registered_at']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'

    def __str__(self):
        return f"Device {self.serial_number} ({self.status})"

    def clean(self):
        """Validate registered_by is a doctor."""
        super().clean()
        if self.registered_by and self.registered_by.role != 'doctor':
            raise ValidationError({'registered_by': 'Devices can only be registered by doctors.'})

    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation."""
        self.full_clean()
        super().save(*args, **kwargs)
