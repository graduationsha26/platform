"""
Django models for CMG (Control Moment Gyroscope) motor telemetry, fault events,
gimbal calibration, servo commands, gimbal state, and PID controller tuning.

Feature 027: CMG Brushless Motor & ESC Initialization
Feature 028: CMG Gimbal Servo Control
Feature 029: CMG PID Controller Tuning
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class MotorTelemetry(models.Model):
    """
    Time-series record of CMG rotor motor state published by the glove at ~1 Hz.

    Stores speed (RPM), current draw, and operational status for each 1-second
    telemetry snapshot received via MQTT topic devices/{serial}/cmg_telemetry.

    Retention: 30 days (older rows purged by purge_cmg_telemetry management command).
    """

    STATUS_IDLE = 'idle'
    STATUS_STARTING = 'starting'
    STATUS_RUNNING = 'running'
    STATUS_FAULT = 'fault'
    STATUS_CHOICES = [
        (STATUS_IDLE, 'Idle'),
        (STATUS_STARTING, 'Starting'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_FAULT, 'Fault'),
    ]

    FAULT_OVERCURRENT = 'overcurrent'
    FAULT_STALL = 'stall'
    FAULT_TYPE_CHOICES = [
        (FAULT_OVERCURRENT, 'Overcurrent'),
        (FAULT_STALL, 'Stall'),
    ]

    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='motor_telemetry',
        db_index=False,  # covered by composite indexes below
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='motor_telemetry',
        db_index=False,  # covered by composite indexes below
    )
    timestamp = models.DateTimeField(
        db_index=False,  # covered by composite indexes below
    )
    rpm = models.IntegerField()
    current_a = models.FloatField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    fault_type = models.CharField(
        max_length=16,
        choices=FAULT_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmg_motor_telemetry'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp'], name='cmg_device_ts_desc_idx'),
            models.Index(fields=['patient', '-timestamp'], name='cmg_patient_ts_desc_idx'),
        ]

    def __str__(self):
        return (
            f"MotorTelemetry(device={self.device_id}, "
            f"ts={self.timestamp}, status={self.status}, rpm={self.rpm})"
        )


class MotorFaultEvent(models.Model):
    """
    Persistent record of each safety fault triggered during CMG operation.

    Records overcurrent and stall faults with their sensor values at the time
    of occurrence. Includes acknowledgment tracking — a doctor must explicitly
    acknowledge a fault before the motor can be restarted.

    Retention: indefinite (medical device event history).
    """

    FAULT_OVERCURRENT = 'overcurrent'
    FAULT_STALL = 'stall'
    FAULT_TYPE_CHOICES = [
        (FAULT_OVERCURRENT, 'Overcurrent'),
        (FAULT_STALL, 'Stall'),
    ]

    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='motor_fault_events',
        db_index=False,  # covered by composite indexes below
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='motor_fault_events',
        db_index=False,  # covered by composite indexes below
    )
    occurred_at = models.DateTimeField(db_index=False)  # covered by composite indexes
    fault_type = models.CharField(max_length=16, choices=FAULT_TYPE_CHOICES)
    rpm_at_fault = models.IntegerField(null=True, blank=True)
    current_at_fault = models.FloatField(null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_faults',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmg_motor_fault_events'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['device', '-occurred_at'], name='cmg_fault_device_ts_idx'),
            models.Index(fields=['patient', '-occurred_at'], name='cmg_fault_patient_ts_idx'),
            models.Index(fields=['acknowledged', '-occurred_at'], name='cmg_fault_ack_ts_idx'),
        ]

    def __str__(self):
        return (
            f"MotorFaultEvent(device={self.device_id}, "
            f"type={self.fault_type}, occurred_at={self.occurred_at}, "
            f"acknowledged={self.acknowledged})"
        )


# ---------------------------------------------------------------------------
# Feature 028: CMG Gimbal Servo Control
# ---------------------------------------------------------------------------


class GimbalCalibration(models.Model):
    """
    Per-device gimbal servo calibration — center positions, travel range, and rate limit.

    A single retained record per device. If no record exists, consumers fall back to
    system defaults (pitch ±30°, roll ±20°, 45 deg/s). Updated by doctors via
    PUT /api/cmg/servo/calibration/{device_pk}/ and pushed to the glove as a
    retained MQTT servo_config message.

    config_version is incremented on every save so the glove can detect stale config.
    """

    device = models.OneToOneField(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='gimbal_calibration',
    )
    pitch_center_deg = models.FloatField(default=0.0)
    roll_center_deg = models.FloatField(default=0.0)
    pitch_min_deg = models.FloatField(default=-30.0)
    pitch_max_deg = models.FloatField(default=30.0)
    roll_min_deg = models.FloatField(default=-20.0)
    roll_max_deg = models.FloatField(default=20.0)
    rate_limit_deg_per_sec = models.FloatField(default=45.0)
    config_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gimbal_calibrations_updated',
    )

    class Meta:
        db_table = 'cmg_gimbal_calibration'

    def clean(self):
        from .validators import validate_calibration_bounds
        validate_calibration_bounds({
            'pitch_min_deg': self.pitch_min_deg,
            'pitch_max_deg': self.pitch_max_deg,
            'roll_min_deg': self.roll_min_deg,
            'roll_max_deg': self.roll_max_deg,
            'rate_limit_deg_per_sec': self.rate_limit_deg_per_sec,
        })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"GimbalCalibration(device={self.device_id}, "
            f"pitch=[{self.pitch_min_deg},{self.pitch_max_deg}], "
            f"roll=[{self.roll_min_deg},{self.roll_max_deg}], "
            f"rate={self.rate_limit_deg_per_sec})"
        )


class ServoCommand(models.Model):
    """
    Audit log of every servo position command issued by a doctor.

    Each record captures a snapshot of the active calibration at the time of
    issue (rate_limit_snap, pitch/roll min/max snapshots) so the audit trail
    is self-contained even if calibration is later updated.

    command_id UUID allows the glove firmware to deduplicate QoS-1 re-deliveries.
    """

    STATUS_PENDING = 'pending'
    STATUS_PUBLISHED = 'published'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_FAILED, 'Failed'),
    ]

    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='servo_commands',
        db_index=False,  # covered by composite index below
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='servo_commands',
        db_index=False,  # covered by composite index below
    )
    issued_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.PROTECT,
        related_name='issued_servo_commands',
    )
    command_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    target_pitch_deg = models.FloatField(null=True, blank=True)
    target_roll_deg = models.FloatField(null=True, blank=True)
    is_home_command = models.BooleanField(default=False)
    # Calibration snapshot at time of issue
    rate_limit_snap = models.FloatField()
    pitch_min_snap = models.FloatField()
    pitch_max_snap = models.FloatField()
    roll_min_snap = models.FloatField()
    roll_max_snap = models.FloatField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmg_servo_commands'
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['device', '-issued_at'], name='cmg_servo_device_ts_idx'),
            models.Index(fields=['patient', '-issued_at'], name='cmg_servo_patient_ts_idx'),
        ]

    def __str__(self):
        cmd = 'home' if self.is_home_command else f'set_position(pitch={self.target_pitch_deg}, roll={self.target_roll_deg})'
        return f"ServoCommand(device={self.device_id}, {cmd}, status={self.status})"


class GimbalState(models.Model):
    """
    Latest-state-only record of current gimbal position and axis status.

    Updated via update_or_create on every MQTT servo_state message from the
    device. Not a time-series table — only stores the most recent reading.

    Returns 404 via REST if no MQTT message has been received yet for the device.
    """

    STATUS_IDLE = 'idle'
    STATUS_MOVING = 'moving'
    STATUS_FAULT = 'fault'
    STATUS_CHOICES = [
        (STATUS_IDLE, 'Idle'),
        (STATUS_MOVING, 'Moving'),
        (STATUS_FAULT, 'Fault'),
    ]

    device = models.OneToOneField(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='gimbal_state',
    )
    pitch_deg = models.FloatField()
    roll_deg = models.FloatField()
    pitch_status = models.CharField(max_length=8, choices=STATUS_CHOICES)
    roll_status = models.CharField(max_length=8, choices=STATUS_CHOICES)
    device_timestamp = models.DateTimeField()
    received_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cmg_gimbal_state'

    def __str__(self):
        return (
            f"GimbalState(device={self.device_id}, "
            f"pitch={self.pitch_deg}°/{self.pitch_status}, "
            f"roll={self.roll_deg}°/{self.roll_status})"
        )


# ---------------------------------------------------------------------------
# Feature 029: CMG PID Controller Tuning
# ---------------------------------------------------------------------------


class PIDConfig(models.Model):
    """
    Per-device PID gain configuration for the dual-axis tremor suppression loop.

    One record per device (OneToOneField). If no record exists, views fall back
    to system defaults read from PID_K*_*_DEFAULT environment variables.

    Pushed to the glove as a retained MQTT pid_config message on every PUT.
    config_version is incremented on each save so the device can detect stale config.
    """

    device = models.OneToOneField(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='pid_config',
    )
    kp_pitch = models.FloatField(default=0.0)
    ki_pitch = models.FloatField(default=0.0)
    kd_pitch = models.FloatField(default=0.0)
    kp_roll  = models.FloatField(default=0.0)
    ki_roll  = models.FloatField(default=0.0)
    kd_roll  = models.FloatField(default=0.0)
    config_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pid_configs_updated',
    )

    class Meta:
        db_table = 'cmg_pid_config'

    def clean(self):
        from .validators import validate_pid_gains
        validate_pid_gains({
            'kp_pitch': self.kp_pitch,
            'ki_pitch': self.ki_pitch,
            'kd_pitch': self.kd_pitch,
            'kp_roll':  self.kp_roll,
            'ki_roll':  self.ki_roll,
            'kd_roll':  self.kd_roll,
        })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"PIDConfig(device={self.device_id}, "
            f"pitch=[{self.kp_pitch},{self.ki_pitch},{self.kd_pitch}], "
            f"roll=[{self.kp_roll},{self.ki_roll},{self.kd_roll}])"
        )


class SuppressionSession(models.Model):
    """
    Bounded period during which automatic PID tremor suppression was active.

    Each doctor-initiated enable creates a new session. Provides audit trail
    (FR-012) and the session context for SuppressionMetric records.

    At most one 'active' session per device at a time. Starting a new session
    while one is active automatically interrupts the previous one.

    Gain snapshot fields capture the PIDConfig values in effect at session start,
    keeping the audit self-contained even if gains are later updated.
    """

    STATUS_ACTIVE      = 'active'
    STATUS_COMPLETED   = 'completed'
    STATUS_INTERRUPTED = 'interrupted'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,      'Active'),
        (STATUS_COMPLETED,   'Completed'),
        (STATUS_INTERRUPTED, 'Interrupted'),
    ]

    session_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.CASCADE,
        related_name='suppression_sessions',
        db_index=False,  # covered by composite indexes below
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='suppression_sessions',
        db_index=False,  # covered by composite indexes below
    )
    started_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.PROTECT,
        related_name='started_suppression_sessions',
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    # PIDConfig snapshot at session start
    kp_pitch_snap = models.FloatField()
    ki_pitch_snap = models.FloatField()
    kd_pitch_snap = models.FloatField()
    kp_roll_snap  = models.FloatField()
    ki_roll_snap  = models.FloatField()
    kd_roll_snap  = models.FloatField()

    class Meta:
        db_table = 'cmg_suppression_sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['device', '-started_at'], name='cmg_supp_device_ts_idx'),
            models.Index(fields=['patient', '-started_at'], name='cmg_supp_patient_ts_idx'),
            models.Index(fields=['status', '-started_at'], name='cmg_supp_status_ts_idx'),
        ]

    def __str__(self):
        return (
            f"SuppressionSession(device={self.device_id}, "
            f"status={self.status}, started={self.started_at})"
        )


class SuppressionMetric(models.Model):
    """
    Time-series amplitude readings captured during a suppression session at ~1 Hz.

    Downsampled from the device's ~10 Hz pid_status stream in the MQTT handler
    (_pid_sample_counters in MQTTClient). Used for aggregate effectiveness reporting
    and live WebSocket chart display.

    Retention: 30 days (cleanup_pid_metrics management command).
    """

    session = models.ForeignKey(
        SuppressionSession,
        on_delete=models.CASCADE,
        related_name='suppression_metrics',
        db_index=False,  # covered by composite index below
    )
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.PROTECT,
        related_name='suppression_metrics',
        db_index=False,  # covered by composite index below
    )
    device_timestamp = models.DateTimeField()
    raw_amplitude_deg = models.FloatField()
    residual_amplitude_deg = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmg_suppression_metrics'
        ordering = ['-device_timestamp']
        indexes = [
            models.Index(fields=['session', 'device_timestamp'], name='cmg_metric_session_ts_idx'),
            models.Index(fields=['device', 'device_timestamp'],  name='cmg_metric_device_ts_idx'),
            models.Index(fields=['created_at'],                  name='cmg_metric_created_idx'),
        ]

    def __str__(self):
        return (
            f"SuppressionMetric(session={self.session_id}, "
            f"ts={self.device_timestamp}, "
            f"raw={self.raw_amplitude_deg:.2f}°, "
            f"residual={self.residual_amplitude_deg:.2f}°)"
        )
