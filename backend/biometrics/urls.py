"""URL routing for biometrics endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BiometricSessionViewSet

# Create DRF router
router = DefaultRouter()
router.register(r'', BiometricSessionViewSet, basename='biometric-session')

urlpatterns = [
    path('', include(router.urls)),
]
