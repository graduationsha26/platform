"""
Serializers for authentication: user registration, login, and JWT tokens.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data (read-only)."""

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.", code='unique_email')
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data.get('role', 'doctor')
        )
        return user


class DoctorListSerializer(serializers.ModelSerializer):
    """
    Read serializer for the admin doctor roster (Feature 047).

    Exposes a single display `name` (full name) and a `patient_count` derived
    from the view's queryset annotation. `patient_count` defaults to 0 when the
    annotation is absent (e.g. on the response after a create).
    """
    name = serializers.SerializerMethodField()
    patient_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email', 'is_active', 'patient_count', 'date_joined']
        read_only_fields = fields

    def get_name(self, obj):
        return obj.get_full_name()

    def get_patient_count(self, obj):
        return getattr(obj, 'patient_count', 0)


class DoctorWriteSerializer(serializers.Serializer):
    """
    Create/update serializer for admin doctor management (Feature 047).

    Accepts a single `name` (split into first/last), `email`, optional
    `password` (required on create), and `is_active` status. Returns the read
    representation via DoctorListSerializer.
    """
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    is_active = serializers.BooleanField(required=False)

    @staticmethod
    def _split_name(name):
        """Split a single full name into (first_name, last_name)."""
        parts = (name or '').strip().split(' ', 1)
        first = parts[0] if parts else ''
        last = parts[1].strip() if len(parts) > 1 else ''
        return first, last

    def validate_email(self, value):
        qs = CustomUser.objects.filter(email=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this email already exists.", code='unique_email')
        return value

    def validate(self, attrs):
        # On create, name, email, and password are required.
        if self.instance is None:
            errors = {}
            if not (attrs.get('name') or '').strip():
                errors['name'] = 'Name is required.'
            if not attrs.get('email'):
                errors['email'] = 'Email is required.'
            if not (attrs.get('password') or '').strip():
                errors['password'] = 'Password is required.'
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        first_name, last_name = self._split_name(validated_data.get('name', ''))
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            role='doctor',
            is_active=validated_data.get('is_active', True),
        )

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.first_name, instance.last_name = self._split_name(validated_data['name'])
        if 'email' in validated_data:
            instance.email = validated_data['email']
        if 'is_active' in validated_data:
            instance.is_active = validated_data['is_active']
        password = validated_data.get('password')
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    def to_representation(self, instance):
        return DoctorListSerializer(instance, context=self.context).data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that includes user data in token response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
