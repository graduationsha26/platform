"""
Admin-only patient distribution URLs (Feature 048).

Mounted at /api/admin/patients/ in tremoai_backend/urls.py — registered BEFORE
the api/admin/ (authentication.admin_urls) include so this more specific prefix
resolves first.
"""
from django.urls import path
from .views import AdminPatientListCreateView, AdminPatientAssignView

urlpatterns = [
    path('', AdminPatientListCreateView.as_view(), name='admin-patients'),
    path('<int:pk>/assign/', AdminPatientAssignView.as_view(), name='admin-patient-assign'),
]
