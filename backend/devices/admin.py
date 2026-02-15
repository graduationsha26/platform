"""
Django admin configuration for Device models.
"""
from django.contrib import admin
from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """Admin interface for Device model."""

    list_display = [
        'id', 'serial_number', 'status', 'patient',
        'last_seen', 'registered_by', 'registered_at'
    ]
    list_filter = ['status', 'registered_at', 'last_seen']
    search_fields = ['serial_number', 'patient__full_name']
    readonly_fields = ['registered_by', 'registered_at']
    ordering = ['-registered_at']

    fieldsets = (
        ('Device Information', {
            'fields': ('serial_number', 'status', 'last_seen')
        }),
        ('Pairing', {
            'fields': ('patient',)
        }),
        ('Registration', {
            'fields': ('registered_by', 'registered_at')
        }),
    )
