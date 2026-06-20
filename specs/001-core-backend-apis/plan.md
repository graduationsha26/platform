# Implementation Plan: Core Backend APIs

**Branch**: `001-core-backend-apis` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-core-backend-apis/spec.md`

## Summary

Implement foundational backend APIs for TremoAI platform including JWT authentication with role-based access control (patient/doctor), patient CRUD operations with search and doctor-patient assignment, device registration and pairing system, and biometric data storage with date-range retrieval. This feature establishes the core data model and RESTful API infrastructure required for all subsequent platform features.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data (not in this feature)
**Integration**: MQTT subscription for glove sensor data (not in this feature)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django (not in this feature)
**Performance Goals**: API response <200ms for 95% of requests, support 10 concurrent doctors with 20 patients each
**Constraints**: Local development only, no Docker/CI/CD, REST APIs only (no WebSocket in this feature)
**Scale/Scope**: 100 patients, 10 doctors, 1000 biometric sessions initially

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/` structure (Django apps for auth, patients, devices, biometrics)
- [X] **Tech Stack Immutability**: Uses Django 5.x + DRF + SimpleJWT (no new frameworks)
- [X] **Database Strategy**: Uses Supabase PostgreSQL only (Django ORM models, no local SQLite)
- [X] **Authentication**: Uses JWT via SimpleJWT with patient/doctor roles
- [X] **Security-First**: All secrets in `.env` files (DB credentials, JWT secret key, Supabase URL)
- [X] **Real-time Requirements**: N/A (WebSocket not in this feature scope)
- [X] **MQTT Integration**: N/A (MQTT not in this feature scope)
- [X] **AI Model Serving**: N/A (AI models not in this feature scope)
- [X] **API Standards**: REST + JSON, standard HTTP codes (200, 201, 400, 401, 403, 404, 500), snake_case naming
- [X] **Development Scope**: Local development only (python manage.py runserver, no Docker/CI/CD)

**Result**: ✅ PASS - All constitutional principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/001-core-backend-apis/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (minimal - stack predefined)
├── data-model.md        # Phase 1 output (Django models)
├── quickstart.md        # Phase 1 output (test scenarios)
├── contracts/           # Phase 1 output (OpenAPI specs)
│   ├── auth.yaml        # Authentication endpoints
│   ├── patients.yaml    # Patient CRUD endpoints
│   ├── devices.yaml     # Device management endpoints
│   └── biometrics.yaml  # Biometric data endpoints
├── checklists/
│   └── requirements.md  # Spec quality checklist (done)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── tremoai_backend/              # Django project
│   ├── settings.py              # Project settings (JWT, CORS, DB config)
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py                  # WSGI application
├── authentication/               # Django app: User auth & JWT
│   ├── models.py                # CustomUser model with role field
│   ├── serializers.py           # UserSerializer, RegisterSerializer, LoginSerializer
│   ├── views.py                 # RegisterView, LoginView, TokenRefreshView
│   ├── urls.py                  # /api/auth/register, /api/auth/login, /api/auth/refresh
│   ├── permissions.py           # IsDoctor, IsPatient, IsOwnerOrDoctor permissions
│   └── tests/
│       ├── test_models.py
│       ├── test_auth_api.py
│       └── test_permissions.py
├── patients/                     # Django app: Patient management
│   ├── models.py                # Patient, DoctorPatientAssignment models
│   ├── serializers.py           # PatientSerializer, PatientListSerializer
│   ├── views.py                 # PatientViewSet (CRUD + search)
│   ├── urls.py                  # /api/patients/ endpoints
│   ├── filters.py               # Patient search filter
│   └── tests/
│       ├── test_models.py
│       ├── test_patient_api.py
│       └── test_search.py
├── devices/                      # Django app: Device registration
│   ├── models.py                # Device model (serial, status, patient FK)
│   ├── serializers.py           # DeviceSerializer, DevicePairingSerializer
│   ├── views.py                 # DeviceViewSet, PairingView, StatusUpdateView
│   ├── urls.py                  # /api/devices/ endpoints
│   └── tests/
│       ├── test_models.py
│       ├── test_device_api.py
│       └── test_pairing.py
├── biometrics/                   # Django app: Biometric data
│   ├── models.py                # BiometricSession model
│   ├── serializers.py           # BiometricSessionSerializer, AggregationSerializer
│   ├── views.py                 # BiometricSessionViewSet, AggregationView
│   ├── urls.py                  # /api/biometric-sessions/ endpoints
│   ├── aggregation.py           # Aggregation logic (avg, count, duration)
│   └── tests/
│       ├── test_models.py
│       ├── test_biometric_api.py
│       └── test_aggregation.py
├── requirements.txt              # Django dependencies
├── manage.py                     # Django management script
└── .env.example                  # Environment variables template

