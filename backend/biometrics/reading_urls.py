"""URL routing for BiometricReading endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BiometricReadingViewSet

router = DefaultRouter()
router.register(r'', BiometricReadingViewSet, basename='biometric-reading')

urlpatterns = [
    path('', include(router.urls)),
]
