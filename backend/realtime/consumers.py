"""
Django Channels WebSocket consumer for real-time tremor data streaming.

This module implements a WebSocket consumer that:
- Authenticates users via JWT token
- Enforces patient access control (doctors + patient themselves)
- Joins patient-specific channel groups for broadcast
- Streams tremor data to connected clients in real-time
- Handles ping/pong for connection keepalive
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from asgiref.sync import sync_to_async

from realtime.auth import extract_jwt_from_query, validate_jwt_token
from realtime.serializers import (
    TremorDataSerializer,
    StatusSerializer,
    ErrorSerializer,
    PingPongSerializer,
)
from patients.models import Patient, DoctorPatientAssignment
from authentication.models import CustomUser

logger = logging.getLogger(__name__)


class TremorDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming real-time tremor data to authenticated clients.

    Endpoint: /ws/tremor-data/{patient_id}/
    Query params: ?token=<JWT_ACCESS_TOKEN>

    Channel group: patient_{patient_id}_tremor_data
    """

    async def connect(self):
        """
        Handle WebSocket connection request.

        Authentication flow:
        1. Extract JWT token from query parameters
        2. Validate token and get user
        3. Verify user has access to patient (is doctor or patient themselves)
        4. Join patient-specific channel group
        5. Send connected status message

        Rejection codes:
        - 4401: Invalid or missing JWT token
        - 4403: User does not have access to this patient
        """
        self.patient_id = self.scope['url_route']['kwargs']['patient_id']
        self.group_name = f'patient_{self.patient_id}_tremor_data'
        self.user = None

        try:
            # Extract JWT token from query parameters
            token = extract_jwt_from_query(self.scope)
            if not token:
                logger.warning(f"WebSocket connection rejected: No token provided for patient {self.patient_id}")
                await self.send_error('unauthorized', 'JWT token required', close_code=4401)
                await self.close(code=4401)
                return

            # Validate JWT token and get user
            self.user = await validate_jwt_token(token)
            if not self.user:
                logger.warning(f"WebSocket connection rejected: Invalid token for patient {self.patient_id}")
                await self.send_error('unauthorized', 'Invalid or expired JWT token', close_code=4401)
                await self.close(code=4401)
                return

            # Verify user has access to this patient
            has_access = await self.check_patient_access(self.user, self.patient_id)
            if not has_access:
                logger.warning(f"WebSocket connection rejected: User {self.user.id} does not have access to patient {self.patient_id}")
                await self.send_error('forbidden', 'You do not have access to this patient', close_code=4403)
                await self.close(code=4403)
                return

            # Accept WebSocket connection
            await self.accept()
            logger.info(f"WebSocket connection accepted: User {self.user.id} connected to patient {self.patient_id}")

            # Join channel group for this patient
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            logger.debug(f"User {self.user.id} joined channel group: {self.group_name}")

            # Send connected status message
            await self.send_status('connected', f'Successfully connected to patient {self.patient_id} tremor data stream')

        except Exception as e:
            logger.error(f"Error during WebSocket connection: {e}", exc_info=True)
            await self.send_error('internal_error', 'Internal server error during connection')
            await self.close(code=4500)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Cleanup:
        - Leave patient-specific channel group
        - Log disconnection
        """
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected: User left channel group {self.group_name} (code: {close_code})")

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming WebSocket messages from client.

        Supported message types:
        - ping: Respond with pong (keepalive)
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                # Respond to ping with pong
                await self.send_pong()
                logger.debug(f"Ping received from user {self.user.id if self.user else 'unknown'}, pong sent")
            else:
                logger.warning(f"Unsupported message type received: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error processing received message: {e}", exc_info=True)

    async def tremor_data(self, event):
        """
        Handle tremor_data messages from channel layer (broadcast from MQTT client).

        This method is called when MQTT client publishes to the channel group.
        It forwards the tremor data to the WebSocket client.

        Args:
            event: Dict containing tremor data message
        """
        try:
            # Extract message payload
            message = event['message']

            # Send to WebSocket client
            await self.send(text_data=json.dumps(message))
            logger.debug(f"Tremor data forwarded to user {self.user.id if self.user else 'unknown'}")

        except Exception as e:
            logger.error(f"Error forwarding tremor data: {e}", exc_info=True)

    async def biometric_reading(self, event):
        """Handle biometric_reading messages from channel layer (broadcast from MQTT client at ~100 Hz).

        Forwards raw 6-axis IMU readings (aX, aY, aZ, gX, gY, gZ) to the connected
        WebSocket client for the live tremor monitor amplitude chart and raw values panel.

        Django Channels maps the channel layer message type 'biometric_reading'
        to this method automatically.

        Args:
            event: Dict containing 'message' with the raw sensor reading payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "biometric_reading forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding biometric_reading: {e}", exc_info=True)

    async def tremor_metrics_update(self, event):
        """Handle tremor_metrics_update messages from channel layer (broadcast from TremorFilterService at ~1 Hz).

        Forwards the FFT analysis result to the connected WebSocket client.
        Django Channels maps the channel layer message type 'tremor_metrics_update'
        to this method automatically.

        Args:
            event: Dict containing 'message' with the FFT analysis result payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "tremor_metrics_update forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding tremor_metrics_update: {e}", exc_info=True)

    async def cmg_telemetry(self, event):
        """Handle cmg_telemetry messages from channel layer (broadcast from MQTT pipeline at ~1 Hz).

        Forwards live motor telemetry (RPM, current, status) to the connected WebSocket client.
        Django Channels maps the channel layer message type 'cmg_telemetry' to this method.

        Args:
            event: Dict containing 'message' with the motor telemetry payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "cmg_telemetry forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding cmg_telemetry: {e}", exc_info=True)

    async def cmg_fault(self, event):
        """Handle cmg_fault messages from channel layer (broadcast from MQTT pipeline on fault detection).

        Forwards motor fault alerts to the connected WebSocket client immediately on occurrence.
        Django Channels maps the channel layer message type 'cmg_fault' to this method.

        Args:
            event: Dict containing 'message' with the motor fault payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "cmg_fault forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding cmg_fault: {e}", exc_info=True)

    async def servo_state(self, event):
        """Handle servo_state messages from channel layer (broadcast from MQTT pipeline at device rate).

        Forwards live gimbal position and axis status to the connected WebSocket client.
        Django Channels maps the channel layer message type 'servo_state' to this method.

        Args:
            event: Dict containing 'message' with the gimbal state payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "servo_state forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding servo_state: {e}", exc_info=True)

    async def pid_status(self, event):
        """Handle pid_status messages from channel layer (broadcast from MQTT pipeline).

        Forwards PID suppression mode status to the connected WebSocket client.
        Django Channels maps the channel layer message type 'pid_status' to this method.

        Args:
            event: Dict containing 'message' with the PID status payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "pid_status forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding pid_status: {e}", exc_info=True)

    async def suppression_metric(self, event):
        """Handle suppression_metric messages from channel layer (broadcast from MQTT pipeline).

        Forwards live suppression effectiveness metrics to the connected WebSocket client.
        Django Channels maps the channel layer message type 'suppression_metric' to this method.

        Args:
            event: Dict containing 'message' with the suppression metric payload.
        """
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            logger.debug(
                "suppression_metric forwarded to user %s",
                self.user.id if self.user else 'unknown',
            )
        except Exception as e:
            logger.error(f"Error forwarding suppression_metric: {e}", exc_info=True)

    # Helper methods

    @sync_to_async
    def check_patient_access(self, user: CustomUser, patient_id: int) -> bool:
        """
        Check if user has access to patient data.

        Access rules:
        - Patient users can only access their own data
        - Doctor users can access data for patients assigned to them

        Args:
            user: Authenticated user
            patient_id: Patient ID to check access for

        Returns:
            True if user has access, False otherwise
        """
        try:
            # Check if patient exists
            patient = Patient.objects.filter(id=patient_id).first()
            if not patient:
                return False

            # If user is a patient, they can only access their own data
            if user.role == 'patient':
                # Check if user is linked to this patient
                return Patient.objects.filter(id=patient_id, user=user).exists()

            # If user is a doctor, check if patient is assigned to them
            elif user.role == 'doctor':
                return DoctorPatientAssignment.objects.filter(
                    doctor=user,
                    patient_id=patient_id
                ).exists()

            # Other roles have no access
            return False

        except Exception as e:
            logger.error(f"Error checking patient access: {e}", exc_info=True)
            return False

    async def send_status(self, status: str, message: str):
        """
        Send status message to WebSocket client.

        Args:
            status: Status code (connected, waiting, device_unpaired, error)
            message: Human-readable status message
        """
        try:
            serializer = StatusSerializer(data={
                'status': status,
                'message': message,
                'timestamp': timezone.now().isoformat(),
            })
            serializer.is_valid(raise_exception=True)

            await self.send(text_data=json.dumps(serializer.validated_data))
        except Exception as e:
            logger.error(f"Error sending status message: {e}", exc_info=True)

    async def send_error(self, error_code: str, error_message: str, close_code: int = None):
        """
        Send error message to WebSocket client.

        Args:
            error_code: Error code (unauthorized, forbidden, internal_error)
            error_message: Human-readable error message
            close_code: Optional WebSocket close code
        """
        try:
            serializer = ErrorSerializer(data={
                'error_code': error_code,
                'error_message': error_message,
                'timestamp': timezone.now().isoformat(),
            })
            serializer.is_valid(raise_exception=True)

            await self.send(text_data=json.dumps(serializer.validated_data))
        except Exception as e:
            logger.error(f"Error sending error message: {e}", exc_info=True)

    async def send_pong(self):
        """Send pong message in response to ping (keepalive)."""
        try:
            serializer = PingPongSerializer(data={
                'type': 'pong',
                'timestamp': timezone.now().isoformat(),
            })
            serializer.is_valid(raise_exception=True)

            await self.send(text_data=json.dumps(serializer.validated_data))
        except Exception as e:
            logger.error(f"Error sending pong message: {e}", exc_info=True)
