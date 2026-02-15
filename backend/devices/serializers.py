"""
Serializers for Device models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Device


class DeviceListSerializer(serializers.ModelSerializer):
    """Read-only serializer for device list view."""

    patient = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ['id', 'serial_number', 'status', 'last_seen', 'patient', 'registered_at']
        read_only_fields = fields

    def get_patient(self, obj):
        """Return nested patient data if paired."""
        if obj.patient:
            return {
                'id': obj.patient.id,
                'full_name': obj.patient.full_name
            }
        return None


class DeviceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for device retrieve view with nested relationships."""

    registered_by = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'serial_number', 'status', 'last_seen',
            'patient', 'registered_by', 'registered_at'
        ]
        read_only_fields = fields

    def get_registered_by(self, obj):
        """Return nested registered_by doctor data."""
        return {
            'id': obj.registered_by.id,
            'email': obj.registered_by.email,
            'first_name': obj.registered_by.first_name,
            'last_name': obj.registered_by.last_name
        }

    def get_patient(self, obj):
        """Return full patient details if paired."""
        if obj.patient:
            return {
                'id': obj.patient.id,
                'full_name': obj.patient.full_name,
                'date_of_birth': obj.patient.date_of_birth,
                'contact_email': obj.patient.contact_email
            }
        return None


class DeviceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating devices."""

    class Meta:
        model = Device
        fields = ['serial_number']

    def validate_serial_number(self, value):
        """Validate serial number format."""
        import re
        if not re.match(r'^[A-Z0-9]{8,20}$', value):
            raise serializers.ValidationError(
                "Serial number must be 8-20 alphanumeric uppercase characters."
            )
        return value

    def create(self, validated_data):
        """Create device with registered_by from request user."""
        request = self.context.get('request')
        validated_data['registered_by'] = request.user
        return super().create(validated_data)


class DevicePairingSerializer(serializers.Serializer):
    """Serializer for pairing device to patient."""

    patient_id = serializers.IntegerField()

    def validate_patient_id(self, value):
        """Validate patient exists and user has access."""
        from patients.models import Patient
        request = self.context.get('request')

        try:
            patient = Patient.objects.get(id=value)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")

        # Check if doctor has access to this patient
        from django.db.models import Q
        user = request.user
        has_access = Patient.objects.filter(
            Q(id=value) & (Q(created_by=user) | Q(doctor_assignments__doctor=user))
        ).exists()

        if not has_access:
            raise serializers.ValidationError("You don't have access to this patient.")

        return value


class DeviceStatusSerializer(serializers.Serializer):
    """Serializer for updating device status."""

    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    last_seen = serializers.DateTimeField(required=False, default=timezone.now)

    def validate_status(self, value):
        """Validate status is valid choice."""
        if value not in ['online', 'offline']:
            raise serializers.ValidationError("Status must be 'online' or 'offline'.")
        return value
