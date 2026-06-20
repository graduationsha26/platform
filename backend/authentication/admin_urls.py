"""
Admin-only URL routing for staff (doctor) management.

Feature 047: Staff Management
Included at /api/admin/ from the project urls.
"""
from django.urls import path
from .views import AdminDoctorListCreateView, AdminDoctorDetailView

urlpatterns = [
    # GET (list with patient_count) + POST (create)
    path('doctors/', AdminDoctorListCreateView.as_view(), name='admin-doctors'),

    # GET (retrieve) + PATCH (update details / toggle is_active)
    path('doctors/<int:pk>/', AdminDoctorDetailView.as_view(), name='admin-doctor-detail'),
]
