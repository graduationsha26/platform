"""URL routing for patients endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, PatientsOverviewView

# Create DRF router
router = DefaultRouter()
router.register(r'', PatientViewSet, basename='patient')

urlpatterns = [
    path('overview/', PatientsOverviewView.as_view(), name='patients-overview'),
    path('', include(router.urls)),
]
