"""
Serializers for Patient models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Patient, DoctorPatientAssignment


class PatientListSerializer(serializers.ModelSerializer):
    """Read-only serializer for patient list view."""

    class Meta:
        model = Patient
        fields = ['id', 'full_name', 'date_of_birth', 'contact_email', 'created_at']
        read_only_fields = fields


class CreatedBySerializer(serializers.ModelSerializer):
    """Nested serializer for created_by field."""

    class Meta:
        model = 'authentication.CustomUser'
        fields = ['id', 'email', 'first_name', 'last_name']


class AssignedDoctorSerializer(serializers.ModelSerializer):
    """Nested serializer for assigned doctors."""

    doctor = serializers.SerializerMethodField()

    class Meta:
        model = DoctorPatientAssignment
        fields = ['doctor', 'assigned_at']

    def get_doctor(self, obj):
        return {
            'id': obj.doctor.id,
            'email': obj.doctor.email,
            'first_name': obj.doctor.first_name,
            'last_name': obj.doctor.last_name
        }


class PatientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for patient retrieve view with nested relationships."""

    created_by = serializers.SerializerMethodField()
    assigned_doctors = serializers.SerializerMethodField()
    paired_device = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'date_of_birth', 'contact_phone', 'contact_email',
            'medical_notes', 'created_by', 'assigned_doctors', 'paired_device',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_created_by(self, obj):
        """Return nested created_by user data."""
        return {
            'id': obj.created_by.id,
            'email': obj.created_by.email,
            'first_name': obj.created_by.first_name,
            'last_name': obj.created_by.last_name
        }

    def get_assigned_doctors(self, obj):
        """Return list of assigned doctors."""
        assignments = obj.doctor_assignments.select_related('doctor').all()
        return [
            {
                'doctor': {
                    'id': assignment.doctor.id,
                    'email': assignment.doctor.email,
                    'first_name': assignment.doctor.first_name,
                    'last_name': assignment.doctor.last_name
                },
                'assigned_at': assignment.assigned_at
            }
            for assignment in assignments
        ]

    def get_paired_device(self, obj):
        """Return paired device if exists."""
        # Device will be added in Phase 5
        device = getattr(obj, 'devices', None)
        if device and device.exists():
            first_device = device.first()
            return {
                'id': first_device.id,
                'serial_number': first_device.serial_number,
                'status': first_device.status
            }
        return None


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating patients."""

    class Meta:
        model = Patient
        fields = [
            'full_name', 'date_of_birth', 'contact_phone',
            'contact_email', 'medical_notes'
        ]

    def validate_date_of_birth(self, value):
        """Validate date_of_birth is not in the future."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def create(self, validated_data):
        """Create patient with created_by from request user."""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class DoctorPatientAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for doctor-patient assignments."""

    doctor_id = serializers.IntegerField(write_only=True)
    patient_id = serializers.IntegerField(write_only=True)
    doctor = serializers.SerializerMethodField(read_only=True)
    patient = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DoctorPatientAssignment
        fields = ['id', 'doctor_id', 'patient_id', 'doctor', 'patient', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']

    def get_doctor(self, obj):
        """Return doctor details."""
        return {
            'id': obj.doctor.id,
            'email': obj.doctor.email,
            'first_name': obj.doctor.first_name,
            'last_name': obj.doctor.last_name
        }

    def get_patient(self, obj):
        """Return patient details."""
        return {
            'id': obj.patient.id,
            'full_name': obj.patient.full_name
        }

    def validate_doctor_id(self, value):
        """Validate doctor exists and has doctor role."""
        from authentication.models import CustomUser
        try:
            doctor = CustomUser.objects.get(id=value)
            if doctor.role != 'doctor':
                raise serializers.ValidationError("User must have doctor role.")
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Doctor not found.")
        return value

    def validate_patient_id(self, value):
        """Validate patient exists."""
        try:
            Patient.objects.get(id=value)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")
        return value

    def validate(self, attrs):
        """Validate assignment doesn't already exist."""
        from authentication.models import CustomUser
        doctor = CustomUser.objects.get(id=attrs['doctor_id'])
        patient = Patient.objects.get(id=attrs['patient_id'])

        if DoctorPatientAssignment.objects.filter(doctor=doctor, patient=patient).exists():
            raise serializers.ValidationError("This doctor is already assigned to this patient.")

        return attrs

    def create(self, validated_data):
        """Create assignment with assigned_by from request user."""
        from authentication.models import CustomUser
        request = self.context.get('request')
        doctor = CustomUser.objects.get(id=validated_data.pop('doctor_id'))
        patient = Patient.objects.get(id=validated_data.pop('patient_id'))

        assignment = DoctorPatientAssignment.objects.create(
            doctor=doctor,
            patient=patient,
            assigned_by=request.user
        )
        return assignment
