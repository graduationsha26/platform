"""
URL configuration for tremoai_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/auth/', include('authentication.urls')),
    path('api/patients/', include('patients.urls')),
    path('api/devices/', include('devices.urls')),
    path('api/biometric-sessions/', include('biometrics.urls')),
    path('api/biometric-readings/', include('biometrics.reading_urls')),
    path('api/tremor-metrics/', include('biometrics.tremor_metrics_urls')),  # Feature 026: Tremor band-pass + FFT
    path('api/analytics/', include('analytics.urls')),  # Feature 003: Analytics and Reporting
    path('api/inference/', include('inference.urls')),  # Feature 008: ML/DL Inference API
    path('api/cmg/', include('cmg.urls')),              # Feature 027: CMG Motor
]
