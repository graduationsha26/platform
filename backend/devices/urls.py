"""URL routing for devices endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet

# Create DRF router
router = DefaultRouter()
router.register(r'', DeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
]
