"""
Analytics App URL Configuration

Feature 003: Analytics and Reporting
Routes for tremor statistics and PDF report generation endpoints.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Feature 046: Admin center-wide stats
    path('admin-stats/', views.AdminStatsView.as_view(), name='admin-stats'),

    # Feature 032: Dashboard overview summary stats
    path('dashboard/', views.DashboardStatsView.as_view(), name='dashboard-stats'),

    # Critical alerts: patients with 5 consecutive days of severe tremors
    path('critical-alerts/', views.CriticalAlertsView.as_view(), name='critical-alerts'),

    # User Story 1: Statistics endpoint (MVP)
    path('stats/', views.StatisticsView.as_view(), name='statistics'),

    # User Story 2: PDF report generation
    path('reports/', views.ReportGenerationView.as_view(), name='reports'),
]
