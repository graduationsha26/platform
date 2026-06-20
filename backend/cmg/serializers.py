"""
Serializers for CMG motor telemetry, fault events, gimbal calibration,
servo commands, and gimbal state.

Feature 027: CMG Brushless Motor & ESC Initialization
Feature 028: CMG Gimbal Servo Control
"""
from rest_framework import serializers

from .models import (
    MotorTelemetry, MotorFaultEvent,
    GimbalCalibration, GimbalState,
    PIDConfig, SuppressionSession, SuppressionMetric,
)


class MotorTelemetrySerializer(serializers.ModelSerializer):
    """Read-only serializer for MotorTelemetry records.

    Exposes device_id and patient_id as flat fields alongside all sensor
    and status fields. Records are created exclusively by the MQTT pipeline.
    """

    class Meta:
        model = MotorTelemetry
        fields = [
            'id', 'device_id', 'patient_id',
            'timestamp', 'rpm', 'current_a', 'status', 'fault_type',
        ]
        read_only_fields = fields


class MotorFaultEventSerializer(serializers.ModelSerializer):
    """Read-only serializer for MotorFaultEvent records.

    Exposes all fault fields including acknowledgment state.
    Records are created exclusively by the MQTT pipeline;
    only the 'acknowledged' fields are mutable (via the acknowledge action).
    """

    class Meta:
        model = MotorFaultEvent
        fields = [
            'id', 'device_id', 'patient_id',
            'occurred_at', 'fault_type', 'rpm_at_fault', 'current_at_fault',
            'acknowledged', 'acknowledged_at', 'acknowledged_by_id',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Feature 028: CMG Gimbal Servo Control
# ---------------------------------------------------------------------------


class ServoCommandInputSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/cmg/servo/commands/.

    Validates the command type and optional angle fields. Angle range validation
    against per-device calibration is performed in the view after calibration is loaded.
    """

    COMMAND_SET_POSITION = 'set_position'
    COMMAND_HOME = 'home'
    VALID_COMMANDS = [COMMAND_SET_POSITION, COMMAND_HOME]

    device_id = serializers.IntegerField()
    command = serializers.ChoiceField(choices=VALID_COMMANDS)
    pitch_deg = serializers.FloatField(required=False, allow_null=True)
    roll_deg = serializers.FloatField(required=False, allow_null=True)

    def validate(self, data):
        if data['command'] == self.COMMAND_SET_POSITION:
            if data.get('pitch_deg') is None and data.get('roll_deg') is None:
                raise serializers.ValidationError(
                    'At least one of pitch_deg or roll_deg is required for set_position command.'
                )
        return data


class GimbalCalibrationSerializer(serializers.ModelSerializer):
    """
    Serializer for GimbalCalibration — used for both GET and PUT responses.

    Exposes device_id as a flat field. The updated_by foreign key is exposed
    as updated_by_id (integer) to match the API contract.
    """

    class Meta:
        model = GimbalCalibration
        fields = [
            'device_id',
            'pitch_center_deg', 'roll_center_deg',
            'pitch_min_deg', 'pitch_max_deg',
            'roll_min_deg', 'roll_max_deg',
            'rate_limit_deg_per_sec',
            'updated_at', 'updated_by_id',
        ]
        read_only_fields = ['device_id', 'updated_at', 'updated_by_id']

    def validate(self, data):
        from .validators import validate_calibration_bounds
        validate_calibration_bounds(data)
        return data


class GimbalStateSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for GimbalState — the latest gimbal position and axis status.

    Exposes device_id as a flat field alongside angle and status fields.
    Records are created/updated exclusively by the MQTT pipeline.
    """

    class Meta:
        model = GimbalState
        fields = [
            'device_id',
            'pitch_deg', 'roll_deg',
            'pitch_status', 'roll_status',
            'device_timestamp', 'received_at',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Feature 029: CMG PID Controller Tuning
# ---------------------------------------------------------------------------


class PIDConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for PIDConfig — used for both GET and PUT responses.

    Exposes device_id as a flat field. The updated_by foreign key is exposed
    as updated_by_id (integer) to match the API contract.
    """

    class Meta:
        model = PIDConfig
        fields = [
            'device_id',
            'kp_pitch', 'ki_pitch', 'kd_pitch',
            'kp_roll', 'ki_roll', 'kd_roll',
            'config_version', 'updated_at', 'updated_by_id',
        ]
        read_only_fields = ['device_id', 'config_version', 'updated_at', 'updated_by_id']

    def validate(self, data):
        from .validators import validate_pid_gains
        validate_pid_gains(data)
        return data


# ---------------------------------------------------------------------------
# Feature 029: Suppression Session & Metrics serializers
# ---------------------------------------------------------------------------


class SuppressionSessionSerializer(serializers.ModelSerializer):
    """Read-only serializer for SuppressionSession records."""

    class Meta:
        model = SuppressionSession
        fields = [
            'id', 'session_uuid',
            'device_id', 'patient_id', 'started_by_id',
            'status', 'started_at', 'ended_at',
            'kp_pitch_snap', 'ki_pitch_snap', 'kd_pitch_snap',
            'kp_roll_snap', 'ki_roll_snap', 'kd_roll_snap',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Feature 029: Metric & summary serializers (US3)
# ---------------------------------------------------------------------------


class SuppressionMetricSerializer(serializers.ModelSerializer):
    """Read-only serializer for SuppressionMetric time-series rows."""

    class Meta:
        model = SuppressionMetric
        fields = ['device_timestamp', 'raw_amplitude_deg', 'residual_amplitude_deg']
        read_only_fields = fields


class SuppressionSessionSummarySerializer(SuppressionSessionSerializer):
    """
    Extends SuppressionSessionSerializer with per-session aggregate fields.

    The three aggregate fields are annotated/set by the view before serialization.
    """

    avg_raw_amplitude_deg = serializers.FloatField(allow_null=True, read_only=True)
    avg_residual_amplitude_deg = serializers.FloatField(allow_null=True, read_only=True)
    reduction_pct = serializers.FloatField(allow_null=True, read_only=True)

    class Meta(SuppressionSessionSerializer.Meta):
        fields = SuppressionSessionSerializer.Meta.fields + [
            'avg_raw_amplitude_deg',
            'avg_residual_amplitude_deg',
            'reduction_pct',
        ]
        read_only_fields = fields
