"""
API views for device management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from authentication.permissions import IsDoctor
from .models import Device
from .serializers import (
    DeviceListSerializer,
    DeviceDetailSerializer,
    DeviceCreateSerializer,
    DevicePairingSerializer,
    DeviceStatusSerializer
)


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing devices.

    Provides:
    - list: GET /api/devices/
    - create: POST /api/devices/
    - retrieve: GET /api/devices/{id}/
    - pair: POST /api/devices/{id}/pair/
    - unpair: POST /api/devices/{id}/unpair/
    - status: PUT /api/devices/{id}/status/
    """

    permission_classes = [IsAuthenticated, IsDoctor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        """Return all devices (doctors can see all registered devices)."""
        return Device.objects.select_related('patient', 'registered_by').all()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DeviceListSerializer
        elif self.action == 'retrieve':
            return DeviceDetailSerializer
        elif self.action == 'create':
            return DeviceCreateSerializer
        elif self.action == 'pair':
            return DevicePairingSerializer
        elif self.action == 'status':
            return DeviceStatusSerializer
        return DeviceDetailSerializer

    def create(self, request, *args, **kwargs):
        """Register a new device."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        device = serializer.save()

        # Return detailed response
        response_serializer = DeviceDetailSerializer(device)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='pair')
    def pair(self, request, pk=None):
        """
        Pair device to a patient.

        POST /api/devices/{id}/pair/
        Body: { "patient_id": 123 }

        Returns:
        - 200: Pairing successful
        - 400: Invalid patient_id or pairing error
        - 404: Device not found
        """
        device = self.get_object()
        previous_patient_id = device.patient_id if device.patient else None

        serializer = DevicePairingSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Update device pairing
        from patients.models import Patient
        patient = Patient.objects.get(id=serializer.validated_data['patient_id'])
        device.patient = patient
        device.save()

        response_data = {
            'message': 'Device paired successfully',
            'device': DeviceDetailSerializer(device).data
        }

        if previous_patient_id:
            response_data['previous_patient_id'] = previous_patient_id
            response_data['message'] = 'Device re-paired successfully'

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unpair')
    def unpair(self, request, pk=None):
        """
        Unpair device from patient.

        POST /api/devices/{id}/unpair/

        Returns:
        - 200: Unpairing successful
        - 404: Device not found
        """
        device = self.get_object()

        if not device.patient:
            return Response(
                {'message': 'Device is not paired to any patient'},
                status=status.HTTP_400_BAD_REQUEST
            )

        previous_patient = device.patient
        device.patient = None
        device.save()

        return Response(
            {
                'message': 'Device unpaired successfully',
                'previous_patient': {
                    'id': previous_patient.id,
                    'full_name': previous_patient.full_name
                }
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['put'], url_path='status')
    def status_update(self, request, pk=None):
        """
        Update device online/offline status.

        PUT /api/devices/{id}/status/
        Body: { "status": "online" | "offline", "last_seen": "2024-01-15T10:30:00Z" (optional) }

        Returns:
        - 200: Status updated
        - 400: Invalid status value
        - 404: Device not found
        """
        device = self.get_object()

        serializer = DeviceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device.status = serializer.validated_data['status']
        device.last_seen = serializer.validated_data.get('last_seen', timezone.now())
        device.save()

        return Response(
            {
                'message': 'Device status updated',
                'device': DeviceDetailSerializer(device).data
            },
            status=status.HTTP_200_OK
        )
