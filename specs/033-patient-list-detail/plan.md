# Implementation Plan: Patient List & Detail Pages

**Branch**: `033-patient-list-detail` | **Date**: 2026-02-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/033-patient-list-detail/spec.md`

## Summary

This feature is primarily a **frontend implementation**. The backend patient CRUD API (`/api/patients/`) and biometric session list API (`/api/biometric-sessions/`) already exist and are fully functional. Two minor backend serializer enhancements are required:

1. Add `last_session_date` to `PatientListSerializer` so the patient list can show each patient's most recent session.
2. Add `ml_prediction_severity` to `BiometricSessionListSerializer` so the session history on the detail page can show ML-predicted tremor severity.

All frontend pages (patient list, detail, create, edit), components (table, session history, form, pagination), services, and hooks are new. Four new routes are added to `AppRoutes.jsx`.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) — `doctor` role enforced via `IsDoctorOrAdmin`
**Testing**: None requested
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: Not applicable — all data is fetched on page load / user action
**Integration**: None — no MQTT or WebSocket involvement
**AI/ML**: None — ML predictions are read from existing session data, not computed here
**Performance Goals**: List loads ≤3s; search results visible ≤1s after typing; detail page ≤3s
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: Up to 100 patients per doctor; up to 10 sessions/page on detail

## Constitution Check

- [x] **Monorepo Architecture**: Two backend serializer edits in `backend/`; all frontend in `frontend/src/`
- [x] **Tech Stack Immutability**: Uses Django + DRF (backend), React + Tailwind (frontend) — no new libraries
- [x] **Database Strategy**: Uses existing Supabase PostgreSQL via Django ORM (no schema changes)
- [x] **Authentication**: `IsDoctorOrAdmin` permission on existing `PatientViewSet`; JWT via `api.js`
- [x] **Security-First**: No new secrets; all auth via existing JWT infrastructure
- [x] **Real-time Requirements**: Not applicable
- [x] **MQTT Integration**: Not applicable
- [x] **AI Model Serving**: Not applicable
- [x] **API Standards**: REST + JSON, snake_case, standard HTTP codes — all existing
- [x] **Development Scope**: Local development only

**Result**: ✅ PASS — No violations. Backend APIs already exist; feature is largely a frontend build.

## Project Structure

### Documentation (this feature)

```text
specs/033-patient-list-detail/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── patient-list.yaml       # GET /api/patients/ (with last_session_date)
│   ├── patient-detail.yaml     # GET/PUT/PATCH /api/patients/{id}/
│   ├── patient-create.yaml     # POST /api/patients/
│   └── session-history.yaml    # GET /api/biometric-sessions/?patient={id}
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code

```text
backend/
└── patients/
    └── serializers.py       # MODIFY — add last_session_date to PatientListSerializer

backend/
└── biometrics/
    └── serializers.py       # MODIFY — add ml_prediction_severity to BiometricSessionListSerializer

frontend/
└── src/
    ├── services/
    │   └── patientService.js         # NEW — API client (list, detail, create, update, sessions)
    ├── hooks/
    │   ├── usePatients.js            # NEW — paginated list with search + page state
    │   └── usePatient.js             # NEW — single patient detail + session history
    ├── components/
    │   ├── common/
    │   │   └── Pagination.jsx        # NEW — reusable pagination control
    │   └── patients/
    │       ├── PatientTable.jsx      # NEW — table with name, DOB, last session, link
    │       ├── PatientForm.jsx       # NEW — shared create/edit form with validation
    │       └── SessionHistoryList.jsx # NEW — paginated session history table
    ├── pages/
    │   ├── PatientListPage.jsx       # NEW — list page (search + table + pagination)
    │   ├── PatientDetailPage.jsx     # NEW — detail page (profile card + session history)
    │   ├── PatientCreatePage.jsx     # NEW — create form page
    │   └── PatientEditPage.jsx       # NEW — edit form page (pre-populated)
    └── routes/
        └── AppRoutes.jsx             # MODIFY — add 4 patient routes
```

## Complexity Tracking

> No constitution violations — section not applicable.
