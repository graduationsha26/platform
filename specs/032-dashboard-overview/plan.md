# Implementation Plan: Dashboard Overview Page

**Branch**: `032-dashboard-overview` | **Date**: 2026-02-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/032-dashboard-overview/spec.md`

## Summary

Implement the doctor dashboard overview page by:
1. Adding a dedicated `GET /api/analytics/dashboard/` endpoint that returns system-wide summary stats (total patients, active devices, alerts count) and a 7-day tremor trend array — all scoped to the logged-in doctor.
2. Replacing the existing placeholder `DoctorDashboard` page with live data: three summary cards wired to the new endpoint and a Recharts `LineChart` rendering the 7-day tremor trend.

No new database models are required. All metrics are computed from existing `Patient`, `Device`, `BiometricSession`, and `TremorMetrics` models.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) — `doctor` role required for this endpoint
**Testing**: pytest (backend), Vitest (frontend)
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: Not needed — dashboard stats are fetched once on page load
**Integration**: None — no MQTT or WebSocket involvement
**AI/ML**: None — no model inference involved
**Performance Goals**: API response < 500ms; page renders within 3 seconds
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: Single doctor session; up to ~100 patients per doctor

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Backend changes go in `backend/analytics/`; frontend in `frontend/src/pages/` and `frontend/src/components/dashboard/`
- [x] **Tech Stack Immutability**: Uses existing Django + DRF (backend), React + Recharts + Tailwind (frontend) — no new libraries
- [x] **Database Strategy**: Queries Supabase PostgreSQL via existing Django ORM models only
- [x] **Authentication**: `IsDoctor` permission class enforced on new endpoint; JWT token sent by frontend `api.js`
- [x] **Security-First**: No new secrets introduced; existing `VITE_API_BASE_URL` and JWT setup used
- [x] **Real-time Requirements**: Not applicable — dashboard is a static fetch-on-load view
- [x] **MQTT Integration**: Not applicable — no sensor data ingestion in this feature
- [x] **AI Model Serving**: Not applicable — no ML inference in this feature
- [x] **API Standards**: New endpoint is RESTful, returns JSON, uses snake_case, standard HTTP codes
- [x] **Development Scope**: Local development only

**Result**: ✅ PASS — No violations

## Project Structure

### Documentation (this feature)

```text
specs/032-dashboard-overview/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── dashboard-stats.yaml   # OpenAPI contract for GET /api/analytics/dashboard/
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code

```text
backend/
└── analytics/
    ├── services/
    │   └── dashboard.py         # NEW — DashboardService: computes all 4 metrics
    ├── serializers.py           # MODIFY — add DashboardStatsSerializer
    ├── views.py                 # MODIFY — add DashboardStatsView
    └── urls.py                  # MODIFY — register GET dashboard/ route

frontend/
└── src/
    ├── services/
    │   └── analyticsService.js  # NEW — fetchDashboardStats() API client function
    ├── hooks/
    │   └── useDashboardStats.js # NEW — useDashboardStats() hook (loading/error/data)
    ├── components/
    │   └── dashboard/
    │       ├── SummaryCard.jsx       # NEW — reusable stat card (label, value, icon)
    │       └── TremorTrendChart.jsx  # NEW — Recharts LineChart for 7-day trend
    └── pages/
        └── DoctorDashboard.jsx  # MODIFY — replace "--" placeholders with live data
```

## Complexity Tracking

> No constitution violations — section not applicable.
