"""
Custom pagination classes for patients app.
"""
from rest_framework.pagination import PageNumberPagination


class PatientPagination(PageNumberPagination):
    """Custom pagination for patient list (20 items per page)."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
