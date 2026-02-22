"""
MQTT client for receiving sensor data from TremoAI glove devices.

This module implements a persistent MQTT connection that subscribes to
device data topics and processes incoming sensor measurements.
"""
import json
import logging
import threading
import time
import uuid
from datetime import timedelta
from typing import Optional

import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from decouple import config
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from devices.models import Device
from biometrics.models import BiometricSession, BiometricReading
from realtime.validators import (
    validate_mqtt_message,
    validate_biometric_reading_message,
    validate_device_pairing,
)
from realtime.ml_service import MLPredictionService
from realtime.filter_service import TremorFilterService

logger = logging.getLogger(__name__)


class MQTTClient:
    """
    MQTT client for subscribing to glove device sensor data.

    Handles:
    - Connection to MQTT broker
    - Subscription to device data topics
    - Message validation and processing
    - Database storage
    - WebSocket broadcasting via channel layer
    - Automatic reconnection with exponential backoff
    """

    def __init__(self):
        """Initialize MQTT client with broker configuration."""
        self.broker_url = config('MQTT_BROKER_URL', default='mqtt://localhost:1883')
        self.username = config('MQTT_USERNAME', default='')
        self.password = config('MQTT_PASSWORD', default='')

        # Parse broker URL
        self.broker_host, self.broker_port = self._parse_broker_url(self.broker_url)

        # Initialize MQTT client (CallbackAPIVersion.VERSION2 — avoids paho-mqtt 2.x deprecation)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish

        # Reconnection tracking
        self.reconnect_count = 0
        self.max_reconnect_attempts = 10
        self.max_reconnect_delay = 60  # seconds

        # Connection state flag — checked before publishing commands
        self.is_connected = False

        # Lock for thread-safe publishing from Django request threads (paho Issue #354)
        self._publish_lock = threading.Lock()

        # Channel layer for WebSocket broadcasting
        self.channel_layer = get_channel_layer()

        # ML prediction service (singleton)
        self.ml_service = MLPredictionService()

        # Tremor signal filter + FFT service (singleton, per-patient state)
        self.tremor_service = TremorFilterService()

        # Per-session sample counter for 1 Hz downsampling of pid_status metrics (Feature 029)
        # Key: "{serial_number}:{session_id}", Value: int sample count
        self._pid_sample_counters: dict = {}

    def _parse_broker_url(self, url: str) -> tuple[str, int]:
        """
        Parse MQTT broker URL into host and port.

        Args:
            url: MQTT URL in format mqtt://host:port

        Returns:
            Tuple of (host, port)
        """
        if url.startswith('mqtt://'):
            url = url[7:]  # Remove mqtt:// prefix

        if ':' in url:
            host, port_str = url.rsplit(':', 1)
            port = int(port_str)
        else:
            host = url
            port = 1883  # Default MQTT port

        return host, port

    def connect(self):
        """
        Connect to MQTT broker and start loop.

        This method blocks and runs forever, maintaining the connection.
        """
        # Set authentication if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # Connect to broker
        logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)

        # Start loop (blocking)
        self.client.loop_forever()

    def disconnect(self):
        """Disconnect from MQTT broker."""
        logger.info("Disconnecting from MQTT broker...")
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        """
        Callback for when connection is established (paho-mqtt VERSION2 signature).

        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            reason_code: Connection result (ReasonCode object; == 0 means success)
            properties: MQTT v5 properties (unused for v3.1.1)
        """
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker successfully (code {reason_code})")
            self.is_connected = True

            # Subscribe to session-level data (BiometricSession)
            session_topic = "devices/+/data"
            client.subscribe(session_topic)
            logger.info(f"Subscribed to topic: {session_topic}")

            # Subscribe to raw sensor readings (BiometricReading, Feature 030)
            reading_topic = "tremo/sensors/+"
            client.subscribe(reading_topic)
            logger.info(f"Subscribed to topic: {reading_topic}")

            # Subscribe to CMG motor telemetry (Feature 027)
            cmg_telemetry_topic = "devices/+/cmg_telemetry"
            client.subscribe(cmg_telemetry_topic)
            logger.info(f"Subscribed to topic: {cmg_telemetry_topic}")

            # Subscribe to gimbal servo state (Feature 028, QoS 0)
            servo_state_topic = "devices/+/servo_state"
            client.subscribe(servo_state_topic, qos=0)
            logger.info(f"Subscribed to topic: {servo_state_topic}")

            # Subscribe to PID suppression status from device (Feature 029, QoS 0)
            pid_status_topic = "devices/+/pid_status"
            client.subscribe(pid_status_topic, qos=0)
            logger.info(f"Subscribed to topic: {pid_status_topic}")

            # Reset reconnection counter on successful connection
            self.reconnect_count = 0
        else:
            logger.error(f"Failed to connect to MQTT broker (code {reason_code})")

    def on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """
        Callback confirming QoS 1 command delivery to broker (PUBACK received).

        Args:
            client: MQTT client instance
            userdata: User data
            mid: Message ID of the published message
            reason_code: Delivery reason code (paho VERSION2)
            properties: MQTT v5 properties (unused)
        """
        logger.debug(f"Command delivery confirmed by broker: mid={mid}")

    def on_disconnect(self, client, userdata, flags=None, reason_code=None, properties=None):
        """
        Callback for when connection is lost (paho-mqtt VERSION2 signature).

        Implements exponential backoff reconnection strategy.

        Args:
            client: MQTT client instance
            userdata: User data
            flags: Disconnect flags (VERSION2)
            reason_code: Disconnect reason code
            properties: MQTT v5 properties (unused)
        """
        self.is_connected = False
        rc = reason_code if reason_code is not None else flags  # compat shim
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker (code {rc})")

            # Implement exponential backoff reconnection
            while self.reconnect_count < self.max_reconnect_attempts:
                # Calculate delay: 1s, 2s, 4s, 8s, ..., up to 60s
                delay = min(2 ** self.reconnect_count, self.max_reconnect_delay)
                logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_count + 1}/{self.max_reconnect_attempts})...")
                time.sleep(delay)

                try:
                    client.reconnect()
                    logger.info("Reconnected successfully")
                    break
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                    self.reconnect_count += 1
            else:
                logger.critical("Max reconnection attempts reached. Exiting.")
                raise SystemExit(1)
        else:
            logger.info("Clean disconnect from MQTT broker")

    def on_message(self, client, userdata, msg):
        """
        Callback for when a message is received.

        Validates message, stores to database, and broadcasts via WebSocket.

        Args:
            client: MQTT client instance
            userdata: User data
            msg: MQTT message
        """
        try:
            # Log message received
            logger.info(f"Received MQTT message on topic: {msg.topic}")

            # Parse JSON payload
            try:
                payload = json.loads(msg.payload.decode())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in MQTT message: {e}")
                return

            # Extract topic segments
            topic_parts = msg.topic.split('/')

            # Route tremo/sensors/{device_id} → biometric reading handler (Feature 030)
            if len(topic_parts) == 3 and topic_parts[0] == 'tremo' and topic_parts[1] == 'sensors':
                device_id = topic_parts[2]
                self._handle_reading_message(payload, device_id)
                return

            # Route devices/{serial}/{type} → handler dispatch
            if len(topic_parts) != 3 or topic_parts[0] != 'devices':
                logger.error(f"Invalid topic format: {msg.topic}")
                return

            serial_number = topic_parts[1]
            message_type = topic_parts[2]

            # Dispatch based on message type
            if message_type == 'data':
                self._handle_session_message(payload, serial_number)
            elif message_type == 'cmg_telemetry':
                self._handle_cmg_telemetry(payload, serial_number)
            elif message_type == 'cmg_fault':
                self._handle_cmg_fault(payload, serial_number)
            elif message_type == 'servo_state':
                self._handle_servo_state(payload, serial_number)
            elif message_type == 'pid_status':
                self._handle_pid_status(payload, serial_number)
            else:
                logger.warning(f"Unknown MQTT message type '{message_type}' on topic {msg.topic}. Discarding.")

        except ValidationError as e:
            logger.warning(f"Validation error for MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)

    def _handle_session_message(self, payload: dict, serial_number: str):
        """
        Handle a session-level MQTT message (topic: devices/{serial}/data).

        Validates, stores as BiometricSession, and broadcasts via WebSocket.

        Args:
            payload: Parsed MQTT JSON payload
            serial_number: Device serial number extracted from topic
        """
        # Validate message schema
        validate_mqtt_message(payload)

        # Validate device pairing
        device, patient = validate_device_pairing(serial_number)
        if not device or not patient:
            logger.warning(f"Device {serial_number} not paired to patient. Rejecting message.")
            return

        logger.info(f"Validated device: {serial_number} (paired to patient {patient.id})")

        # Generate ML prediction (T044)
        prediction = None
        ml_predicted_at = None
        try:
            sensor_data = {
                'tremor_intensity': payload['tremor_intensity'],
                'frequency': payload['frequency'],
                'timestamps': payload['timestamps'],
            }
            prediction = self.ml_service.predict_severity(sensor_data)
            if prediction:
                ml_predicted_at = timezone.now()
                logger.info(f"ML prediction generated: {prediction}")
        except Exception as e:
            logger.error(f"ML prediction failed: {e}", exc_info=True)
            # Continue processing without prediction (T046)

        # Store to database (T019, T044, T047)
        biometric_session = self._store_to_database(payload, device, patient, prediction, ml_predicted_at)
        logger.info(f"Stored BiometricSession: id={biometric_session.id}")

        # Broadcast to WebSocket clients via channel layer (T034, T045)
        self._broadcast_to_websocket(payload, patient, device, biometric_session, prediction)

    def _handle_reading_message(self, payload: dict, device_id: str) -> BiometricReading:
        """
        Handle a raw sensor reading MQTT message (topic: tremo/sensors/{device_id}).

        Validates the sensor payload (aX, aY, aZ, gX, gY, gZ, battery_level),
        resolves the device-patient pairing, and creates a BiometricReading record.

        Flex fields (flex_1–flex_5) and magnetometer fields (mX, mY, mZ) are
        silently ignored if present in the payload — they are never read or stored.

        Args:
            payload: Parsed MQTT JSON payload
            device_id: Device ID extracted from topic (tremo/sensors/{device_id})

        Returns:
            Created BiometricReading instance

        Raises:
            ValidationError: If the payload fails schema validation
            Exception: If the database write fails
        """
        # Validate raw reading schema (flex fields silently ignored)
        validate_biometric_reading_message(payload)

        # Validate device pairing
        device, patient = validate_device_pairing(device_id)
        if not device or not patient:
            logger.warning(f"Device {device_id} not paired to patient. Rejecting reading.")
            return None

        logger.info(f"Validated device for reading: {device_id} (patient {patient.id})")

        # Extract and log battery_level (not stored — requires separate migration)
        battery_level = payload.get('battery_level')
        if battery_level is not None:
            logger.debug(f"Device {device_id} battery level: {battery_level:.1f}%")

        # Parse timestamp
        reading_timestamp = timezone.datetime.fromisoformat(
            payload['timestamp'].replace('Z', '+00:00')
        )

        # Create BiometricReading with exactly the six sensor fields.
        # No flex fields (flex_1-flex_5) are passed — they are not read from payload.
        biometric_reading = BiometricReading.objects.create(
            patient=patient,
            timestamp=reading_timestamp,
            aX=payload['aX'],
            aY=payload['aY'],
            aZ=payload['aZ'],
            gX=payload['gX'],
            gY=payload['gY'],
            gZ=payload['gZ'],
        )

        logger.info(f"Stored BiometricReading: id={biometric_reading.id} for patient {patient.id}")

        # Broadcast raw reading to WebSocket clients (Feature 034: Live Tremor Monitor)
        if biometric_reading:
            self._broadcast_reading_to_websocket(biometric_reading, device, patient)

        # Pass the reading through the tremor filter+FFT pipeline (non-fatal)
        if biometric_reading:
            try:
                self.tremor_service.process(biometric_reading)
            except Exception as e:
                logger.error(f"Tremor filter pipeline error: {e}", exc_info=True)

        return biometric_reading

    def _broadcast_reading_to_websocket(self, reading, device: Device, patient) -> None:
        """Broadcast a raw BiometricReading to WebSocket clients via Django Channels.

        Sends a 'biometric_reading' message to the patient's channel group so the
        Live Tremor Monitor frontend (Feature 034) can update its amplitude chart
        and raw sensor values panel at the full 100 Hz reading rate.

        Args:
            reading: BiometricReading instance just stored to the database.
            device: Paired Device instance (provides serial_number).
            patient: Patient instance (provides patient.id for the channel group).
        """
        try:
            group_name = f'patient_{patient.id}_tremor_data'
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'biometric_reading',
                    'message': {
                        'type': 'biometric_reading',
                        'patient_id': patient.id,
                        'device_serial': device.serial_number,
                        'timestamp': reading.timestamp.isoformat(),
                        'aX': float(reading.aX),
                        'aY': float(reading.aY),
                        'aZ': float(reading.aZ),
                        'gX': float(reading.gX),
                        'gY': float(reading.gY),
                        'gZ': float(reading.gZ),
                    },
                },
            )
            logger.debug(
                "biometric_reading broadcast to group %s for reading id=%s",
                group_name, reading.id,
            )
        except Exception as e:
            logger.error(
                "biometric_reading WebSocket broadcast failed for patient %s: %s",
                patient.id, e, exc_info=True,
            )

    def _store_to_database(self, payload: dict, device: Device, patient, prediction: Optional[dict] = None, ml_predicted_at: Optional[timezone.datetime] = None) -> BiometricSession:
        """
        Store sensor data to database as BiometricSession.

        Args:
            payload: MQTT message payload
            device: Device instance
            patient: Patient instance
            prediction: ML prediction dict (severity, confidence) or None
            ml_predicted_at: Timestamp when prediction was generated or None

        Returns:
            Created BiometricSession instance

        Raises:
            Exception: If database write fails
        """
        try:
            # Parse timestamp
            session_start = timezone.datetime.fromisoformat(
                payload['timestamp'].replace('Z', '+00:00')
            )

            # Calculate session duration
            session_duration_ms = payload['session_duration']
            session_duration = timedelta(milliseconds=session_duration_ms)

            # Create BiometricSession
            biometric_session = BiometricSession.objects.create(
                patient=patient,
                device=device,
                session_start=session_start,
                session_duration=session_duration,
                sensor_data={
                    'tremor_intensity': payload['tremor_intensity'],
                    'frequency': payload['frequency'],
                    'timestamps': payload['timestamps'],
                },
                ml_prediction=prediction,
                ml_predicted_at=ml_predicted_at,
                received_via_mqtt=True
            )

            logger.debug(f"Created BiometricSession id={biometric_session.id} for patient {patient.id}")
            return biometric_session

        except Exception as e:
            logger.error(f"Database write failed: {e}", exc_info=True)

            # Retry once (T024)
            logger.info("Retrying database write once...")
            try:
                biometric_session = BiometricSession.objects.create(
                    patient=patient,
                    device=device,
                    session_start=session_start,
                    session_duration=session_duration,
                    sensor_data={
                        'tremor_intensity': payload['tremor_intensity'],
                        'frequency': payload['frequency'],
                        'timestamps': payload['timestamps'],
                    },
                    ml_prediction=prediction,
                    ml_predicted_at=ml_predicted_at,
                    received_via_mqtt=True
                )
                logger.info(f"Database write succeeded on retry: id={biometric_session.id}")
                return biometric_session
            except Exception as retry_error:
                logger.error(f"Database write failed on retry. Discarding message: {retry_error}")
                raise

    def _broadcast_to_websocket(self, payload: dict, patient, device: Device, biometric_session: BiometricSession, prediction: Optional[dict] = None):
        """
        Broadcast tremor data to WebSocket clients via Django Channels.

        Sends message to channel group: patient_{patient_id}_tremor_data

        Args:
            payload: MQTT message payload
            patient: Patient instance
            device: Device instance
            biometric_session: BiometricSession instance that was just created
            prediction: ML prediction dict (severity, confidence) or None

        Note:
            This method uses async_to_sync because it's called from a sync context (MQTT callback).
            The channel layer will distribute the message to all WebSocket consumers in the group.
        """
        try:
            # Construct WebSocket message (T045)
            ws_message = {
                'type': 'tremor_data',  # Maps to consumer method: tremor_data()
                'message': {
                    'type': 'tremor_data',
                    'patient_id': patient.id,
                    'device_serial': device.serial_number,
                    'timestamp': payload['timestamp'],
                    'tremor_intensity': payload['tremor_intensity'],
                    'frequency': payload['frequency'],
                    'session_duration': payload['session_duration'],
                    'prediction': prediction,  # Include ML prediction if available
                    'received_at': timezone.now().isoformat(),
                }
            }

            # Send to channel group
            group_name = f'patient_{patient.id}_tremor_data'
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                ws_message
            )

            logger.debug(f"Broadcast tremor data to WebSocket group: {group_name}")

        except Exception as e:
            logger.error(f"Failed to broadcast to WebSocket: {e}", exc_info=True)
            # Don't raise - broadcasting failure shouldn't block MQTT processing

    # -------------------------------------------------------------------------
    # CMG PID handlers (Feature 029)
    # -------------------------------------------------------------------------

    def _handle_pid_status(self, payload: dict, serial_number: str) -> None:
        """
        Handle a PID status MQTT message (topic: devices/{serial}/pid_status).

        Responsibilities:
        - If mode is 'fault' or 'interrupted', mark any active SuppressionSession
          as interrupted and publish pid_mode='disabled'.
        - Broadcast the payload to the patient's WebSocket channel group.
        - SuppressionMetric storage at 1 Hz is handled in this method (T025 extends this).

        Args:
            payload: Parsed MQTT JSON payload from device
            serial_number: Device serial number extracted from topic
        """
        device, patient = validate_device_pairing(serial_number)
        if not device or not patient:
            logger.warning(f"PID status: device {serial_number} not paired. Rejecting.")
            return

        # Auto-interrupt session if device reports fault/interrupted mode
        mode = payload.get('mode')
        if mode in ('fault', 'interrupted'):
            try:
                from cmg.models import SuppressionSession
                active_session = SuppressionSession.objects.filter(
                    device=device, status='active'
                ).first()
                if active_session:
                    active_session.status = 'interrupted'
                    active_session.ended_at = timezone.now()
                    active_session.save(update_fields=['status', 'ended_at'])
                    # Clean up sample counter for this session
                    counter_key = f"{serial_number}:{active_session.id}"
                    self._pid_sample_counters.pop(counter_key, None)
                    logger.warning(
                        f"SuppressionSession id={active_session.id} marked interrupted "
                        f"due to pid_status mode='{mode}' from device {serial_number}"
                    )
                    self.publish_pid_mode(serial_number, 'disabled')
            except Exception as e:
                logger.error(
                    f"Failed to mark session interrupted for device {serial_number}: {e}",
                    exc_info=True,
                )

        # Broadcast pid_status to WebSocket (non-fatal)
        group_name = f'patient_{patient.id}_tremor_data'
        try:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'pid_status',
                    'message': {
                        'type': 'pid_status',
                        'device_serial': device.serial_number,
                        'patient_id': patient.id,
                        **payload,
                    },
                },
            )
            logger.debug(f"pid_status broadcast to group: {group_name}")
        except Exception as e:
            logger.error(
                f"pid_status WebSocket broadcast failed for patient {patient.id}: {e}",
                exc_info=True,
            )

        # SuppressionMetric storage at 1 Hz and suppression_metric broadcast (T025)
        session_id = payload.get('session_id')
        raw_amplitude = payload.get('raw_amplitude_deg')
        residual_amplitude = payload.get('residual_amplitude_deg')
        ts_str = payload.get('timestamp')

        if session_id is not None and raw_amplitude is not None and residual_amplitude is not None:
            # Downsample to 1 Hz: store every 10th message per session
            try:
                counter_key = f"{serial_number}:{session_id}"
                count = self._pid_sample_counters.get(counter_key, 0) + 1
                self._pid_sample_counters[counter_key] = count

                if count % 10 == 0:
                    from cmg.models import SuppressionMetric
                    device_timestamp = timezone.now()
                    if ts_str:
                        try:
                            device_timestamp = timezone.datetime.fromisoformat(
                                ts_str.replace('Z', '+00:00')
                            )
                        except (ValueError, AttributeError):
                            pass

                    SuppressionMetric.objects.create(
                        session_id=session_id,
                        device=device,
                        device_timestamp=device_timestamp,
                        raw_amplitude_deg=float(raw_amplitude),
                        residual_amplitude_deg=float(residual_amplitude),
                    )
                    logger.debug(
                        f"SuppressionMetric stored for session {session_id} "
                        f"(counter={count}, device={serial_number})"
                    )
            except Exception as e:
                logger.error(
                    f"SuppressionMetric storage failed for session {session_id}: {e}",
                    exc_info=True,
                )

            # Always broadcast suppression_metric for live chart (regardless of storage sampling)
            try:
                async_to_sync(self.channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'suppression_metric',
                        'message': {
                            'type': 'suppression_metric',
                            'session_id': session_id,
                            'raw_amplitude_deg': raw_amplitude,
                            'residual_amplitude_deg': residual_amplitude,
                            'timestamp': ts_str,
                        },
                    },
                )
                logger.debug(f"suppression_metric broadcast for session {session_id}")
            except Exception as e:
                logger.error(
                    f"suppression_metric WebSocket broadcast failed for session {session_id}: {e}",
                    exc_info=True,
                )

    # -------------------------------------------------------------------------
    # CMG Motor handlers (Feature 027)
    # -------------------------------------------------------------------------

    def _handle_cmg_telemetry(self, payload: dict, serial_number: str) -> None:
        """
        Handle a CMG motor telemetry MQTT message (topic: devices/{serial}/cmg_telemetry).

        Validates device pairing, creates a MotorTelemetry row, then broadcasts
        a cmg_telemetry message to the patient's WebSocket channel group.

        Args:
            payload: Parsed MQTT JSON payload with keys:
                     timestamp, rpm, current_a, status, fault_type (nullable)
            serial_number: Device serial number extracted from topic
        """
        device, patient = validate_device_pairing(serial_number)
        if not device or not patient:
            logger.warning(f"CMG telemetry: device {serial_number} not paired. Rejecting.")
            return

        try:
            ts = timezone.datetime.fromisoformat(
                payload['timestamp'].replace('Z', '+00:00')
            )
            from cmg.models import MotorTelemetry
            telemetry = MotorTelemetry.objects.create(
                device=device,
                patient=patient,
                timestamp=ts,
                rpm=int(payload['rpm']),
                current_a=float(payload['current_a']),
                status=payload['status'],
                fault_type=payload.get('fault_type'),
            )
            logger.info(
                f"Stored MotorTelemetry id={telemetry.id} "
                f"for patient {patient.id} (status={telemetry.status}, rpm={telemetry.rpm})"
            )
        except Exception as e:
            logger.error(f"CMG telemetry DB write failed for device {serial_number}: {e}", exc_info=True)
            return

        # Broadcast to WebSocket (non-fatal)
        try:
            group_name = f'patient_{patient.id}_tremor_data'
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'cmg_telemetry',
                    'message': {
                        'type': 'cmg_telemetry',
                        'device_serial': device.serial_number,
                        'patient_id': patient.id,
                        'timestamp': payload['timestamp'],
                        'rpm': telemetry.rpm,
                        'current_a': telemetry.current_a,
                        'status': telemetry.status,
                        'fault_type': telemetry.fault_type,
                    },
                },
            )
            logger.debug(f"CMG telemetry broadcast to group: {group_name}")
        except Exception as e:
            logger.error(f"CMG telemetry WebSocket broadcast failed for patient {patient.id}: {e}", exc_info=True)

    def _handle_cmg_fault(self, payload: dict, serial_number: str) -> None:
        """
        Handle a CMG fault event MQTT message (topic: devices/{serial}/cmg_fault).

        Validates device pairing, creates a MotorFaultEvent row (acknowledged=False),
        then broadcasts a cmg_fault message to the patient's WebSocket channel group.

        Args:
            payload: Parsed MQTT JSON payload with keys:
                     timestamp, fault_type, rpm_at_fault (nullable), current_at_fault (nullable)
            serial_number: Device serial number extracted from topic
        """
        device, patient = validate_device_pairing(serial_number)
        if not device or not patient:
            logger.warning(f"CMG fault: device {serial_number} not paired. Rejecting.")
            return

        try:
            occurred_at = timezone.datetime.fromisoformat(
                payload['timestamp'].replace('Z', '+00:00')
            )
            from cmg.models import MotorFaultEvent
            fault = MotorFaultEvent.objects.create(
                device=device,
                patient=patient,
                occurred_at=occurred_at,
                fault_type=payload['fault_type'],
                rpm_at_fault=payload.get('rpm_at_fault'),
                current_at_fault=payload.get('current_at_fault'),
            )
            logger.warning(
                f"Stored MotorFaultEvent id={fault.id} "
                f"type={fault.fault_type} for patient {patient.id}"
            )
        except Exception as e:
            logger.error(f"CMG fault DB write failed for device {serial_number}: {e}", exc_info=True)
            return

        # Broadcast to WebSocket (non-fatal)
        try:
            group_name = f'patient_{patient.id}_tremor_data'
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'cmg_fault',
                    'message': {
                        'type': 'cmg_fault',
                        'fault_event_id': fault.id,
                        'device_serial': device.serial_number,
                        'patient_id': patient.id,
                        'occurred_at': payload['timestamp'],
                        'fault_type': fault.fault_type,
                        'rpm_at_fault': fault.rpm_at_fault,
                        'current_at_fault': fault.current_at_fault,
                    },
                },
            )
            logger.debug(f"CMG fault broadcast to group: {group_name}")
        except Exception as e:
            logger.error(f"CMG fault WebSocket broadcast failed for patient {patient.id}: {e}", exc_info=True)

    def _handle_servo_state(self, payload: dict, serial_number: str) -> None:
        """
        Handle a gimbal servo state MQTT message (topic: devices/{serial}/servo_state).

        Upserts the latest-state-only GimbalState record for the device, then
        broadcasts a servo_state message to the patient's WebSocket channel group.

        Args:
            payload: Parsed MQTT JSON payload with keys:
                     timestamp, pitch_deg, roll_deg, pitch_status, roll_status
            serial_number: Device serial number extracted from topic
        """
        device, patient = validate_device_pairing(serial_number)
        if not device or not patient:
            logger.warning(f"Servo state: device {serial_number} not paired. Rejecting.")
            return

        try:
            device_timestamp = timezone.datetime.fromisoformat(
                payload['timestamp'].replace('Z', '+00:00')
            )
            from cmg.models import GimbalState
            GimbalState.objects.update_or_create(
                device=device,
                defaults={
                    'pitch_deg': float(payload['pitch_deg']),
                    'roll_deg': float(payload['roll_deg']),
                    'pitch_status': payload['pitch_status'],
                    'roll_status': payload['roll_status'],
                    'device_timestamp': device_timestamp,
                },
            )
            logger.debug(
                f"GimbalState updated for device {serial_number} "
                f"(pitch={payload['pitch_deg']}, roll={payload['roll_deg']})"
            )
        except Exception as e:
            logger.error(f"Servo state DB write failed for device {serial_number}: {e}", exc_info=True)
            return

        # Broadcast to WebSocket (non-fatal)
        try:
            group_name = f'patient_{patient.id}_tremor_data'
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'servo_state',
                    'message': {
                        'type': 'servo_state',
                        'device_serial': device.serial_number,
                        'patient_id': patient.id,
                        'pitch_deg': float(payload['pitch_deg']),
                        'roll_deg': float(payload['roll_deg']),
                        'pitch_status': payload['pitch_status'],
                        'roll_status': payload['roll_status'],
                        'device_timestamp': payload['timestamp'],
                    },
                },
            )
            logger.debug(f"Servo state broadcast to group: {group_name}")
        except Exception as e:
            logger.error(f"Servo state WebSocket broadcast failed for patient {patient.id}: {e}", exc_info=True)

    def publish_cmg_command(self, serial_number: str, command: str) -> bool:
        """
        Publish a motor control command to a glove device via MQTT (QoS 1).

        Thread-safe. Can be called from any Django request thread.

        Each command payload includes a unique command_id UUID to allow the
        glove firmware to deduplicate re-deliveries (QoS 1 can deliver twice).

        Args:
            serial_number: Device serial number (MQTT topic segment)
            command: One of 'start', 'stop', 'emergency_stop'

        Returns:
            True if message was enqueued successfully, False otherwise.
        """
        if not self.is_connected:
            logger.error(
                f"publish_cmg_command: MQTT broker not connected. "
                f"Command '{command}' for device {serial_number} not sent."
            )
            return False

        topic = f"devices/{serial_number}/cmg_command"
        payload = json.dumps({
            'command': command,
            'command_id': str(uuid.uuid4()),
            'issued_at': timezone.now().isoformat(),
        })

        with self._publish_lock:
            result = self.client.publish(topic, payload, qos=1)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"publish_cmg_command: publish failed for device {serial_number} "
                f"(rc={result.rc})"
            )
            return False

        logger.info(f"CMG command '{command}' enqueued for device {serial_number} (mid={result.mid})")
        return True

    def publish_servo_command(self, serial_number: str, command_data: dict) -> bool:
        """
        Publish a gimbal servo position command to a glove device via MQTT (QoS 1).

        Thread-safe. Can be called from any Django request thread.

        The payload includes all calibration bounds so the device can validate
        locally. command_id UUID enables QoS-1 deduplication on the device.

        Args:
            serial_number: Device serial number (MQTT topic segment)
            command_data:  Dict with keys: command, command_id, issued_at,
                           rate_limit_deg_per_sec, pitch_min_deg, pitch_max_deg,
                           roll_min_deg, roll_max_deg, and optionally
                           pitch_deg / roll_deg for set_position commands.

        Returns:
            True if message was enqueued successfully, False otherwise.
        """
        if not self.is_connected:
            logger.error(
                f"publish_servo_command: MQTT broker not connected. "
                f"Servo command for device {serial_number} not sent."
            )
            return False

        topic = f"devices/{serial_number}/servo_command"
        payload = json.dumps(command_data)

        with self._publish_lock:
            result = self.client.publish(topic, payload, qos=1, retain=False)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"publish_servo_command: publish failed for device {serial_number} "
                f"(rc={result.rc})"
            )
            return False

        logger.info(
            f"Servo command '{command_data.get('command')}' enqueued for device "
            f"{serial_number} (mid={result.mid})"
        )
        return True

    def publish_servo_config(self, serial_number: str, calibration) -> bool:
        """
        Publish retained gimbal calibration config to a device via MQTT (QoS 1).

        The retained flag ensures the glove receives the current configuration
        immediately after reconnecting, without waiting for the next PUT.

        Args:
            serial_number: Device serial number (MQTT topic segment)
            calibration:   GimbalCalibration model instance

        Returns:
            True if message was enqueued successfully, False otherwise.
        """
        if not self.is_connected:
            logger.error(
                f"publish_servo_config: MQTT broker not connected. "
                f"Config for device {serial_number} not sent."
            )
            return False

        topic = f"devices/{serial_number}/servo_config"
        payload = json.dumps({
            'pitch_center_deg': calibration.pitch_center_deg,
            'roll_center_deg': calibration.roll_center_deg,
            'pitch_min_deg': calibration.pitch_min_deg,
            'pitch_max_deg': calibration.pitch_max_deg,
            'roll_min_deg': calibration.roll_min_deg,
            'roll_max_deg': calibration.roll_max_deg,
            'rate_limit_deg_per_sec': calibration.rate_limit_deg_per_sec,
            'config_version': calibration.config_version,
            'updated_at': calibration.updated_at.isoformat(),
        })

        with self._publish_lock:
            result = self.client.publish(topic, payload, qos=1, retain=True)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"publish_servo_config: publish failed for device {serial_number} "
                f"(rc={result.rc})"
            )
            return False

        logger.info(
            f"Servo config published (retained) for device {serial_number} "
            f"(version={calibration.config_version}, mid={result.mid})"
        )
        return True

    def publish_pid_config(self, serial_number: str, pid_config) -> bool:
        """
        Publish retained PID gain configuration to a device via MQTT (QoS 1).

        The retained flag ensures the glove receives the current PID gains
        immediately after reconnecting, without waiting for the next PUT.

        Args:
            serial_number: Device serial number (MQTT topic segment)
            pid_config:    PIDConfig model instance

        Returns:
            True if message was enqueued successfully, False otherwise.
        """
        if not self.is_connected:
            logger.error(
                f"publish_pid_config: MQTT broker not connected. "
                f"Config for device {serial_number} not sent."
            )
            return False

        topic = f"devices/{serial_number}/pid_config"
        payload = json.dumps({
            'kp_pitch': pid_config.kp_pitch,
            'ki_pitch': pid_config.ki_pitch,
            'kd_pitch': pid_config.kd_pitch,
            'kp_roll': pid_config.kp_roll,
            'ki_roll': pid_config.ki_roll,
            'kd_roll': pid_config.kd_roll,
            'config_version': pid_config.config_version,
            'updated_at': pid_config.updated_at.isoformat(),
        })

        with self._publish_lock:
            result = self.client.publish(topic, payload, qos=1, retain=True)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"publish_pid_config: publish failed for device {serial_number} "
                f"(rc={result.rc})"
            )
            return False

        logger.info(
            f"PID config published (retained) for device {serial_number} "
            f"(version={pid_config.config_version}, mid={result.mid})"
        )
        return True

    def publish_pid_mode(self, serial_number: str, mode: str) -> bool:
        """
        Publish retained PID suppression mode command to a device via MQTT (QoS 1).

        The retained flag ensures an offline device receives the mode command
        immediately upon reconnecting.

        Args:
            serial_number: Device serial number (MQTT topic segment)
            mode:          'enabled' or 'disabled'

        Returns:
            True if message was enqueued successfully, False otherwise.
        """
        if not self.is_connected:
            logger.error(
                f"publish_pid_mode: MQTT broker not connected. "
                f"Mode '{mode}' for device {serial_number} not sent."
            )
            return False

        topic = f"devices/{serial_number}/pid_mode"
        payload = json.dumps({
            'mode': mode,
            'command_id': str(uuid.uuid4()),
            'issued_at': timezone.now().isoformat(),
        })

        with self._publish_lock:
            result = self.client.publish(topic, payload, qos=1, retain=True)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"publish_pid_mode: publish failed for device {serial_number} "
                f"(rc={result.rc})"
            )
            return False

        logger.info(f"PID mode '{mode}' published (retained) for device {serial_number} (mid={result.mid})")
        return True
