"""
API views for patient management.
"""
from datetime import timedelta

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q, Max
from django.utils import timezone

from authentication.permissions import IsDoctorOrAdmin, IsAdmin
from .models import Patient, DoctorPatientAssignment
from .serializers import (
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
    DoctorPatientAssignmentSerializer,
    PatientOverviewItemSerializer,
    AdminPatientListSerializer,
    AdminPatientRegisterSerializer,
    AdminPatientAssignSerializer,
)
from .filters import PatientFilter
from .pagination import PatientPagination, AdminPatientPagination


class PatientsOverviewView(APIView):
    """
    GET /api/patients/overview/

    Returns the authenticated doctor's patient list with avatar URL and
    live device status (online = last telemetry within 60 seconds).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can access the patients overview.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        threshold = timezone.now() - timedelta(seconds=60)
        patients = (
            Patient.objects
            .filter(doctor_assignments__doctor=request.user)
            .annotate(latest_device_seen=Max('devices__last_seen'))
            .order_by('full_name')
        )

        results = [
            {
                'id': p.id,
                'full_name': p.full_name,
                'avatar_url': p.avatar_url or '',
                'device_online': (
                    p.latest_device_seen is not None
                    and p.latest_device_seen >= threshold
                ),
            }
            for p in patients
        ]

        serializer = PatientOverviewItemSerializer(results, many=True)
        return Response(
            {'count': len(results), 'results': serializer.data},
            status=status.HTTP_200_OK,
        )


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


# ---------------------------------------------------------------------------
# Feature 048: Patient Distribution (Admin)
# ---------------------------------------------------------------------------

class AdminPatientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/patients/   — center-wide patient roster (admin only).
    POST /api/admin/patients/   — register a new patient, optionally assigning a doctor.

    Each roster row carries the patient's single effective assigned doctor
    (most-recent assignment) or null when Unassigned.
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = AdminPatientPagination

    def get_queryset(self):
        queryset = (
            Patient.objects
            .all()
            .select_related('created_by')
            .prefetch_related('doctor_assignments__doctor')
            .order_by('full_name', 'id')
        )
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(contact_email__icontains=search)
            )
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminPatientRegisterSerializer
        return AdminPatientListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        data = AdminPatientListSerializer(patient, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class AdminPatientAssignView(APIView):
    """
    POST /api/admin/patients/<id>/assign/  — assign or reassign a patient to a doctor.

    Replace semantics: the patient's existing assignments are removed and a single
    new assignment to the chosen doctor is created (admin-initiated → assigned_by=None).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        serializer = AdminPatientAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from authentication.models import CustomUser
        doctor = CustomUser.objects.get(id=serializer.validated_data['doctor_id'])

        with transaction.atomic():
            patient.doctor_assignments.all().delete()
            DoctorPatientAssignment.objects.create(
                doctor=doctor,
                patient=patient,
                assigned_by=None,
            )

        patient.refresh_from_db()
        data = AdminPatientListSerializer(patient, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)
