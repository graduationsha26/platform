"""
URL routing for CMG motor telemetry, fault events, motor commands,
gimbal servo commands, calibration, and gimbal state.

Feature 027: CMG Brushless Motor & ESC Initialization
Feature 028: CMG Gimbal Servo Control
Feature 029: CMG PID Controller Tuning
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MotorTelemetryViewSet,
    MotorFaultViewSet,
    CMGCommandView,
    ServoCommandView,
    GimbalCalibrationView,
    GimbalStateView,
    PIDConfigView,
    SuppressionSessionView,
    SuppressionModeView,
    SuppressionMetricView,
)

router = DefaultRouter()
router.register(r'telemetry', MotorTelemetryViewSet, basename='cmg-telemetry')
router.register(r'faults', MotorFaultViewSet, basename='cmg-faults')

urlpatterns = [
    path('', include(router.urls)),
    path('commands/', CMGCommandView.as_view(), name='cmg-commands'),
    # Feature 028: Gimbal Servo Control
    path('servo/commands/', ServoCommandView.as_view(), name='cmg-servo-commands'),
    path('servo/calibration/<int:device_pk>/', GimbalCalibrationView.as_view(), name='cmg-servo-calibration'),
    path('servo/state/<int:device_pk>/', GimbalStateView.as_view(), name='cmg-servo-state'),
    # Feature 029: PID Controller Tuning
    path('pid/config/<int:device_pk>/', PIDConfigView.as_view(), name='cmg-pid-config'),
    path('pid/sessions/', SuppressionSessionView.as_view(), name='cmg-pid-sessions'),
    path('pid/sessions/<int:session_pk>/', SuppressionSessionView.as_view(), name='cmg-pid-session-detail'),
    path('pid/sessions/<int:session_pk>/metrics/', SuppressionMetricView.as_view(), name='cmg-pid-session-metrics'),
    path('pid/mode/<int:device_pk>/', SuppressionModeView.as_view(), name='cmg-pid-mode'),
]
