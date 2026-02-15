"""
WebSocket URL routing for tremoai_backend project.

This module aggregates WebSocket URL patterns from all apps.
"""
from django.urls import path
from realtime import routing as realtime_routing

# Aggregate WebSocket URL patterns from all apps
websocket_urlpatterns = [
    # Real-time pipeline WebSocket routes
    *realtime_routing.websocket_urlpatterns,
]
