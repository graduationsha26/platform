"""
Analytics App URL Configuration

Feature 003: Analytics and Reporting
Routes for tremor statistics and PDF report generation endpoints.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Feature 032: Dashboard overview summary stats
    path('dashboard/', views.DashboardStatsView.as_view(), name='dashboard-stats'),

    # User Story 1: Statistics endpoint (MVP)
    path('stats/', views.StatisticsView.as_view(), name='statistics'),

    # User Story 2: PDF report generation
    path('reports/', views.ReportGenerationView.as_view(), name='reports'),
]
