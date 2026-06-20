"""
Django admin configuration for Patient models.
"""
from django.contrib import admin
from .models import Patient, DoctorPatientAssignment


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Admin interface for Patient model."""

    list_display = [
        'id', 'full_name', 'date_of_birth', 'contact_email',
        'created_by', 'created_at'
    ]
    list_filter = ['created_at', 'date_of_birth']
    search_fields = ['full_name', 'contact_email', 'contact_phone']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Patient Information', {
            'fields': ('full_name', 'date_of_birth', 'contact_phone', 'contact_email')
        }),
        ('Medical Information', {
            'fields': ('medical_notes',)
        }),
        ('System Information', {
            'fields': ('user', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(DoctorPatientAssignment)
class DoctorPatientAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for DoctorPatientAssignment model."""

    list_display = ['id', 'doctor', 'patient', 'assigned_at', 'assigned_by']
    list_filter = ['assigned_at']
    search_fields = ['doctor__email', 'patient__full_name']
    readonly_fields = ['assigned_at']
    ordering = ['-assigned_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('doctor', 'patient', 'assigned_by')
        }),
        ('Metadata', {
            'fields': ('assigned_at',)
        }),
    )
