"""Django models for inference app."""

from django.db import models
from django.conf import settings
import uuid


class InferenceLog(models.Model):
    """
    Audit log for all inference requests.

    Stores metadata about each inference request for:
    - Compliance and audit trail
    - Analytics and usage statistics
    - Performance monitoring
    - Debugging inference issues

    Note: Does NOT store raw sensor data (privacy consideration).
    Only stores prediction outcomes and metadata.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this inference request"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inference_logs',
        help_text="User who made the inference request (doctor or patient)"
    )

    model_used = models.CharField(
        max_length=50,
        help_text="Model name: rf, svm, lstm, or cnn_1d"
    )

    prediction = models.BooleanField(
        help_text="Tremor detected (True) or not detected (False)"
    )

    severity = models.IntegerField(
        help_text="Severity level: 0 (none), 1 (mild), 2 (moderate), 3 (severe)"
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Model confidence score (0.0-1.0) - P3 feature"
    )

    inference_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Inference duration in milliseconds - P3 feature"
    )

    input_shape = models.CharField(
        max_length=50,
        help_text="Input data shape for debugging (e.g., '(128, 6)' or '(18,)')"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the inference was performed"
    )

    class Meta:
        db_table = 'inference_inferencelog'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp'], name='idx_user_time'),
            models.Index(fields=['model_used'], name='idx_model'),
            models.Index(fields=['-timestamp'], name='idx_time'),
        ]
        verbose_name = 'Inference Log'
        verbose_name_plural = 'Inference Logs'

    def __str__(self):
        return f"Inference {self.id} - {self.model_used} - {self.timestamp}"

    def __repr__(self):
        return (
            f"<InferenceLog id={self.id} user={self.user.username} "
            f"model={self.model_used} prediction={self.prediction} "
            f"severity={self.severity}>"
        )
