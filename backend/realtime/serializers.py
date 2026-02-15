"""
Serializers for WebSocket messages in the real-time pipeline.

Defines serializers for all WebSocket message types:
- TremorDataSerializer: Sensor data with ML predictions
- StatusSerializer: Connection status messages
- ErrorSerializer: Error messages
- PingPongSerializer: Keepalive messages
"""
from rest_framework import serializers


class MLPredictionSerializer(serializers.Serializer):
    """Serializer for ML prediction results."""

    severity = serializers.ChoiceField(
        choices=['mild', 'moderate', 'severe'],
        help_text="Predicted tremor severity classification"
    )
    confidence = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text="Prediction confidence score (0.0-1.0)"
    )


class TremorDataSerializer(serializers.Serializer):
    """Serializer for tremor data messages sent to WebSocket clients."""

    type = serializers.CharField(default='tremor_data', read_only=True)
    patient_id = serializers.IntegerField(help_text="Patient primary key")
    device_serial = serializers.CharField(help_text="Device serial number")
    timestamp = serializers.DateTimeField(help_text="Session start time from device (ISO 8601 UTC)")
    tremor_intensity = serializers.ListField(
        child=serializers.FloatField(min_value=0.0, max_value=1.0),
        help_text="Normalized tremor magnitude readings"
    )
    frequency = serializers.FloatField(min_value=0, help_text="Dominant tremor frequency in Hz")
    session_duration = serializers.IntegerField(
        min_value=0,
        help_text="Session duration in milliseconds"
    )
    prediction = MLPredictionSerializer(
        required=False,
        allow_null=True,
        help_text="ML prediction result (optional, omitted if ML unavailable)"
    )
    received_at = serializers.DateTimeField(
        help_text="Server timestamp when data was received"
    )


class StatusSerializer(serializers.Serializer):
    """Serializer for status messages sent to WebSocket clients."""

    type = serializers.CharField(default='status', read_only=True)
    status = serializers.ChoiceField(
        choices=['connected', 'waiting', 'device_unpaired', 'error'],
        help_text="Status code"
    )
    message = serializers.CharField(help_text="Human-readable status message")
    timestamp = serializers.DateTimeField(help_text="Server timestamp")


class ErrorSerializer(serializers.Serializer):
    """Serializer for error messages sent to WebSocket clients."""

    type = serializers.CharField(default='error', read_only=True)
    error_code = serializers.ChoiceField(
        choices=['unauthorized', 'forbidden', 'internal_error'],
        help_text="Machine-readable error code"
    )
    error_message = serializers.CharField(help_text="Human-readable error description")
    timestamp = serializers.DateTimeField(help_text="Server timestamp")


class PingPongSerializer(serializers.Serializer):
    """Serializer for ping/pong keepalive messages."""

    type = serializers.ChoiceField(
        choices=['ping', 'pong'],
        help_text="Message type (ping or pong)"
    )
    timestamp = serializers.DateTimeField(help_text="Timestamp")
