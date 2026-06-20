"""URL routing for TremorMetrics endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TremorMetricsViewSet

router = DefaultRouter()
router.register(r'', TremorMetricsViewSet, basename='tremor-metrics')

urlpatterns = [
    path('', include(router.urls)),
]
