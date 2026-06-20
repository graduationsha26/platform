"""
Custom pagination classes for patients app.
"""
from rest_framework.pagination import PageNumberPagination


class PatientPagination(PageNumberPagination):
    """Custom pagination for patient list (20 items per page)."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminPatientPagination(PageNumberPagination):
    """Pagination for the admin center-wide patient roster (50 items per page).

    Feature 048: Patient Distribution. Matches feature 047's admin roster page size.
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100
