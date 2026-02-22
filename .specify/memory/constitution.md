<!--
Sync Impact Report:
- Version: NEW → 1.0.0
- Type: Initial constitution creation
- Principles added: 5 core principles + 3 supplementary sections
- Modified principles: None (initial creation)
- Added sections: Real-Time & Integration, API Standards, Development Environment
- Removed sections: None
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md (updated with TremoAI-specific Technical Context,
     Constitution Check items, and monorepo Project Structure)
  ✅ .specify/templates/spec-template.md (reviewed - no updates needed, remains generic)
  ✅ .specify/templates/tasks-template.md (reviewed - no updates needed, remains generic)
- Follow-up TODOs: None
-->

# TremoAI Web Platform Constitution

This constitution defines the non-negotiable architectural and technical principles for the TremoAI graduation project - a web platform for doctors to monitor patients using smart wearable gloves for Parkinson's tremor suppression.

## Core Principles

### I. Monorepo Architecture

**Rule**: The platform MUST maintain a monorepo structure with `backend/` (Django) and `frontend/` (React) directories at the repository root.

**Rationale**: Single repository ensures synchronized versioning, simplified dependency management between frontend and backend, and atomic commits for features spanning both layers.

**Non-negotiable constraints**:
- All backend code resides in `backend/` directory
- All frontend code resides in `frontend/` directory
- Shared types/contracts may exist in a `shared/` or `contracts/` directory
- No splitting into separate repositories

### II. Tech Stack Immutability

**Rule**: The technology stack is fixed and MUST NOT be changed without constitutional amendment:

**Backend**:
- Django 5.x
- Django REST Framework
- Django Channels (for WebSocket support)

**Frontend**:
- React 18+
- Vite (build tool)
- Tailwind CSS (styling)
- Recharts (data visualization)

**Rationale**: This is a graduation project with time constraints. Stack stability prevents scope creep, ensures focused learning, and maintains architectural consistency.

### III. Database Strategy

**Rule**: The platform MUST use Supabase PostgreSQL as the sole database.

**Non-negotiable constraints**:
- Remote Supabase PostgreSQL only
- NO local SQLite databases
- NO switching to other database systems (MySQL, MongoDB, etc.)
- Database connection details stored in `.env` files only

**Rationale**: Supabase provides production-grade PostgreSQL with real-time capabilities, authentication helpers, and eliminates local database setup complexity.

### IV. Authentication & Authorization

**Rule**: User authentication MUST use JWT tokens via Django SimpleJWT with role-based access control.

**Non-negotiable constraints**:
- JWT tokens for authentication (no session-based auth)
- Two roles: `doctor` and `admin`
- Role-based access control enforced at API endpoint level
- Tokens must include user role in payload
- Frontend must store tokens securely and include in API requests

**Rationale**: JWT provides stateless authentication suitable for real-time applications, role-based access ensures proper access control for doctors and platform administrators.

### V. Security-First Configuration

**Rule**: All sensitive configuration MUST use environment variables via `.env` files. Secrets MUST NEVER be hardcoded.

**Non-negotiable constraints**:
- Database credentials in `.env`
- JWT secret keys in `.env`
- MQTT broker credentials in `.env`
- API keys (if any) in `.env`
- `.env` files MUST be in `.gitignore`
- `.env.example` files with placeholder values for documentation

**Rationale**: Prevents credential leaks, enables environment-specific configuration, and follows security best practices for credential management.

## Real-Time & Integration Requirements

### WebSocket Real-Time Data

**Rule**: Live tremor data streaming MUST use Django Channels WebSocket connections.

**Requirements**:
- Django Channels configured for WebSocket support
- Real-time tremor data pushed from backend to frontend via WebSocket
- Connection authenticated using JWT tokens
- Graceful handling of connection drops and reconnection

### MQTT Integration

**Rule**: The backend MUST subscribe to an MQTT broker to receive incoming sensor data from the glove hardware.

**Requirements**:
- Django application subscribes to MQTT topics for glove sensor data
- MQTT broker connection details in `.env` files
- Sensor data processed and stored in PostgreSQL
- Real-time data forwarded to connected WebSocket clients

### AI Model Serving

**Rule**: AI/ML models MUST be served via Django backend. Supported formats:
- scikit-learn models (`.pkl` files)
- TensorFlow/Keras models (`.h5` files)

**Requirements**:
- Models stored in `backend/models/` directory (excluded from git via `.gitignore`)
- Model inference performed server-side, never in browser
- Predictions returned via REST API endpoints

## API Standards

**Rule**: All API endpoints MUST follow REST conventions and return JSON responses.

**Non-negotiable constraints**:
- RESTful endpoint design (`/api/patients/`, `/api/tremor-data/`, etc.)
- JSON request/response bodies only
- Standard HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- Error responses must include `{ "error": "message" }` format
- Pagination for list endpoints
- Consistent naming (snake_case for JSON keys)

**Rationale**: REST + JSON provides universal compatibility, predictable API behavior, and simplifies frontend-backend contract.

## Development Environment

**Rule**: This is a local development project ONLY. Production deployment is out of scope.

**Non-negotiable constraints**:
- NO Docker containerization
- NO CI/CD pipelines
- NO production deployment configurations
- NO infrastructure-as-code (Terraform, etc.)
- Development servers only (`python manage.py runserver`, `npm run dev`)

**Rationale**: This is a graduation project focused on feature implementation and demonstration. DevOps complexity is explicitly excluded to maintain scope and timeline.

## Governance

**Amendment Process**:
- Constitutional changes require explicit discussion and approval
- Version bumps follow semantic versioning (MAJOR.MINOR.PATCH)
- All amendments must update this document with rationale

**Compliance**:
- All feature specifications must be validated against these principles
- Planning phase includes constitutional compliance check
- Violations must be explicitly justified or rejected

**Enforcement**:
- `/speckit.plan` command validates features against constitution
- Feature plans must document any principle conflicts
- Unjustified violations block feature implementation

**Version**: 1.0.0 | **Ratified**: 2026-02-15 | **Last Amended**: 2026-02-15
