# Quickstart: Dashboard Overview Page

**Branch**: `032-dashboard-overview` | **Date**: 2026-02-20

---

## Overview

This guide shows how the dashboard overview feature works end-to-end: from a doctor loading the page to the rendered summary cards and tremor trend chart.

---

## Scenario 1: Doctor views the dashboard with full data

**Prerequisites**:
- Doctor account exists and is authenticated (JWT token in browser storage)
- At least 2 patients are assigned to the doctor via `DoctorPatientAssignment`
- At least 1 device is online
- TremorMetrics data exists for the past 7 days

**Flow**:

```
1. Doctor navigates to /doctor/dashboard

2. DoctorDashboard.jsx mounts
   → useDashboardStats() hook fires
   → analyticsService.fetchDashboardStats() is called
   → GET /api/analytics/dashboard/ with Authorization: Bearer <jwt>

3. DashboardStatsView (backend)
   → IsDoctor permission: passes
   → DashboardService.get_dashboard_stats(doctor=request.user)
     a. patients = Patient.objects.filter(doctor_assignments__doctor=doctor)
     b. total_patients = patients.count()          → e.g. 12
     c. active_devices = Device.objects.filter(patient__in=patients, status='online').count()  → e.g. 3
     d. alerts_count = BiometricSession.objects.filter(
            patient__in=patients,
            session_start__gte=now() - 24h,
            ml_prediction__severity='severe'
        ).count()                                   → e.g. 2
     e. tremor_trend = TremorMetrics over last 7 days
            grouped by date, avg(dominant_amplitude) → 7 data points

4. Response 200:
   {
     "total_patients": 12,
     "active_devices": 3,
     "alerts_count": 2,
     "tremor_trend": [
       {"date": "2026-02-14", "avg_amplitude": 0.45},
       ...
       {"date": "2026-02-20", "avg_amplitude": 0.33}
     ]
   }

5. useDashboardStats hook: loading → false, data set

6. DoctorDashboard renders:
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  Total Patients  │  │  Active Devices  │  │     Alerts       │
   │       12         │  │        3         │  │        2         │
   └──────────────────┘  └──────────────────┘  └──────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │              7-Day Tremor Trend (LineChart)                 │
   │  0.6 │              ●                                       │
   │  0.5 │         ●                                           │
   │  0.4 │    ●              ●         ●                       │
   │  0.3 │                                       ●             │
   │      └────────────────────────────────────────────────      │
   │       Feb14  Feb15  Feb16  Feb17  Feb18  Feb19  Feb20      │
   └─────────────────────────────────────────────────────────────┘
```

---

## Scenario 2: Doctor has no patients

**Flow**:
```
GET /api/analytics/dashboard/
→ Response 200:
  {
    "total_patients": 0,
    "active_devices": 0,
    "alerts_count": 0,
    "tremor_trend": [
      {"date": "2026-02-14", "avg_amplitude": null},
      {"date": "2026-02-15", "avg_amplitude": null},
      ...
      {"date": "2026-02-20", "avg_amplitude": null}
    ]
  }

→ Cards show "0" (not blank)
→ Chart shows empty state: "No tremor data available"
```

---

## Scenario 3: Analytics endpoint is unavailable

**Flow**:
```
GET /api/analytics/dashboard/
→ Network error / 500

→ useDashboardStats: error = "Failed to load dashboard data"
→ DoctorDashboard renders error states:
  - Summary cards show "—" with error icon
  - Chart area shows: "Unable to load trend data. Please refresh."
  (Page does not crash; other layout elements remain visible)
```

---

## Scenario 4: Unauthenticated access attempt

**Flow**:
```
GET /api/analytics/dashboard/ (no Authorization header)
→ Response 401: {"error": "Authentication credentials were not provided."}

→ Frontend api.js 401 interceptor fires
→ Token cleared, user redirected to /login
```

---

## Integration Points

| Layer | File | What it does |
|-------|------|--------------|
| Backend service | `backend/analytics/services/dashboard.py` | Computes all 4 metrics with a single DB round-trip per metric |
| Backend serializer | `backend/analytics/serializers.py` | `DashboardStatsSerializer` validates and formats the response |
| Backend view | `backend/analytics/views.py` | `DashboardStatsView` — `IsDoctor` permission, delegates to service |
| Backend URL | `backend/analytics/urls.py` | `path('dashboard/', DashboardStatsView.as_view())` |
| Frontend service | `frontend/src/services/analyticsService.js` | `fetchDashboardStats()` — GET with JWT |
| Frontend hook | `frontend/src/hooks/useDashboardStats.js` | `{ data, loading, error }` state management |
| Frontend card | `frontend/src/components/dashboard/SummaryCard.jsx` | Renders label + value + loading/error state |
| Frontend chart | `frontend/src/components/dashboard/TremorTrendChart.jsx` | Recharts `LineChart` with empty/error states |
| Frontend page | `frontend/src/pages/DoctorDashboard.jsx` | Composes cards + chart, passes data from hook |
