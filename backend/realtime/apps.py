"""
Django app configuration for realtime app.
"""
from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """Configuration for the realtime application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'realtime'
    verbose_name = 'Real-Time Pipeline'
