"""
Django-filter classes for Patient model.
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Patient


class PatientFilter(filters.FilterSet):
    """Filter class for patient search."""

    name = filters.CharFilter(method='filter_by_name')

    class Meta:
        model = Patient
        fields = ['name']

    def filter_by_name(self, queryset, name, value):
        """
        Filter patients by full_name (case-insensitive).
        Searches across full_name field using ILIKE (PostgreSQL).
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(full_name__icontains=value)
        )
