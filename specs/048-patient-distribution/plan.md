# Implementation Plan: Patient Distribution (Admin)

**Branch**: `048-patient-distribution` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/048-patient-distribution/spec.md`

## Summary

Give the **admin** (institutional manager) three center-wide patient-distribution capabilities, all gated to the `admin` role:

1. **Center-wide roster** — `GET /api/admin/patients/` returns every patient in the center with their single effective assigned doctor (or `null` = Unassigned), paginated. Rendered by the `AdminPatientTable` component.
2. **Register patient** — `POST /api/admin/patients/` creates a patient (`created_by` = admin) and optionally assigns a doctor in one call. Rendered by the `RegisterPatientForm` component with a doctor-assignment dropdown.
3. **Assign / reassign** — `POST /api/admin/patients/<id>/assign/` replaces the patient's assignment so they belong to exactly one doctor.

**Technical approach**: Reuse the existing `Patient` and `DoctorPatientAssignment` models unchanged (no migration). Views live in `patients/views.py` (per user instruction) as DRF generic/`APIView` classes, exposed through a new `patients/admin_urls.py` mounted at `/api/admin/patients/`. The one real constraint — `DoctorPatientAssignment.clean()` rejects an `assigned_by` whose role isn't `doctor` — is handled by setting `assigned_by=None` for admin-initiated assignments (the FK is `null=True, on_delete=SET_NULL`). Reassignment uses replace semantics (delete existing assignments for the patient, create one new) inside `transaction.atomic()`. The frontend reuses feature 047's `doctorService.listDoctors()` to populate the doctor dropdown (filtered to active doctors).

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote) — **no schema change / no migration** (reuses `patients` + `doctor_patient_assignments` tables)
**Authentication**: JWT (SimpleJWT); `admin` role enforced via existing `authentication.permissions.IsAdmin`
**Testing**: Manual quickstart verification + read-only API smoke check (avoid mutating remote DB in automated checks)
**Project Type**: monorepo (backend/, frontend/, firmware/)
**Real-time**: Not used by this feature
**Integration**: Not used by this feature (no MQTT, no ESP32)
**AI/ML**: Not used by this feature
**Performance Goals**: Roster page load returns in a single request; admin actions reflected on roster after a refresh
**Constraints**: Local development only; admin-only access; one effective doctor per patient
**Scale/Scope**: Single center; tens–hundreds of patients; pagination at 50/page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Backend in `backend/patients/`, frontend in `frontend/src/` — fits existing structure
- [x] **Tech Stack Immutability**: Django + DRF + React + Tailwind only; no new frameworks/libraries
- [x] **Database Strategy**: Supabase PostgreSQL only; reuses existing tables; no new DB, no local SQLite
- [x] **Authentication**: JWT via SimpleJWT; `admin` role enforced with existing `IsAdmin` permission
- [x] **Security-First**: No secrets introduced; no hardcoded credentials; all config stays in `.env`
- [x] **Real-time Requirements**: N/A — no real-time need; no Channels usage
- [x] **MQTT Integration**: N/A — no glove data/control in scope
- [x] **AI Model Serving**: N/A — no model inference in scope
- [x] **API Standards**: REST + JSON, snake_case keys, standard HTTP codes, `{ "error": "message" }` error format
- [x] **Development Scope**: Local development only; no Docker/CI-CD/production config

**Result**: ✅ PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/048-patient-distribution/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── admin-patients.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
backend/
├── patients/
│   ├── models.py                 # UNCHANGED (reuse Patient, DoctorPatientAssignment)
│   ├── serializers.py            # MODIFY: add AdminPatientListSerializer,
│   │                             #         AdminPatientRegisterSerializer,
│   │                             #         AdminPatientAssignSerializer
│   ├── views.py                  # MODIFY: add AdminPatientListCreateView, AdminPatientAssignView
│   ├── pagination.py             # MODIFY: add AdminPatientPagination (page_size=50)
│   ├── admin_urls.py             # CREATE: routes for /api/admin/patients/ + /<id>/assign/
│   └── urls.py                   # UNCHANGED
└── tremoai_backend/
    └── urls.py                   # MODIFY: include patients.admin_urls at api/admin/patients/
                                  #         (BEFORE the api/admin/ authentication include)

frontend/
├── src/
│   ├── services/
│   │   └── adminPatientService.js     # CREATE: list/register/assign admin patient calls
│   ├── hooks/
│   │   └── useAdminPatients.js        # CREATE: paginated roster hook (mirrors useDoctors)
│   ├── components/admin/
│   │   ├── AdminPatientTable.jsx      # CREATE: center-wide roster table + Reassign action
│   │   ├── RegisterPatientForm.jsx    # CREATE: register modal/form + doctor dropdown
│   │   └── AssignDoctorModal.jsx      # CREATE: lightweight reassign modal (doctor dropdown)
│   ├── pages/
│   │   └── PatientDistributionPage.jsx# CREATE: page wiring roster + register + reassign
│   ├── routes/
│   │   └── AppRoutes.jsx              # MODIFY: add /admin/patients protected route
│   └── utils/
│       └── roleHelpers.js            # MODIFY: add "Patients" item to admin sidebar menu
```

**Structure Decision**: Backend views stay in `patients/views.py` (explicit user instruction). The admin URL surface is a new `patients/admin_urls.py` mounted at `/api/admin/patients/` and registered **before** the existing `api/admin/` → `authentication.admin_urls` include in `tremoai_backend/urls.py`, so the more specific `patients/` prefix resolves first (see research.md decision 2). Frontend mirrors the layered service → hook → page → components pattern established by feature 047 (Staff Management), reusing its `doctorService` for the doctor dropdown.

## Complexity Tracking

No constitutional violations. Table intentionally omitted.
