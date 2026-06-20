"""
Custom user model for TremoAI platform with role-based access control.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser — uses email instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds role field for doctor/admin distinction.
    Uses email instead of username for authentication.
    """

    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]

    # Remove username field - use email instead
    username = None

    # Email as primary identifier
    email = models.EmailField(
        unique=True,
        db_index=True,
        help_text='User email address (used for login)'
    )

    # Role field for access control
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='doctor',
        help_text='User role: doctor or admin'
    )

    # Use email for authentication instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    objects = CustomUserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def is_doctor(self):
        """Check if user is a doctor."""
        return self.role == 'doctor'

    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'admin'
