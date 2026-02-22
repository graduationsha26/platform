"""
API views for patient management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from authentication.permissions import IsDoctorOrAdmin
from .models import Patient, DoctorPatientAssignment
from .serializers import (
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
    DoctorPatientAssignmentSerializer
)
from .filters import PatientFilter
from .pagination import PatientPagination


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient profiles.

    Provides:
    - list: GET /api/patients/
    - create: POST /api/patients/
    - retrieve: GET /api/patients/{id}/
    - update: PUT /api/patients/{id}/
    - partial_update: PATCH /api/patients/{id}/
    - search: GET /api/patients/search/?name=...
    - assign_doctor: POST /api/patients/{id}/assign-doctor/
    """

    permission_classes = [IsAuthenticated, IsDoctorOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PatientFilter
    pagination_class = PatientPagination

    def get_queryset(self):
        """
        Filter patients by doctor access.

        Doctors can see:
        - Patients they created (created_by)
        - Patients assigned to them (via DoctorPatientAssignment)
        """
        user = self.request.user

        if user.role == 'admin':
            return Patient.objects.all().select_related('created_by').prefetch_related(
                'doctor_assignments__doctor', 'biometric_sessions'
            )

        if user.role != 'doctor':
            return Patient.objects.none()

        # Get patients created by this doctor OR assigned to this doctor
        return Patient.objects.filter(
            Q(created_by=user) | Q(doctor_assignments__doctor=user)
        ).distinct().select_related('created_by').prefetch_related(
            'doctor_assignments__doctor', 'biometric_sessions'
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PatientListSerializer
        elif self.action == 'retrieve':
            return PatientDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientCreateSerializer
        return PatientDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create a new patient."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()

        # Return detailed response
        response_serializer = PatientDetailSerializer(patient)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update patient (full update)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()

        # Return detailed response
        response_serializer = PatientDetailSerializer(patient)
        return Response(response_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Update patient (partial update)."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Search patients by name.

        Query params:
        - name: Search term for patient full name (case-insensitive)

        Example: GET /api/patients/search/?name=john
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PatientListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PatientListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='assign-doctor')
    def assign_doctor(self, request, pk=None):
        """
        Assign a doctor to a patient.

        POST /api/patients/{id}/assign-doctor/
        Body: { "doctor_id": 123 }

        Returns:
        - 201: Assignment created successfully
        - 400: Invalid doctor_id or assignment already exists
        - 404: Patient not found
        """
        patient = self.get_object()

        # Create assignment data
        data = {
            'doctor_id': request.data.get('doctor_id'),
            'patient_id': patient.id
        }

        serializer = DoctorPatientAssignmentSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()

        return Response(
            {
                'message': 'Doctor assigned successfully',
                'assignment': DoctorPatientAssignmentSerializer(assignment).data
            },
            status=status.HTTP_201_CREATED
        )
