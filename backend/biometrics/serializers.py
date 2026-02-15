"""
Serializers for BiometricSession models.
"""
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import BiometricSession


class BiometricSessionListSerializer(serializers.ModelSerializer):
    """Read-only serializer for biometric session list view."""

    patient = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()

    class Meta:
        model = BiometricSession
        fields = [
            'id', 'patient', 'device', 'session_start',
            'session_duration', 'created_at'
        ]
        read_only_fields = fields

    def get_patient(self, obj):
        """Return nested patient data."""
        return {
            'id': obj.patient.id,
            'full_name': obj.patient.full_name
        }

    def get_device(self, obj):
        """Return nested device data."""
        return {
            'id': obj.device.id,
            'serial_number': obj.device.serial_number,
            'status': obj.device.status
        }


class BiometricSessionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with full sensor_data JSON."""

    patient = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()

    class Meta:
        model = BiometricSession
        fields = [
            'id', 'patient', 'device', 'session_start',
            'session_duration', 'sensor_data', 'created_at'
        ]
        read_only_fields = fields

    def get_patient(self, obj):
        """Return full patient details."""
        return {
            'id': obj.patient.id,
            'full_name': obj.patient.full_name,
            'date_of_birth': obj.patient.date_of_birth
        }

    def get_device(self, obj):
        """Return full device details."""
        return {
            'id': obj.device.id,
            'serial_number': obj.device.serial_number,
            'status': obj.device.status,
            'last_seen': obj.device.last_seen
        }


class BiometricSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating biometric sessions."""

    patient_id = serializers.IntegerField(write_only=True)
    device_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = BiometricSession
        fields = [
            'patient_id', 'device_id', 'session_start',
            'session_duration', 'sensor_data'
        ]

    def validate_patient_id(self, value):
        """Validate patient exists."""
        from patients.models import Patient
        try:
            Patient.objects.get(id=value)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")
        return value

    def validate_device_id(self, value):
        """Validate device exists."""
        from devices.models import Device
        try:
            Device.objects.get(id=value)
        except Device.DoesNotExist:
            raise serializers.ValidationError("Device not found.")
        return value

    def validate_session_start(self, value):
        """Validate session_start is not in future."""
        if value > timezone.now():
            raise serializers.ValidationError("Session start time cannot be in the future.")
        return value

    def validate_session_duration(self, value):
        """Validate session_duration is positive."""
        if isinstance(value, timedelta):
            if value.total_seconds() <= 0:
                raise serializers.ValidationError("Session duration must be positive.")
        return value

    def validate_sensor_data(self, value):
        """Validate sensor_data JSON structure."""
        required_keys = ['tremor_intensity', 'timestamps', 'frequency']
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            raise serializers.ValidationError(
                f"Missing required keys: {', '.join(missing_keys)}"
            )

        # Validate tremor_intensity is array
        if not isinstance(value.get('tremor_intensity'), list):
            raise serializers.ValidationError("tremor_intensity must be an array.")

        # Validate timestamps is array
        if not isinstance(value.get('timestamps'), list):
            raise serializers.ValidationError("timestamps must be an array.")

        # Validate frequency is number
        if not isinstance(value.get('frequency'), (int, float)):
            raise serializers.ValidationError("frequency must be a number.")

        return value

    def validate(self, attrs):
        """Validate device-patient pairing."""
        from patients.models import Patient
        from devices.models import Device

        patient = Patient.objects.get(id=attrs['patient_id'])
        device = Device.objects.get(id=attrs['device_id'])

        # Check if device is paired to this patient
        if device.patient_id != patient.id:
            raise serializers.ValidationError({
                'device_id': f'Device {device.serial_number} is not paired to this patient.'
            })

        return attrs

    def create(self, validated_data):
        """Create biometric session."""
        from patients.models import Patient
        from devices.models import Device

        patient = Patient.objects.get(id=validated_data.pop('patient_id'))
        device = Device.objects.get(id=validated_data.pop('device_id'))

        session = BiometricSession.objects.create(
            patient=patient,
            device=device,
            **validated_data
        )
        return session


class BiometricAggregationSerializer(serializers.Serializer):
    """Serializer for aggregated biometric data."""

    patient_id = serializers.IntegerField()
    date_range = serializers.DictField(child=serializers.DateTimeField())
    metrics = serializers.DictField(child=serializers.FloatField())

    def to_representation(self, instance):
        """Format aggregation results."""
        return {
            'patient_id': instance['patient_id'],
            'date_range': {
                'start': instance.get('start_date'),
                'end': instance.get('end_date')
            },
            'metrics': {
                'session_count': instance.get('session_count', 0),
                'total_duration_seconds': instance.get('total_duration', 0),
                'average_tremor_intensity': instance.get('average_tremor', 0.0),
                'min_tremor_intensity': instance.get('min_tremor', 0.0),
                'max_tremor_intensity': instance.get('max_tremor', 0.0)
            }
        }
