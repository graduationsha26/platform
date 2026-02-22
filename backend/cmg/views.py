"""
API views for CMG motor telemetry, fault events, motor commands,
gimbal servo commands, calibration, and gimbal state.

Feature 027: CMG Brushless Motor & ESC Initialization
Feature 028: CMG Gimbal Servo Control
"""
import logging

from decouple import config
from django.core.exceptions import ValidationError
from django.db.models import Avg, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsOwnerOrDoctor
from devices.models import Device
from .models import (
    MotorTelemetry, MotorFaultEvent,
    GimbalCalibration, GimbalState,
    PIDConfig, SuppressionSession, SuppressionMetric,
)
from .serializers import (
    MotorTelemetrySerializer,
    MotorFaultEventSerializer,
    ServoCommandInputSerializer,
    GimbalCalibrationSerializer,
    GimbalStateSerializer,
    PIDConfigSerializer,
    SuppressionSessionSerializer,
    SuppressionMetricSerializer,
    SuppressionSessionSummarySerializer,
)

logger = logging.getLogger(__name__)


class MotorTelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for MotorTelemetry records.

    Endpoints:
    - list:   GET /api/cmg/telemetry/?device_id=<id>   (or patient_id=<id>)
    - latest: GET /api/cmg/telemetry/latest/?device_id=<id>

    Access control: doctors see data for their accessible patients only.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]
    serializer_class = MotorTelemetrySerializer

    def _get_accessible_patient_ids(self, user):
        """Return queryset of patient IDs accessible to the requesting doctor."""
        from patients.models import Patient
        return Patient.objects.filter(
            Q(created_by=user) | Q(doctor_assignments__doctor=user)
        ).distinct().values_list('id', flat=True)

    def get_queryset(self):
        """Filter telemetry by doctor access."""
        user = self.request.user
        if user.role == 'doctor':
            accessible = self._get_accessible_patient_ids(user)
            return MotorTelemetry.objects.filter(
                patient_id__in=accessible
            ).select_related('device', 'patient')
        return MotorTelemetry.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List telemetry records for a device or patient.

        Query params:
        - device_id: Filter by device (at least one of device_id/patient_id required)
        - patient_id: Filter by patient
        - limit: Max records (default 60, max 300)
        - since: ISO timestamp — return records newer than this
        """
        device_id = request.query_params.get('device_id')
        patient_id = request.query_params.get('patient_id')

        if not device_id and not patient_id:
            return Response(
                {'error': 'At least one of device_id or patient_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()

        if device_id:
            try:
                queryset = queryset.filter(device_id=int(device_id))
            except ValueError:
                return Response(
                    {'error': 'device_id must be an integer'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if patient_id:
            try:
                queryset = queryset.filter(patient_id=int(patient_id))
            except ValueError:
                return Response(
                    {'error': 'patient_id must be an integer'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        since = request.query_params.get('since')
        if since:
            try:
                since_dt = timezone.datetime.fromisoformat(since.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=since_dt)
            except ValueError:
                return Response(
                    {'error': 'since must be a valid ISO timestamp'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            limit = int(request.query_params.get('limit', 60))
            limit = min(limit, 300)
        except ValueError:
            limit = 60

        queryset = queryset[:limit]

        serializer = self.get_serializer(queryset, many=True)
        return Response({'count': len(serializer.data), 'results': serializer.data})

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """
        Return the most recent MotorTelemetry record for a device.

        Query params:
        - device_id: Required
        """
        device_id = request.query_params.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            device_id = int(device_id)
        except ValueError:
            return Response(
                {'error': 'device_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = self.get_queryset().filter(device_id=device_id).order_by('-timestamp').first()
        if record is None:
            return Response(
                {'error': f'No telemetry found for device {device_id}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(record)
        return Response(serializer.data)


class MotorFaultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for MotorFaultEvent records with an acknowledge action.

    Endpoints:
    - list:        GET /api/cmg/faults/?device_id=<id>
    - retrieve:    GET /api/cmg/faults/{id}/
    - acknowledge: POST /api/cmg/faults/{id}/acknowledge/

    Access control: doctors see faults for their accessible patients only.
    """

    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]
    serializer_class = MotorFaultEventSerializer

    def _get_accessible_patient_ids(self, user):
        from patients.models import Patient
        return Patient.objects.filter(
            Q(created_by=user) | Q(doctor_assignments__doctor=user)
        ).distinct().values_list('id', flat=True)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'doctor':
            accessible = self._get_accessible_patient_ids(user)
            return MotorFaultEvent.objects.filter(
                patient_id__in=accessible
            ).select_related('device', 'patient', 'acknowledged_by')
        return MotorFaultEvent.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List fault events for a device or patient.

        Query params:
        - device_id: Filter by device (at least one of device_id/patient_id required)
        - patient_id: Filter by patient
        - acknowledged: 'true'/'false' to filter by acknowledgment status
        """
        device_id = request.query_params.get('device_id')
        patient_id = request.query_params.get('patient_id')

        if not device_id and not patient_id:
            return Response(
                {'error': 'At least one of device_id or patient_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()

        if device_id:
            try:
                queryset = queryset.filter(device_id=int(device_id))
            except ValueError:
                return Response({'error': 'device_id must be an integer'}, status=400)

        if patient_id:
            try:
                queryset = queryset.filter(patient_id=int(patient_id))
            except ValueError:
                return Response({'error': 'patient_id must be an integer'}, status=400)

        acknowledged_param = request.query_params.get('acknowledged')
        if acknowledged_param is not None:
            queryset = queryset.filter(acknowledged=acknowledged_param.lower() == 'true')

        serializer = self.get_serializer(queryset, many=True)
        return Response({'count': len(serializer.data), 'results': serializer.data})

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """
        Acknowledge a motor fault event.

        Idempotent: acknowledging an already-acknowledged fault returns 200.
        Only doctors can acknowledge faults.
        """
        fault = self.get_object()
        if not fault.acknowledged:
            fault.acknowledged = True
            fault.acknowledged_at = timezone.now()
            fault.acknowledged_by = request.user
            fault.save(update_fields=['acknowledged', 'acknowledged_at', 'acknowledged_by'])
            logger.info(f"MotorFaultEvent id={fault.id} acknowledged by user {request.user.id}")
        serializer = self.get_serializer(fault)
        return Response(serializer.data)


class CMGCommandView(APIView):
    """
    POST /api/cmg/commands/ — Send a motor control command to the glove.

    Publishes a command to the glove via MQTT (QoS 1) after validating that
    the requesting doctor has access to the device's patient.

    Returns 503 if the MQTT broker is not connected.
    """

    permission_classes = [IsAuthenticated]

    VALID_COMMANDS = {'start', 'stop', 'emergency_stop'}

    def post(self, request):
        device_id = request.data.get('device_id')
        command = request.data.get('command')

        if not device_id or not command:
            return Response(
                {'error': 'device_id and command are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if command not in self.VALID_COMMANDS:
            return Response(
                {'error': f'Invalid command. Must be one of: {", ".join(sorted(self.VALID_COMMANDS))}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            device = Device.objects.select_related('patient').get(id=int(device_id))
        except (Device.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': f'Device {device_id} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify doctor has access to this device's patient
        user = request.user
        if user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can issue motor commands'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if device.patient is None:
            return Response(
                {'error': 'Device is not paired to a patient'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from patients.models import Patient
        from django.db.models import Q
        accessible = Patient.objects.filter(
            Q(id=device.patient_id) & (Q(created_by=user) | Q(doctor_assignments__doctor=user))
        ).exists()
        if not accessible:
            return Response(
                {'error': 'You do not have access to this device'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Publish command via MQTT singleton
        from realtime.mqtt_client import mqtt_client_instance
        published = mqtt_client_instance.publish_cmg_command(device.serial_number, command)
        if not published:
            return Response(
                {'error': 'MQTT broker not connected. Command not sent.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'status': 'published',
            'command': command,
            'device_serial': device.serial_number,
            'published_at': timezone.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Feature 028: CMG Gimbal Servo Control
# ---------------------------------------------------------------------------

# Conservative system defaults used when no GimbalCalibration record exists.
_CALIB_DEFAULTS = {
    'pitch_center_deg': 0.0,
    'roll_center_deg': 0.0,
    'pitch_min_deg': -30.0,
    'pitch_max_deg': 30.0,
    'roll_min_deg': -20.0,
    'roll_max_deg': 20.0,
    'rate_limit_deg_per_sec': 45.0,
    'config_version': 0,
}


def _get_accessible_patient_ids(user):
    """Return queryset of patient IDs accessible to the given doctor."""
    from patients.models import Patient
    return Patient.objects.filter(
        Q(created_by=user) | Q(doctor_assignments__doctor=user)
    ).distinct().values_list('id', flat=True)


def _get_calibration_dict(device):
    """
    Return a plain dict of calibration values for the given device.

    Falls back to system defaults if no GimbalCalibration record exists.
    """
    try:
        cal = device.gimbal_calibration
        return {
            'pitch_center_deg': cal.pitch_center_deg,
            'roll_center_deg': cal.roll_center_deg,
            'pitch_min_deg': cal.pitch_min_deg,
            'pitch_max_deg': cal.pitch_max_deg,
            'roll_min_deg': cal.roll_min_deg,
            'roll_max_deg': cal.roll_max_deg,
            'rate_limit_deg_per_sec': cal.rate_limit_deg_per_sec,
            'config_version': cal.config_version,
        }
    except GimbalCalibration.DoesNotExist:
        return dict(_CALIB_DEFAULTS)


def _get_device(device_pk, user):
    """
    Return (device, None) if device exists and user has access.
    Return (None, error_response) if device not found or access denied.

    Doctors must have access to the device's patient.
    Patients must own the device.
    """
    try:
        device = Device.objects.select_related('patient').get(id=device_pk)
    except Device.DoesNotExist:
        return None, Response(
            {'error': 'Device not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if user.role == 'doctor':
        if device.patient_id is not None:
            accessible = _get_accessible_patient_ids(user)
            if device.patient_id not in accessible:
                return None, Response(
                    {'error': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
    elif user.role == 'patient':
        from patients.models import Patient
        try:
            patient = Patient.objects.get(user=user)
        except Patient.DoesNotExist:
            return None, Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if device.patient_id != patient.id:
            return None, Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        return None, Response(
            {'error': 'Access denied.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    return device, None


# ---------------------------------------------------------------------------
# Feature 029: CMG PID Controller Tuning — module-level defaults
# ---------------------------------------------------------------------------

_PID_DEFAULTS = {
    'kp_pitch': config('PID_KP_PITCH_DEFAULT', default=0.08, cast=float),
    'ki_pitch': config('PID_KI_PITCH_DEFAULT', default=0.002, cast=float),
    'kd_pitch': config('PID_KD_PITCH_DEFAULT', default=0.012, cast=float),
    'kp_roll':  config('PID_KP_ROLL_DEFAULT',  default=0.06,  cast=float),
    'ki_roll':  config('PID_KI_ROLL_DEFAULT',  default=0.001, cast=float),
    'kd_roll':  config('PID_KD_ROLL_DEFAULT',  default=0.008, cast=float),
}


class ServoCommandView(APIView):
    """
    POST /api/cmg/servo/commands/ — Issue a gimbal servo position command.

    Validates angles against per-device calibration, creates an audit record,
    and publishes the command to the device via MQTT (QoS 1).

    Returns 503 if the MQTT broker is not connected.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Doctor-only endpoint
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can issue servo commands'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ServoCommandInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        device_id = data['device_id']
        command = data['command']
        pitch_deg = data.get('pitch_deg')
        roll_deg = data.get('roll_deg')

        # Resolve device
        try:
            device = Device.objects.select_related('patient', 'gimbal_calibration').get(id=device_id)
        except Device.DoesNotExist:
            return Response(
                {'error': f'Device {device_id} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if device.patient is None:
            return Response(
                {'error': 'Device is not paired to a patient'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify doctor has access to this device's patient
        accessible = _get_accessible_patient_ids(request.user)
        if device.patient_id not in accessible:
            return Response(
                {'error': 'You do not have access to this device'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Load calibration (or system defaults)
        cal = _get_calibration_dict(device)

        # Validate angles against calibration bounds for set_position
        if command == 'set_position':
            from .validators import validate_angle_in_range
            try:
                if pitch_deg is not None:
                    validate_angle_in_range(
                        pitch_deg, cal['pitch_min_deg'], cal['pitch_max_deg'], 'pitch_deg'
                    )
                if roll_deg is not None:
                    validate_angle_in_range(
                        roll_deg, cal['roll_min_deg'], cal['roll_max_deg'], 'roll_deg'
                    )
            except ValidationError as exc:
                return Response(
                    {'error': exc.message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create audit record with calibration snapshot
        from .models import ServoCommand
        import uuid as _uuid
        command_id = _uuid.uuid4()
        issued_at = timezone.now()

        servo_cmd = ServoCommand.objects.create(
            device=device,
            patient=device.patient,
            issued_by=request.user,
            command_id=command_id,
            target_pitch_deg=pitch_deg,
            target_roll_deg=roll_deg,
            is_home_command=(command == 'home'),
            rate_limit_snap=cal['rate_limit_deg_per_sec'],
            pitch_min_snap=cal['pitch_min_deg'],
            pitch_max_snap=cal['pitch_max_deg'],
            roll_min_snap=cal['roll_min_deg'],
            roll_max_snap=cal['roll_max_deg'],
            status=ServoCommand.STATUS_PENDING,
        )

        # Build MQTT payload
        mqtt_payload = {
            'command': command,
            'rate_limit_deg_per_sec': cal['rate_limit_deg_per_sec'],
            'pitch_min_deg': cal['pitch_min_deg'],
            'pitch_max_deg': cal['pitch_max_deg'],
            'roll_min_deg': cal['roll_min_deg'],
            'roll_max_deg': cal['roll_max_deg'],
            'command_id': str(command_id),
            'issued_at': issued_at.isoformat(),
        }
        if command == 'set_position':
            if pitch_deg is not None:
                mqtt_payload['pitch_deg'] = pitch_deg
            if roll_deg is not None:
                mqtt_payload['roll_deg'] = roll_deg

        # Publish via MQTT singleton
        from realtime.mqtt_client import mqtt_client_instance
        published = mqtt_client_instance.publish_servo_command(device.serial_number, mqtt_payload)

        if published:
            servo_cmd.status = ServoCommand.STATUS_PUBLISHED
        else:
            servo_cmd.status = ServoCommand.STATUS_FAILED
        servo_cmd.save(update_fields=['status'])

        if not published:
            return Response(
                {'error': 'MQTT broker not connected. Command not sent.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message = 'Home command published to device' if command == 'home' else 'Command published to device'
        return Response({
            'success': True,
            'command_id': str(command_id),
            'device_id': device.id,
            'command': command,
            'target_pitch_deg': pitch_deg,
            'target_roll_deg': roll_deg,
            'message': message,
        })


class GimbalCalibrationView(APIView):
    """
    GET/PUT /api/cmg/servo/calibration/{device_pk}/ — Read or update gimbal calibration.

    GET returns actual calibration or synthetic defaults (never 404 — defaults always exist).
    PUT creates or fully replaces calibration, then publishes retained MQTT servo_config.
    Only doctors may PUT; both doctors and patients associated with the device may GET.
    """

    permission_classes = [IsAuthenticated]

    def _get_device(self, device_pk, user):
        """Return device if it exists and user has access; otherwise raise."""
        try:
            device = Device.objects.select_related('patient', 'gimbal_calibration').get(id=device_pk)
        except Device.DoesNotExist:
            return None, Response(
                {'error': 'Device not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.role == 'doctor':
            # Doctor must have access to the device's patient
            if device.patient_id is not None:
                accessible = _get_accessible_patient_ids(user)
                if device.patient_id not in accessible:
                    return None, Response(
                        {'error': 'Access denied.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        elif user.role == 'patient':
            # Patient must own the device
            from patients.models import Patient
            try:
                patient = Patient.objects.get(user=user)
            except Patient.DoesNotExist:
                return None, Response(
                    {'error': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if device.patient_id != patient.id:
                return None, Response(
                    {'error': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return None, Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return device, None

    def get(self, request, device_pk):
        device, err = self._get_device(device_pk, request.user)
        if err:
            return err

        try:
            cal = device.gimbal_calibration
            serializer = GimbalCalibrationSerializer(cal)
            return Response(serializer.data)
        except GimbalCalibration.DoesNotExist:
            # Return synthetic defaults — no record yet
            defaults = {
                'device_id': device.id,
                **{k: v for k, v in _CALIB_DEFAULTS.items() if k != 'config_version'},
                'updated_at': None,
                'updated_by_id': None,
            }
            return Response(defaults)

    def put(self, request, device_pk):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can update calibration.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        device, err = self._get_device(device_pk, request.user)
        if err:
            return err

        serializer = GimbalCalibrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            cal, created = GimbalCalibration.objects.update_or_create(
                device=device,
                defaults={
                    **data,
                    'updated_by': request.user,
                    'config_version': (
                        (device.gimbal_calibration.config_version + 1)
                        if hasattr(device, 'gimbal_calibration') and device.gimbal_calibration
                        else 1
                    ),
                },
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Push retained config to device via MQTT (non-fatal on failure)
        from realtime.mqtt_client import mqtt_client_instance
        if not mqtt_client_instance.publish_servo_config(device.serial_number, cal):
            logger.warning(
                f"GimbalCalibrationView: MQTT broker offline — servo_config not sent for device {device.id}"
            )

        response_serializer = GimbalCalibrationSerializer(cal)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=http_status)


class GimbalStateView(APIView):
    """
    GET /api/cmg/servo/state/{device_pk}/ — Read latest gimbal state.

    Returns the most recently received servo state for the device.
    Returns 404 if the device has never published a servo_state MQTT message.
    Both doctors and patients associated with the device may read this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, device_pk):
        # Resolve device with access check
        try:
            device = Device.objects.select_related('patient', 'gimbal_state').get(id=device_pk)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        if user.role == 'doctor':
            if device.patient_id is not None:
                accessible = _get_accessible_patient_ids(user)
                if device.patient_id not in accessible:
                    return Response(
                        {'error': 'Access denied.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        elif user.role == 'patient':
            from patients.models import Patient
            try:
                patient = Patient.objects.get(user=user)
            except Patient.DoesNotExist:
                return Response(
                    {'error': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if device.patient_id != patient.id:
                return Response(
                    {'error': 'Access denied.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            state = device.gimbal_state
        except GimbalState.DoesNotExist:
            return Response(
                {'error': 'No gimbal state available for this device yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = GimbalStateSerializer(state)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Feature 029: CMG PID Controller Tuning
# ---------------------------------------------------------------------------


class PIDConfigView(APIView):
    """
    GET/PUT /api/cmg/pid/config/{device_pk}/ — Read or update PID gain configuration.

    GET returns actual PID config or synthetic defaults (never 404 — defaults always exist).
    PUT creates or fully replaces PID config, then publishes retained MQTT pid_config.
    Only doctors may PUT; both doctors and patients associated with the device may GET.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, device_pk):
        device, err = _get_device(device_pk, request.user)
        if err:
            return err

        try:
            pid_cfg = device.pid_config
            serializer = PIDConfigSerializer(pid_cfg)
            return Response(serializer.data)
        except PIDConfig.DoesNotExist:
            defaults = {
                'device_id': device.id,
                **_PID_DEFAULTS,
                'config_version': 0,
                'updated_at': None,
                'updated_by_id': None,
            }
            return Response(defaults)

    def put(self, request, device_pk):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can update PID configuration.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        device, err = _get_device(device_pk, request.user)
        if err:
            return err

        serializer = PIDConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            existing_version = PIDConfig.objects.filter(device=device).values_list(
                'config_version', flat=True
            ).first()
            new_version = (existing_version + 1) if existing_version is not None else 1

            pid_cfg, created = PIDConfig.objects.update_or_create(
                device=device,
                defaults={
                    **data,
                    'updated_by': request.user,
                    'config_version': new_version,
                },
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Push retained config to device via MQTT (non-fatal on failure)
        from realtime.mqtt_client import mqtt_client_instance
        if not mqtt_client_instance.publish_pid_config(device.serial_number, pid_cfg):
            logger.warning(
                f"PIDConfigView: MQTT broker offline — pid_config not sent for device {device.id}"
            )

        response_serializer = PIDConfigSerializer(pid_cfg)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=http_status)


class SuppressionSessionView(APIView):
    """
    POST   /api/cmg/pid/sessions/           — Start suppression session (doctor only).
    GET    /api/cmg/pid/sessions/           — List sessions for a device.
    DELETE /api/cmg/pid/sessions/{pk}/      — Stop active session (doctor only).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can start suppression sessions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        device_id = request.data.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device, err = _get_device(device_id, request.user)
        if err:
            return err

        # Device must have PID configuration
        try:
            pid_cfg = device.pid_config
        except PIDConfig.DoesNotExist:
            return Response(
                {'error': 'Device has no PID configuration. Set gains before enabling suppression.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only one active session per device
        active = SuppressionSession.objects.filter(device=device, status='active').first()
        if active:
            return Response(
                {'error': f'Device already has an active suppression session (id={active.id}).'},
                status=status.HTTP_409_CONFLICT,
            )

        if device.patient is None:
            return Response(
                {'error': 'Device is not paired to a patient.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = SuppressionSession.objects.create(
            device=device,
            patient=device.patient,
            started_by=request.user,
            status='active',
            kp_pitch_snap=pid_cfg.kp_pitch,
            ki_pitch_snap=pid_cfg.ki_pitch,
            kd_pitch_snap=pid_cfg.kd_pitch,
            kp_roll_snap=pid_cfg.kp_roll,
            ki_roll_snap=pid_cfg.ki_roll,
            kd_roll_snap=pid_cfg.kd_roll,
        )

        # Publish retained mode=enabled (non-fatal on MQTT failure)
        from realtime.mqtt_client import mqtt_client_instance
        if not mqtt_client_instance.publish_pid_mode(device.serial_number, 'enabled'):
            logger.warning(
                f"SuppressionSessionView: MQTT offline — pid_mode=enabled not sent for device {device.id}"
            )

        serializer = SuppressionSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        device_id = request.query_params.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            device_id = int(device_id)
        except ValueError:
            return Response(
                {'error': 'device_id must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device, err = _get_device(device_id, request.user)
        if err:
            return err

        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
        except ValueError:
            limit = 20

        queryset = (
            SuppressionSession.objects
            .filter(device=device)
            .annotate(
                avg_raw_amplitude_deg=Avg('suppression_metrics__raw_amplitude_deg'),
                avg_residual_amplitude_deg=Avg('suppression_metrics__residual_amplitude_deg'),
            )
            .order_by('-started_at')[:limit]
        )

        results = list(queryset)
        for session in results:
            avg_raw = session.avg_raw_amplitude_deg
            avg_residual = session.avg_residual_amplitude_deg
            session.reduction_pct = (
                round((avg_raw - avg_residual) / avg_raw * 100, 1)
                if avg_raw else None
            )

        serializer = SuppressionSessionSummarySerializer(results, many=True)
        return Response({'count': len(serializer.data), 'results': serializer.data})

    def delete(self, request, session_pk):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can stop suppression sessions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            session = SuppressionSession.objects.select_related('device').get(id=session_pk)
        except SuppressionSession.DoesNotExist:
            return Response(
                {'error': f'Suppression session {session_pk} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify doctor has access to this device
        _, err = _get_device(session.device_id, request.user)
        if err:
            return err

        if session.status != 'active':
            return Response(
                {'error': f'Session is already {session.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.status = 'completed'
        session.ended_at = timezone.now()
        session.save(update_fields=['status', 'ended_at'])

        # Publish retained mode=disabled (non-fatal)
        from realtime.mqtt_client import mqtt_client_instance
        if not mqtt_client_instance.publish_pid_mode(session.device.serial_number, 'disabled'):
            logger.warning(
                f"SuppressionSessionView: MQTT offline — pid_mode=disabled not sent for session {session.id}"
            )

        serializer = SuppressionSessionSerializer(session)
        return Response(serializer.data)


class SuppressionModeView(APIView):
    """
    GET /api/cmg/pid/mode/{device_pk}/ — Current suppression mode status for a device.

    Returns whether suppression is active, and the active session details if so.
    Both doctors and patients associated with the device may read this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, device_pk):
        device, err = _get_device(device_pk, request.user)
        if err:
            return err

        active_session = SuppressionSession.objects.filter(
            device=device, status='active'
        ).first()

        return Response({
            'device_id': device.id,
            'is_active': active_session is not None,
            'session_id': active_session.id if active_session else None,
            'session_uuid': str(active_session.session_uuid) if active_session else None,
            'started_at': active_session.started_at.isoformat() if active_session else None,
        })


class SuppressionMetricView(APIView):
    """
    GET /api/cmg/pid/sessions/{session_pk}/metrics/ — Time-series + aggregate for a session.

    Returns the stored SuppressionMetric rows (downsampled to 1 Hz) along with
    aggregate statistics. Both doctors and patients associated with the device may read.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, session_pk):
        try:
            session = SuppressionSession.objects.select_related('device').get(id=session_pk)
        except SuppressionSession.DoesNotExist:
            return Response(
                {'error': f'Session {session_pk} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify access via device
        _, err = _get_device(session.device_id, request.user)
        if err:
            return err

        try:
            limit = min(int(request.query_params.get('limit', 300)), 3600)
        except ValueError:
            limit = 300

        metrics_qs = session.suppression_metrics.order_by('device_timestamp')

        since = request.query_params.get('since')
        if since:
            try:
                since_dt = timezone.datetime.fromisoformat(since.replace('Z', '+00:00'))
                metrics_qs = metrics_qs.filter(device_timestamp__gte=since_dt)
            except ValueError:
                return Response(
                    {'error': 'since must be a valid ISO timestamp'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        metrics_qs = metrics_qs[:limit]

        agg = session.suppression_metrics.aggregate(
            avg_raw=Avg('raw_amplitude_deg'),
            avg_residual=Avg('residual_amplitude_deg'),
        )
        avg_raw = agg['avg_raw']
        avg_residual = agg['avg_residual']
        reduction_pct = (
            round((avg_raw - avg_residual) / avg_raw * 100, 1) if avg_raw else None
        )

        return Response({
            'session_id': session.id,
            'session_status': session.status,
            'aggregate': {
                'avg_raw_amplitude_deg': round(avg_raw, 4) if avg_raw is not None else None,
                'avg_residual_amplitude_deg': round(avg_residual, 4) if avg_residual is not None else None,
                'reduction_pct': reduction_pct,
            },
            'metrics': SuppressionMetricSerializer(metrics_qs, many=True).data,
        })
