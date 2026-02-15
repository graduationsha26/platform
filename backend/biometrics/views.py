"""
API views for biometric data management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import datetime

from authentication.permissions import IsOwnerOrDoctor
from .models import BiometricSession
from .serializers import (
    BiometricSessionListSerializer,
    BiometricSessionDetailSerializer,
    BiometricSessionCreateSerializer,
    BiometricAggregationSerializer
)
from .aggregation import aggregate_biometric_data


class BiometricSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing biometric sessions.

    Provides:
    - list: GET /api/biometric-sessions/
    - create: POST /api/biometric-sessions/
    - retrieve: GET /api/biometric-sessions/{id}/
    - aggregate: GET /api/biometric-sessions/aggregate/
    """

    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'device']

    def get_queryset(self):
        """
        Filter sessions by user access.

        Patients see only their own sessions.
        Doctors see sessions for patients they have access to.
        """
        user = self.request.user

        if user.role == 'patient':
            # Patients see only their own sessions
            try:
                patient_profile = user.patient_profile
                return BiometricSession.objects.filter(
                    patient=patient_profile
                ).select_related('patient', 'device')
            except:
                return BiometricSession.objects.none()

        elif user.role == 'doctor':
            # Doctors see sessions for patients they created or are assigned to
            from patients.models import Patient
            accessible_patients = Patient.objects.filter(
                Q(created_by=user) | Q(doctor_assignments__doctor=user)
            ).distinct()

            return BiometricSession.objects.filter(
                patient__in=accessible_patients
            ).select_related('patient', 'device')

        return BiometricSession.objects.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BiometricSessionListSerializer
        elif self.action == 'retrieve':
            return BiometricSessionDetailSerializer
        elif self.action == 'create':
            return BiometricSessionCreateSerializer
        elif self.action == 'aggregate':
            return BiometricAggregationSerializer
        return BiometricSessionDetailSerializer

    def filter_queryset_by_date_range(self, queryset):
        """Apply date range filtering from query params."""
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(session_start__gte=start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(session_start__lte=end_dt)
            except ValueError:
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        """
        List biometric sessions with date range filtering.

        Query params:
        - patient: Filter by patient ID
        - device: Filter by device ID
        - start_date: Filter sessions after this date (ISO format)
        - end_date: Filter sessions before this date (ISO format)
        """
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)
        queryset = self.filter_queryset_by_date_range(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new biometric session.

        Validates device-patient pairing before accepting sensor data.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()

        # Return detailed response
        response_serializer = BiometricSessionDetailSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='aggregate')
    def aggregate(self, request):
        """
        Get aggregated biometric metrics.

        Query params:
        - patient_id: Required - Patient ID to aggregate
        - start_date: Optional - Start date (ISO format)
        - end_date: Optional - End date (ISO format)

        Returns:
        - session_count: Total number of sessions
        - total_duration_seconds: Sum of all session durations
        - average_tremor_intensity: Mean tremor intensity across all sessions
        - min_tremor_intensity: Minimum tremor intensity value
        - max_tremor_intensity: Maximum tremor intensity value

        Example: GET /api/biometric-sessions/aggregate/?patient_id=1&start_date=2024-01-01&end_date=2024-12-31
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            patient_id = int(patient_id)
        except ValueError:
            return Response(
                {'error': 'patient_id must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has access to this patient
        user = request.user
        if user.role == 'patient':
            try:
                if user.patient_profile.id != patient_id:
                    return Response(
                        {'error': 'You can only access your own data'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except:
                return Response(
                    {'error': 'Patient profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif user.role == 'doctor':
            from patients.models import Patient
            accessible = Patient.objects.filter(
                Q(id=patient_id) & (Q(created_by=user) | Q(doctor_assignments__doctor=user))
            ).exists()
            if not accessible:
                return Response(
                    {'error': 'You do not have access to this patient'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Parse date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Compute aggregations
        results = aggregate_biometric_data(patient_id, start_dt, end_dt)

        serializer = BiometricAggregationSerializer(results)
        return Response(serializer.data, status=status.HTTP_200_OK)
