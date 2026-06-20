"""
Django admin configuration for BiometricSession models.
"""
from django.contrib import admin
from .models import BiometricSession


@admin.register(BiometricSession)
class BiometricSessionAdmin(admin.ModelAdmin):
    """Admin interface for BiometricSession model."""

    list_display = [
        'id', 'patient', 'device', 'session_start',
        'session_duration', 'created_at'
    ]
    list_filter = ['session_start', 'created_at', 'device__status']
    search_fields = ['patient__full_name', 'device__serial_number']
    readonly_fields = ['created_at']
    ordering = ['-session_start']

    fieldsets = (
        ('Session Information', {
            'fields': ('patient', 'device', 'session_start', 'session_duration')
        }),
        ('Sensor Data', {
            'fields': ('sensor_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )
