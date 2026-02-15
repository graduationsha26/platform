"""
Patient models for TremoAI platform.
"""
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class Patient(models.Model):
    """Patient profile with medical information."""

    user = models.OneToOneField(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_profile'
    )
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    contact_email = models.EmailField(blank=True)
    medical_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.PROTECT,
        related_name='created_patients'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patients'
        ordering = ['-created_at']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.full_name} (ID: {self.id})"

    def clean(self):
        """Validate date_of_birth is not in the future."""
        super().clean()
        if self.date_of_birth and self.date_of_birth > timezone.now().date():
            raise ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})

    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class DoctorPatientAssignment(models.Model):
    """Many-to-many relationship between doctors and patients."""

    doctor = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.CASCADE,
        related_name='patient_assignments'
    )
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE,
        related_name='doctor_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made'
    )

    class Meta:
        db_table = 'doctor_patient_assignments'
        unique_together = [['doctor', 'patient']]
        ordering = ['-assigned_at']
        verbose_name = 'Doctor-Patient Assignment'
        verbose_name_plural = 'Doctor-Patient Assignments'

    def __str__(self):
        return f"Dr. {self.doctor.get_full_name()} → {self.patient.full_name}"

    def clean(self):
        """Validate doctor role."""
        super().clean()
        if self.doctor and self.doctor.role != 'doctor':
            raise ValidationError({'doctor': 'Assigned user must have doctor role.'})
        if self.assigned_by and self.assigned_by.role != 'doctor':
            raise ValidationError({'assigned_by': 'Assignment creator must have doctor role.'})

    def save(self, *args, **kwargs):
        """Override save to call full_clean for validation."""
        self.full_clean()
        super().save(*args, **kwargs)
