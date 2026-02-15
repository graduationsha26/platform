"""
Analytics App URL Configuration

Feature 003: Analytics and Reporting
Routes for tremor statistics and PDF report generation endpoints.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # User Story 1: Statistics endpoint (MVP)
    path('stats/', views.StatisticsView.as_view(), name='statistics'),

    # User Story 2: PDF report generation
    path('reports/', views.ReportGenerationView.as_view(), name='reports'),
]