.env                              # Environment variables (gitignored)
├── DJANGO_SECRET_KEY
├── SUPABASE_URL
├── SUPABASE_KEY
├── DATABASE_URL
└── JWT_SECRET_KEY
```

**Structure Decision**: Using Django apps architecture where each domain (authentication, patients, devices, biometrics) is a separate app within the backend/ directory. This follows Django best practices for modularity and aligns with the monorepo constitution principle. Frontend implementation is out of scope for this feature (backend APIs only).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All constitutional principles are satisfied:
- Monorepo architecture maintained (backend/ directory)
- Tech stack follows constitutional mandates (Django 5.x, DRF, SimpleJWT, Supabase PostgreSQL)
- JWT authentication with patient/doctor roles as specified
- All secrets in .env files
- REST + JSON APIs with standard conventions
- Local development only (no deployment infrastructure)

## Phase 0: Research & Technology Decisions

### Research Summary

Since the TremoAI constitution predefines the entire tech stack, minimal research is required. Key decisions:

**Decision 1: Django Project Structure**
- **Decision**: Four Django apps (authentication, patients, devices, biometrics)
- **Rationale**: Django apps provide natural boundaries for domain models and APIs. Each app maps to a spec entity group, enabling independent testing and clear ownership.
- **Alternatives considered**:
  - Single monolithic app (rejected: poor separation of concerns)
  - Django projects per domain (rejected: violates monorepo principle)

**Decision 2: JWT Token Storage Strategy**
- **Decision**: JWT access tokens (24h expiry) + refresh tokens (7 day expiry)
- **Rationale**: Django SimpleJWT built-in pattern. Access tokens short-lived for security, refresh tokens enable seamless re-authentication.
- **Alternatives considered**:
  - Access tokens only (rejected: poor UX, forces frequent re-login)
  - Session-based auth (rejected: violates JWT constitutional requirement)

**Decision 3: Patient Search Implementation**
- **Decision**: django-filter with Q objects for name search (case-insensitive, partial match)
- **Rationale**: DRF built-in integration, performant for <10k records, PostgreSQL ILIKE support
- **Alternatives considered**:
  - Full-text search (rejected: overkill for name-only search at this scale)
  - Frontend filtering (rejected: requires loading all patients, doesn't scale)

**Decision 4: Device Status Tracking**
- **Decision**: Status field (ENUM: online/offline) + last_seen timestamp on Device model
- **Rationale**: Simple model field updates, no external service needed. Future MQTT integration will trigger status updates.
- **Alternatives considered**:
  - Separate DeviceStatus table (rejected: unnecessary complexity for 2 states)
  - Time-based inference (rejected: requires background job, less reliable)

**Decision 5: Biometric Data Storage Format**
- **Decision**: JSON field for sensor measurements in BiometricSession model
- **Rationale**: PostgreSQL native JSON support, flexible schema for evolving sensor data format, queryable with JSON operators
- **Alternatives considered**:
  - Separate SensorMeasurement table (rejected: complex queries, poor performance for time-series)
  - Binary blob storage (rejected: not queryable, harder to debug)

**Decision 6: API Pagination Strategy**
- **Decision**: DRF PageNumberPagination (50 items per page for biometric sessions, 20 for patients)
- **Rationale**: Standard REST pattern, built into DRF, supports page number and page size parameters
- **Alternatives considered**:
  - Cursor pagination (rejected: better for real-time feeds, unnecessary here)
  - Limit/offset (rejected: less user-friendly than page numbers)

## Phase 1: Data Model & Contracts

See `data-model.md` and `contracts/*.yaml` for complete details.

### Entity Summary

- **CustomUser**: Extends Django AbstractUser with role field (patient/doctor)
- **Patient**: Patient profiles with personal info, medical notes, relationships to doctors
- **DoctorPatientAssignment**: Many-to-many relationship between doctors and patients
- **Device**: Glove hardware with serial number, status, pairing to patient
- **BiometricSession**: Sensor data sessions with timestamp, measurements, aggregation support

### API Endpoint Summary

- **Authentication**: POST /api/auth/register, POST /api/auth/login, POST /api/auth/refresh
- **Patients**: GET/POST /api/patients/, GET/PUT /api/patients/{id}/, GET /api/patients/search/
- **Devices**: GET/POST /api/devices/, GET/PUT /api/devices/{id}/, POST /api/devices/{id}/pair/, PUT /api/devices/{id}/status/
- **Biometrics**: GET/POST /api/biometric-sessions/, GET /api/biometric-sessions/{id}/, GET /api/biometric-sessions/aggregate/

## Phase 2: Task Breakdown

Run `/speckit.tasks` to generate detailed task breakdown in `tasks.md`.

Expected task structure:
- **Phase 1: Setup** - Django project init, app creation, requirements
- **Phase 2: Foundational** - Database config, authentication base, middleware
- **Phase 3: User Story 1 (US1)** - Authentication models, serializers, views, tests
- **Phase 4: User Story 2 (US2)** - Patient models, CRUD views, search, tests
- **Phase 5: User Story 3 (US3)** - Device models, pairing logic, status tracking, tests
- **Phase 6: User Story 4 (US4)** - Biometric models, storage, retrieval, aggregation, tests
- **Phase 7: Polish** - Error handling, validation, documentation, integration tests
