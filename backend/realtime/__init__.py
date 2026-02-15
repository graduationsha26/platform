"""
Real-Time Pipeline app for TremoAI platform.

This app provides real-time data streaming via MQTT and WebSocket:
- MQTT subscriber for glove device sensor data
- WebSocket consumers for live monitoring
- ML prediction integration
"""
default_app_config = 'realtime.apps.RealtimeConfig'
