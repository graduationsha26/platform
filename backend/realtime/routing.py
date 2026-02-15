"""
WebSocket URL routing for the realtime app.

Defines WebSocket URL patterns for real-time tremor data streaming.
"""
from django.urls import path
from realtime import consumers

websocket_urlpatterns = [
    path('ws/tremor-data/<int:patient_id>/', consumers.TremorDataConsumer.as_asgi()),
]
