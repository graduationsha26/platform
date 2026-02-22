"""
Unit tests for MQTT client.

Tests MQTT message validation and processing logic.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from django.test import TestCase

from realtime.mqtt_client import MQTTClient
from realtime.validators import validate_mqtt_message, validate_biometric_reading_message
from django.core.exceptions import ValidationError


class MQTTMessageValidationTest(TestCase):
    """Test MQTT message validation logic."""

    def test_valid_mqtt_message(self):
        """Test validation passes for valid MQTT message."""
        valid_payload = {
            'serial_number': 'GLV2024A001',
            'timestamp': '2024-02-15T10:30:00Z',
            'tremor_intensity': [0.25, 0.30, 0.28, 0.32],
            'frequency': 4.5,
            'timestamps': ['2024-02-15T10:30:00Z', '2024-02-15T10:30:01Z', '2024-02-15T10:30:02Z', '2024-02-15T10:30:03Z'],
            'session_duration': 1000
        }

        # Should not raise exception
        validate_mqtt_message(valid_payload)

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        invalid_payload = {
            'serial_number': 'GLV-2024-A001',
            # Missing timestamp, tremor_intensity, etc.
        }

        with pytest.raises(ValidationError):
            validate_mqtt_message(invalid_payload)

    def test_invalid_tremor_intensity_range(self):
        """Test validation fails when tremor_intensity values are out of range."""
        invalid_payload = {
            'serial_number': 'GLV-2024-A001',
            'timestamp': '2024-02-15T10:30:00Z',
            'tremor_intensity': [1.5, 0.30],  # 1.5 is out of range [0.0, 1.0]
            'frequency': 4.5,
            'timestamps': ['2024-02-15T10:30:00Z', '2024-02-15T10:30:01Z'],
            'session_duration': 1000
        }

        with pytest.raises(ValidationError):
            validate_mqtt_message(invalid_payload)

    def test_invalid_serial_number_format(self):
        """Test validation fails for invalid serial number format."""
        invalid_payload = {
            'serial_number': '123',  # Too short
            'timestamp': '2024-02-15T10:30:00Z',
            'tremor_intensity': [0.25, 0.30],
            'frequency': 4.5,
            'timestamps': ['2024-02-15T10:30:00Z', '2024-02-15T10:30:01Z'],
            'session_duration': 1000
        }

        with pytest.raises(ValidationError):
            validate_mqtt_message(invalid_payload)


# TODO: Add tests for:
# - MQTT connection handling
# - Device pairing validation
# - Database storage logic
# - Reconnection with exponential backoff
# - WebSocket broadcasting


# ---------------------------------------------------------------------------
# Feature E-2.4: Raw sensor reading MQTT message validation
# Tests for validate_biometric_reading_message() and _handle_reading_message()
# ---------------------------------------------------------------------------

def _valid_reading_payload(**overrides):
    """Return a minimal valid 6-field reading payload, with optional overrides."""
    payload = {
        'device_id': 'GLV20241001',
        'timestamp': '2026-02-18T10:30:00.123Z',
        'aX': 1.23,
        'aY': -0.45,
        'aZ': 9.81,
        'gX': 0.12,
        'gY': -0.34,
        'gZ': 0.56,
    }
    payload.update(overrides)
    return payload


class BiometricReadingMQTTValidationTest(TestCase):
    """
    Test suite for the raw sensor reading MQTT validator (Feature E-2.4).

    Validates that:
    - 6-field payloads (no flex) are accepted
    - Legacy 11-field payloads (with flex_1-flex_5) are also accepted
    - Required field violations raise ValidationError
    - Out-of-range values warn but are not rejected
    - flex_1-flex_5 are never stored in BiometricReading records
    """

    # ── T006: US1 — Valid 6-field payload passes validation ─────────────────

    def test_valid_6_field_reading_payload(self):
        """Valid 6-sensor-field payload passes without exception (T006)."""
        payload = _valid_reading_payload()
        # Should not raise any exception
        validate_biometric_reading_message(payload)

    # ── T007: US1 — Missing required sensor field raises ValidationError ─────

    def test_missing_required_sensor_field_raises_error(self):
        """Payload missing gZ raises ValidationError mentioning gZ (T007)."""
        payload = _valid_reading_payload()
        del payload['gZ']

        with self.assertRaises(ValidationError) as ctx:
            validate_biometric_reading_message(payload)

        self.assertIn('gZ', str(ctx.exception))

    # ── T008: US1 — Non-numeric sensor value raises ValidationError ──────────

    def test_non_numeric_sensor_value_raises_error(self):
        """Payload with aX as a string raises ValidationError (T008)."""
        payload = _valid_reading_payload(aX='not_a_number')

        with self.assertRaises(ValidationError):
            validate_biometric_reading_message(payload)

    # ── T009: US1 — Invalid timestamp raises ValidationError ─────────────────

    def test_invalid_timestamp_format_raises_error(self):
        """Payload with an unparseable timestamp raises ValidationError (T009)."""
        payload = _valid_reading_payload(timestamp='not-a-date')

        with self.assertRaises(ValidationError):
            validate_biometric_reading_message(payload)

    # ── T010: US2 — Legacy 11-field payload (with flex) is accepted ──────────

    def test_legacy_11_field_payload_is_accepted(self):
        """
        Payload with flex_1-flex_5 alongside the 6 standard fields passes
        validation without error. Flex fields are silently ignored (T010).
        """
        payload = _valid_reading_payload(
            flex_1=0.50,
            flex_2=0.33,
            flex_3=0.71,
            flex_4=0.20,
            flex_5=0.44,
        )
        # Should not raise any exception
        validate_biometric_reading_message(payload)

    # ── T011: US2 — flex fields not stored in BiometricReading ───────────────

    def test_flex_fields_not_stored_in_biometric_reading(self):
        """
        _handle_reading_message() creates BiometricReading with only the 6
        standard sensor fields. flex_1-flex_5 are never passed to .create() (T011).
        """
        legacy_payload = _valid_reading_payload(
            flex_1=0.50,
            flex_2=0.33,
            flex_3=0.71,
            flex_4=0.20,
            flex_5=0.44,
        )

        mock_patient = Mock()
        mock_patient.id = 1
        mock_device = Mock()
        mock_reading = Mock()
        mock_reading.id = 99

        with patch('realtime.mqtt_client.validate_biometric_reading_message'), \
             patch('realtime.mqtt_client.validate_device_pairing',
                   return_value=(mock_device, mock_patient)), \
             patch('realtime.mqtt_client.BiometricReading.objects.create',
                   return_value=mock_reading) as mock_create, \
             patch('realtime.mqtt_client.get_channel_layer'), \
             patch('realtime.mqtt_client.MLPredictionService'):

            client = MQTTClient()
            client._handle_reading_message(legacy_payload, 'GLV20241001')

        # Verify create() was called exactly once
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs

        # Six standard fields must be present
        for field in ('aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'):
            self.assertIn(field, call_kwargs, f"Expected '{field}' in create() kwargs")

        # Flex fields must NOT be present
        for flex_field in ('flex_1', 'flex_2', 'flex_3', 'flex_4', 'flex_5'):
            self.assertNotIn(
                flex_field, call_kwargs,
                f"'{flex_field}' should not be passed to BiometricReading.objects.create()"
            )

    # ── T012: US2 — Out-of-range sensor value warns but does not raise ───────

    def test_out_of_range_sensor_value_warns_not_raises(self):
        """
        aX=999.0 (outside the -20.0/+20.0 m/s² range) triggers a WARNING log
        but does NOT raise ValidationError (T012).
        """
        payload = _valid_reading_payload(aX=999.0)

        with self.assertLogs('realtime.validators', level='WARNING') as log_ctx:
            # Should not raise; out-of-range is a warning-level event
            validate_biometric_reading_message(payload)

        # Confirm a warning about the out-of-range value was emitted
        warning_messages = ' '.join(log_ctx.output)
        self.assertIn('aX', warning_messages)
