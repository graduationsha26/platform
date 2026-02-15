"""
Custom user model for TremoAI platform with role-based access control.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds role field for patient/doctor distinction.
    Uses email instead of username for authentication.
    """

    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
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
        help_text='User role: doctor or patient'
    )

    # Use email for authentication instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

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

    def is_patient(self):
        """Check if user is a patient."""
        return self.role == 'patient'
