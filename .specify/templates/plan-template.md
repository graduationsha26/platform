# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Fill in the specific technical details for this feature.

  TremoAI Project Defaults (from constitution):
  - Backend: Django 5.x + Django REST Framework + Django Channels
  - Frontend: React 18+ + Vite + Tailwind CSS + Recharts
  - Database: Supabase PostgreSQL (remote only)
  - Authentication: JWT via Django SimpleJWT (roles: doctor/admin)
  - Real-time & Hardware: Django Channels WebSocket & Bidirectional MQTT
  - AI/ML Serving: Models routed exclusively through Django 'inference' app
  - Testing: pytest (backend), Jest/Vitest (frontend)
  - Project Type: monorepo (backend/, frontend/, firmware/)
-->

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (doctor/admin)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: monorepo (backend/, frontend/, firmware/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: Bidirectional MQTT (ESP32 sensor data in, actuator commands out)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django `inference` app
**Performance Goals**: [domain-specific, e.g., WebSocket latency <100ms, API response <200ms]
**Constraints**: [domain-specific, e.g., local development only, requires ESP32 hardware connection]
**Scale/Scope**: [domain-specific, e.g., 10 concurrent doctors, high-frequency IMU telemetry]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validate this feature against `.specify/memory/constitution.md` principles:

- [ ] **Monorepo Architecture**: Feature fits in `backend/`, `frontend/`, or `firmware/` structure
- [ ] **Tech Stack Immutability**: No new frameworks/libraries outside constitutional stack
- [ ] **Database Strategy**: Uses Supabase PostgreSQL only (no local DB, no other systems)
- [ ] **Authentication**: Uses JWT via SimpleJWT with doctor/admin roles
- [ ] **Security-First**: All secrets in `.env` files, no hardcoded credentials
- [ ] **Real-time Requirements**: Uses Django Channels WebSocket if real-time needed
- [ ] **MQTT Integration**: Uses bidirectional MQTT if ESP32 glove data/control is involved
- [ ] **AI Model Serving**: Models served via Django `inference` backend (`.pkl` or `.h5`)
- [ ] **API Standards**: REST + JSON, standard HTTP codes, snake_case naming
- [ ] **Development Scope**: Local development only (no Docker/CI/CD/production)

**Result**: ✅ PASS / ⚠️ VIOLATIONS REQUIRE JUSTIFICATION (see Complexity Tracking)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  TremoAI uses a monorepo structure with backend/ and frontend/ directories.
  Expand this with the specific files/modules this feature will create or modify.
-->

```text
backend/
├── [app_name]/               # Django app for this feature
│   ├── models.py            # Django models (map to data-model.md entities)
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API views/viewsets
│   ├── urls.py              # URL routing
│   ├── consumers.py         # WebSocket consumers (if real-time)
│   ├── mqtt_handlers.py     # MQTT handlers (if hardware integration)
│   └── services.py          # Business logic
├── inference/                # Dedicated API app for ML model predictions
├── ml_models/models/         # scikit-learn models (.pkl) - gitignored
├── dl_models/models/         # TensorFlow/Keras models (.h5) - gitignored
├── tests/
│   ├── test_models.py
│   ├── test_api.py
│   └── test_websocket.py
└── .env                      # Environment variables (gitignored)

frontend/
├── src/
│   ├── components/           # React components for this feature
│   │   └── [FeatureName]/
│   ├── pages/                # Page components
│   │   └── [FeaturePage].jsx
│   ├── services/             # API client, WebSocket client
│   │   └── [featureService].js
│   ├── hooks/                # Custom React hooks
│   └── utils/                # Utility functions
└── tests/
    └── [feature].test.jsx

firmware/
├── src/                      # ESP32 main logic (main.cpp)
├── include/                  # C++ headers
└── lib/                      # Custom hardware libraries

shared/                       # Optional: shared types/contracts
└── contracts/                # API contract definitions
```

**Structure Decision**: [Document which directories/files this feature creates or modifies.
Reference data-model.md entities, contracts/ endpoints, and specify exact file paths.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
