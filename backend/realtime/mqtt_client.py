"""
MQTT client for receiving sensor data from TremoAI glove devices.

This module implements a persistent MQTT connection that subscribes to
device data topics and processes incoming sensor measurements.
"""
import json
import logging
import time
from datetime import timedelta
from typing import Optional

import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from decouple import config
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from devices.models import Device
from biometrics.models import BiometricSession
from realtime.validators import validate_mqtt_message, validate_device_pairing

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

        # Initialize MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # Reconnection tracking
        self.reconnect_count = 0
        self.max_reconnect_attempts = 10
        self.max_reconnect_delay = 60  # seconds

        # Channel layer for WebSocket broadcasting
        self.channel_layer = get_channel_layer()

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

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback for when connection is established.

        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            rc: Connection result code
        """
        if rc == 0:
            logger.info(f"Connected to MQTT broker successfully (code {rc})")

            # Subscribe to all device data topics using wildcard
            topic = "devices/+/data"
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

            # Reset reconnection counter on successful connection
            self.reconnect_count = 0
        else:
            logger.error(f"Failed to connect to MQTT broker (code {rc})")

    def on_disconnect(self, client, userdata, rc):
        """
        Callback for when connection is lost.

        Implements exponential backoff reconnection strategy.

        Args:
            client: MQTT client instance
            userdata: User data
            rc: Disconnect result code
        """
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

            # Validate message schema
            validate_mqtt_message(payload)

            # Extract serial number from topic (devices/SERIAL/data)
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 3 or topic_parts[0] != 'devices' or topic_parts[2] != 'data':
                logger.error(f"Invalid topic format: {msg.topic}")
                return

            serial_number = topic_parts[1]

            # Validate device pairing
            device, patient = validate_device_pairing(serial_number)
            if not device or not patient:
                logger.warning(f"Device {serial_number} not paired to patient. Rejecting message.")
                return

            logger.info(f"Validated device: {serial_number} (paired to patient {patient.id})")

            # Store to database (T019)
            biometric_session = self._store_to_database(payload, device, patient)
            logger.info(f"Stored BiometricSession: id={biometric_session.id}")

            # Broadcast to WebSocket clients via channel layer (T034 - will be implemented in Phase 4)
            # self._broadcast_to_websocket(payload, patient.id, biometric_session)

        except ValidationError as e:
            logger.warning(f"Validation error for MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)

    def _store_to_database(self, payload: dict, device: Device, patient) -> BiometricSession:
        """
        Store sensor data to database as BiometricSession.

        Args:
            payload: MQTT message payload
            device: Device instance
            patient: Patient instance

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
                    received_via_mqtt=True
                )
                logger.info(f"Database write succeeded on retry: id={biometric_session.id}")
                return biometric_session
            except Exception as retry_error:
                logger.error(f"Database write failed on retry. Discarding message: {retry_error}")
                raise
