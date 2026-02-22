# Implementation Plan: Frontend Authentication & Layout

**Branch**: `009-frontend-auth-layout` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-frontend-auth-layout/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements the foundational frontend authentication and layout infrastructure for the TremoAI platform. It provides JWT-based login and registration pages with role-based access control, protected route guards, and a responsive layout shell with role-specific navigation. The implementation integrates with the existing Django backend authentication API and establishes the UI framework for all authenticated user experiences.

**Primary Components**:
- Login and registration pages with form validation
- JWT token management and secure storage
- Protected route guards with automatic redirects
- Role-based routing (doctor vs patient dashboards)
- Responsive sidebar layout with role-specific menus
- Top bar with user profile and logout functionality

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Not required for this feature (auth is request-response)
**Integration**: REST API integration with existing backend auth endpoints
**Performance Goals**:
  - Login/registration response < 2 seconds
  - Route navigation < 500ms
  - Form validation feedback < 100ms
**Constraints**:
  - Local development only
  - Must work with existing backend authentication API
  - No third-party auth providers
  - Modern browser support only (Chrome, Firefox, Safari, Edge - last 2 versions)
**Scale/Scope**:
  - Support 10 concurrent doctors, 100 patients
  - Single-page application (SPA) architecture
  - Mobile-responsive (320px to 1920px+)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [x] **Monorepo Architecture**: Feature fits in `frontend/` structure ✅
- [x] **Tech Stack Immutability**: Uses React 18+, Vite, Tailwind CSS (constitutional stack) ✅
- [x] **Database Strategy**: No database changes (uses existing Supabase PostgreSQL via backend API) ✅
- [x] **Authentication**: Implements JWT authentication with patient/doctor roles ✅
- [x] **Security-First**: No secrets in frontend (JWT tokens stored securely in browser) ✅
- [x] **Real-time Requirements**: Not applicable (no WebSocket needed for auth flows) ✅
- [x] **MQTT Integration**: Not applicable (no glove data in this feature) ✅
- [x] **AI Model Serving**: Not applicable (no ML models in this feature) ✅
- [x] **API Standards**: Integrates with REST + JSON backend APIs ✅
- [x] **Development Scope**: Local development only (no Docker/CI/CD) ✅

**Result**: ✅ PASS - No constitutional violations. Feature fully compliant with all principles.

## Project Structure

### Documentation (this feature)

```text
specs/009-frontend-auth-layout/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Technical research findings
├── data-model.md        # Phase 1: Frontend state/data structures
├── quickstart.md        # Phase 1: Integration scenarios
├── contracts/           # Phase 1: API contract specifications
│   ├── auth.yaml       # Authentication API endpoints
│   └── user.yaml       # User profile endpoints
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2: Task breakdown (created by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── accounts/                 # Existing Django app (no changes needed for this feature)
│   ├── models.py            # User model (already exists)
│   ├── serializers.py       # Auth serializers (already exists)
│   ├── views.py             # Login/register views (already exists)
│   └── urls.py              # Auth endpoints (already exists)
└── .env                      # Backend config (no changes)

frontend/
├── src/
│   ├── components/
│   │   ├── auth/            # Authentication components (NEW)
│   │   │   ├── LoginForm.jsx
│   │   │   ├── RegisterForm.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── layout/          # Layout components (NEW)
│   │   │   ├── AppLayout.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── TopBar.jsx
│   │   │   └── MobileMenu.jsx
│   │   └── common/          # Shared components (NEW)
│   │       ├── Button.jsx
│   │       ├── Input.jsx
│   │       └── LoadingSpinner.jsx
│   ├── pages/               # Page components (NEW)
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── DoctorDashboard.jsx  # Placeholder for P1
│   │   └── PatientDashboard.jsx # Placeholder for P1
│   ├── contexts/            # React contexts (NEW)
│   │   └── AuthContext.jsx  # Global auth state management
│   ├── services/            # API services (NEW)
│   │   ├── api.js          # Base API client with JWT interceptor
│   │   └── authService.js   # Login/register/logout functions
│   ├── hooks/               # Custom React hooks (NEW)
│   │   ├── useAuth.js      # Hook for accessing auth context
│   │   └── useForm.js      # Generic form validation hook
│   ├── utils/               # Utility functions (NEW)
│   │   ├── tokenStorage.js  # JWT token storage (localStorage)
│   │   ├── validators.js    # Form validation rules
│   │   └── roleHelpers.js   # Role-based logic (menus, redirects)
│   ├── routes/              # Routing configuration (NEW)
│   │   └── AppRoutes.jsx    # React Router setup with protected routes
│   ├── App.jsx              # Root component (MODIFIED)
│   └── main.jsx             # Entry point (MODIFIED)
├── tests/                   # Frontend tests (NEW)
│   ├── auth/
│   │   ├── LoginForm.test.jsx
│   │   └── ProtectedRoute.test.jsx
│   └── layout/
│       └── Sidebar.test.jsx
├── .env.local               # Frontend environment variables (NEW)
└── package.json             # Dependencies (MODIFIED - add react-router-dom)

shared/
└── contracts/               # API contract documentation (reference only)
    ├── auth.yaml
    └── user.yaml
```

**Structure Decision**:
- All frontend code resides in `frontend/src/` following monorepo structure
- Authentication state managed via React Context API (no external state management needed for this scope)
- Component organization by feature (auth/, layout/) and type (pages/, components/)
- API client layer abstracts backend communication with JWT token injection
- JWT tokens stored in localStorage (trade-off: simplicity vs XSS risk; acceptable for graduation project scope)
- React Router v6 for client-side routing with protected route wrapper component
- Tailwind CSS utility classes for styling (no custom CSS files needed)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

**Status**: No constitutional violations. Feature maintains full compliance with TremoAI principles.
