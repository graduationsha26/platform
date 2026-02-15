"""
Validation functions for MQTT messages and device pairing.

Provides validation for:
- MQTT message schema
- Device registration and pairing
- Tremor intensity values
- Timestamp ordering
"""
import logging
from typing import Optional, Tuple
from datetime import datetime

from django.core.exceptions import ValidationError
from devices.models import Device
from patients.models import Patient

logger = logging.getLogger(__name__)


def validate_mqtt_message(payload: dict) -> None:
    """
    Validate MQTT message schema and data integrity.

    Args:
        payload: MQTT message payload (parsed JSON)

    Raises:
        ValidationError: If message is invalid

    Validates:
        - Required fields present
        - Data types correct
        - tremor_intensity values in range [0.0, 1.0]
        - tremor_intensity and timestamps arrays have equal length
        - timestamps are chronologically ordered
    """
    # Check required fields
    required_fields = [
        'serial_number',
        'timestamp',
        'tremor_intensity',
        'frequency',
        'timestamps',
        'session_duration'
    ]

    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate serial_number
    serial_number = payload.get('serial_number')
    if not isinstance(serial_number, str) or not (8 <= len(serial_number) <= 20):
        raise ValidationError("serial_number must be a string with 8-20 characters")

    if not serial_number.isalnum() or not serial_number.isupper():
        raise ValidationError("serial_number must be alphanumeric uppercase")

    # Validate timestamp
    timestamp = payload.get('timestamp')
    if not isinstance(timestamp, str):
        raise ValidationError("timestamp must be a string in ISO 8601 format")

    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        raise ValidationError("timestamp must be valid ISO 8601 format")

    # Validate tremor_intensity
    tremor_intensity = payload.get('tremor_intensity')
    if not isinstance(tremor_intensity, list) or len(tremor_intensity) == 0:
        raise ValidationError("tremor_intensity must be a non-empty array")

    for i, value in enumerate(tremor_intensity):
        if not isinstance(value, (int, float)):
            raise ValidationError(f"tremor_intensity[{i}] must be a number")
        if not (0.0 <= value <= 1.0):
            raise ValidationError(f"tremor_intensity[{i}] = {value} is out of range [0.0, 1.0]")

    # Validate frequency
    frequency = payload.get('frequency')
    if not isinstance(frequency, (int, float)) or frequency <= 0:
        raise ValidationError("frequency must be a positive number")

    # Validate timestamps array
    timestamps = payload.get('timestamps')
    if not isinstance(timestamps, list) or len(timestamps) == 0:
        raise ValidationError("timestamps must be a non-empty array")

    # Check equal length
    if len(tremor_intensity) != len(timestamps):
        raise ValidationError(
            f"tremor_intensity ({len(tremor_intensity)}) and timestamps ({len(timestamps)}) "
            f"must have equal length"
        )

    # Validate timestamps are ISO 8601 strings and chronologically ordered
    prev_ts = None
    for i, ts_str in enumerate(timestamps):
        if not isinstance(ts_str, str):
            raise ValidationError(f"timestamps[{i}] must be a string")

        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(f"timestamps[{i}] must be valid ISO 8601 format")

        if prev_ts and ts < prev_ts:
            raise ValidationError(f"timestamps[{i}] is not chronologically ordered")

        prev_ts = ts

    # Validate session_duration
    session_duration = payload.get('session_duration')
    if not isinstance(session_duration, int) or session_duration <= 0:
        raise ValidationError("session_duration must be a positive integer")


def validate_device_pairing(serial_number: str) -> Tuple[Optional[Device], Optional[Patient]]:
    """
    Validate that a device is registered and paired to a patient.

    Args:
        serial_number: Device serial number

    Returns:
        Tuple of (Device, Patient) if valid, (None, None) if not paired

    Raises:
        ValidationError: If device is not registered
    """
    # Check if device exists
    try:
        device = Device.objects.select_related('patient').get(serial_number=serial_number)
    except Device.DoesNotExist:
        raise ValidationError(f"Device with serial number {serial_number} is not registered")

    # Check if device is paired to a patient
    if not device.patient:
        logger.warning(f"Device {serial_number} is not paired to any patient")
        return None, None

    patient = device.patient
    logger.debug(f"Device {serial_number} is paired to patient {patient.id} ({patient.full_name})")

    return device, patient
