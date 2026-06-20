# Implementation Plan: Real-Time Pipeline

**Branch**: `002-realtime-pipeline` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-realtime-pipeline/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The Real-Time Pipeline feature enables continuous data collection from TremoAI glove devices via MQTT, real-time streaming of tremor data to authenticated users via WebSocket, and AI-powered severity predictions displayed alongside raw sensor readings. This feature provides the foundational real-time infrastructure for doctors to monitor patients during live sessions and for patients to receive immediate feedback on their tremor measurements.

**Technical Approach**:
- Django management command (persistent process) subscribes to MQTT broker
- Incoming sensor data validated against Device/Patient models from Feature 001
- Validated data stored in BiometricSession model (extended with ML predictions)
- Django Channels WebSocket consumers handle live monitoring connections
- Channel groups broadcast sensor data to all connected viewers for a patient
- ML prediction service (in-process) generates severity classifications
- Redis channel layer coordinates between MQTT subscriber and WebSocket consumers

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data (paho-mqtt library)
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django
**Channel Layer**: Redis for inter-process communication (Django Channels requirement)
**Performance Goals**:
- WebSocket end-to-end latency <500ms
- ML prediction inference <200ms
- MQTT message processing <100ms
- Support 50 concurrent WebSocket connections
- Support 10 concurrent MQTT device streams at 50Hz
**Constraints**:
- Local development only (no Docker/CI/CD)
- MQTT broker assumed pre-existing (not provisioned by this feature)
- Backend-focused feature (frontend WebSocket client out of scope)
**Scale/Scope**: 10 concurrent doctors, 100 patients, 50 concurrent monitoring sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Check** (before Phase 0): ✅ PASS
**Post-Design Check** (after Phase 1): ✅ PASS

Validate this feature against `.specify/memory/constitution.md` principles:

- [X] **Monorepo Architecture**: Feature fits in `backend/` structure (backend-focused, frontend separate)
- [X] **Tech Stack Immutability**: Uses constitutional stack (Django + Django Channels + paho-mqtt for MQTT)
- [X] **Database Strategy**: Uses Supabase PostgreSQL only (extends BiometricSession model)
- [X] **Authentication**: Uses JWT via SimpleJWT for WebSocket authentication
- [X] **Security-First**: MQTT broker credentials, Redis URL in `.env` files
- [X] **Real-time Requirements**: Uses Django Channels WebSocket for live monitoring (constitutional requirement)
- [X] **MQTT Integration**: Uses MQTT subscription for glove sensor data (constitutional requirement)
- [X] **AI Model Serving**: ML models (`.pkl` or `.h5`) loaded in-process for predictions
- [X] **API Standards**: REST + JSON for any auxiliary endpoints (primary data flow is MQTT → WebSocket)
- [X] **Development Scope**: Local development only (no Docker/CI/CD)

**Result**: ✅ PASS - Full constitutional compliance. No violations.

**Additional Dependencies**:
- Redis server (required for Django Channels channel layer) - assumes local Redis installed
- MQTT broker (e.g., Mosquitto) - assumes pre-existing deployment per spec assumptions
- paho-mqtt Python library (MQTT client for Django)
- channels-redis Python library (Redis channel layer backend)

## Project Structure

### Documentation (this feature)

```text
specs/002-realtime-pipeline/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Technical research and decisions
├── data-model.md        # Phase 1: Entity definitions and relationships
├── quickstart.md        # Phase 1: Integration scenarios for testing
├── contracts/           # Phase 1: WebSocket message schemas
│   └── websocket-messages.yaml
└── tasks.md             # Phase 2: Task breakdown (created by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── realtime/                    # NEW Django app for real-time pipeline
│   ├── __init__.py
│   ├── models.py               # NO new models (extends biometrics.BiometricSession)
│   ├── serializers.py          # WebSocket message serializers
│   ├── consumers.py            # WebSocket consumers for live monitoring
│   ├── routing.py              # WebSocket URL routing
│   ├── mqtt_client.py          # MQTT subscriber service
│   ├── ml_service.py           # ML model loader and prediction service
│   ├── management/
│   │   └── commands/
│   │       └── run_mqtt_subscriber.py  # Management command to start MQTT listener
│   └── tests/
│       ├── test_consumers.py   # WebSocket consumer tests
│       ├── test_mqtt_client.py # MQTT client tests
│       └── test_ml_service.py  # ML prediction tests
├── biometrics/                  # MODIFIED (extends existing app from Feature 001)
│   └── models.py               # ADD ML prediction fields to BiometricSession
├── tremoai_backend/
│   ├── settings.py             # ADD Django Channels, channel layer (Redis), MQTT config
│   ├── asgi.py                 # CONFIGURE ASGI application for Channels
│   └── routing.py              # ADD WebSocket routing to ASGI app
├── models/                      # AI/ML model files (.pkl, .h5) - gitignored
│   ├── tremor_severity_model.pkl  # Assumed to exist
│   └── README.md               # Model documentation
├── requirements.txt             # ADD channels, channels-redis, paho-mqtt, redis
└── .env                         # ADD MQTT_BROKER_URL, MQTT_USERNAME, MQTT_PASSWORD, REDIS_URL

frontend/
├── src/
│   ├── components/
│   │   └── LiveMonitoring/     # OUT OF SCOPE (separate feature)
│   └── services/
│       └── websocketService.js # OUT OF SCOPE (separate feature)
```

**Structure Decision**:
- Create new `backend/realtime/` Django app for MQTT and WebSocket logic
- Extend `backend/biometrics/models.py` to add ML prediction fields to BiometricSession
- Update `backend/tremoai_backend/settings.py` and `asgi.py` for Django Channels configuration
- Frontend components out of scope (this is backend-focused)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitutional violations. All checks pass.

---

## Phase 0: Research & Technical Decisions

**Status**: ✅ COMPLETE

**Research Tasks**:
1. Django Channels + Redis channel layer best practices for production-grade WebSocket
2. paho-mqtt client patterns for persistent MQTT subscription in Django
3. ML model loading and inference optimization (caching, thread-safety)
4. WebSocket authentication patterns with JWT in Django Channels
5. MQTT message schema and validation strategies
6. Django Channels message serialization (JSON vs MessagePack)
7. Error handling and reconnection logic for MQTT subscriber
8. WebSocket group broadcasting patterns for patient isolation
9. Performance optimization: batching database writes from high-frequency MQTT data
10. Testing strategies: mocking MQTT broker and WebSocket connections

**Output**: `research.md` with consolidated findings and decisions

---

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

**Tasks**:
1. **Data Model Design** (`data-model.md`):
   - Extend BiometricSession model with ML prediction fields
   - Define MQTT message schema (incoming sensor data)
   - Define WebSocket message schemas (outgoing to clients)
   - Define channel group naming conventions

2. **API Contracts** (`contracts/websocket-messages.yaml`):
   - WebSocket connection handshake (authentication)
   - Sensor data message format (JSON schema)
   - ML prediction message format (JSON schema)
   - Error/status messages (connection errors, device unpaired)
   - Channel group topics (e.g., `patient_{patient_id}_tremor_data`)

3. **Integration Scenarios** (`quickstart.md`):
   - Scenario 1: MQTT subscriber receives device data → stores to DB
   - Scenario 2: Doctor opens live monitoring → WebSocket connection → receives data
   - Scenario 3: Multiple doctors monitor same patient → all receive broadcast
   - Scenario 4: Device unpaired mid-session → WebSocket clients notified
   - Scenario 5: ML prediction generation and inclusion in broadcast

**Output**: `data-model.md`, `contracts/websocket-messages.yaml`, `quickstart.md`

---

## Phase 2: Task Generation

**Status**: PENDING (requires Phase 1 completion)

**Executed by**: `/speckit.tasks` command (NOT part of `/speckit.plan`)

**Expected Task Categories**:
1. **Setup Tasks**:
   - Install dependencies (channels, channels-redis, paho-mqtt)
   - Configure Django Channels in settings
   - Configure ASGI application
   - Set up Redis channel layer
   - Create realtime/ Django app

2. **User Story 1 (P1) - Data Collection**:
   - Implement MQTT client service
   - Implement management command `run_mqtt_subscriber`
   - Validate incoming MQTT messages against Device/Patient models
   - Extend BiometricSession model with ML prediction fields
   - Store validated sensor data to database
   - Implement error handling and reconnection logic
   - Add logging for MQTT events
   - Write tests for MQTT client

3. **User Story 2 (P2) - Live Monitoring**:
   - Implement WebSocket consumer for live monitoring
   - Configure WebSocket routing
   - Implement JWT authentication for WebSocket connections
   - Implement channel group management (join/leave)
   - Broadcast sensor data to channel groups
   - Implement access control (doctors + patient only)
   - Handle WebSocket disconnections
   - Write tests for WebSocket consumer

4. **User Story 3 (P3) - ML Predictions**:
   - Implement ML model loading service
   - Implement prediction generation function
   - Integrate ML prediction into MQTT message processing
   - Include predictions in WebSocket broadcasts
   - Handle ML service failures gracefully
   - Persist predictions to BiometricSession
   - Write tests for ML service

5. **Polish & Integration**:
   - Integration testing (MQTT → DB → WebSocket)
   - Performance testing (latency, concurrency)
   - Update README with setup instructions
   - Document MQTT topic structure
   - Document WebSocket connection procedure

**Output**: `tasks.md` (generated by `/speckit.tasks`)

---

## Notes

### Implementation Priorities

**MVP (User Story 1 only)**:
- MQTT subscriber receives and stores sensor data
- No WebSocket streaming yet
- No ML predictions yet
- Validates foundational data ingestion pipeline

**Increment 2 (+ User Story 2)**:
- Add WebSocket consumers and live monitoring
- Doctors can view real-time data
- Demonstrates full real-time pipeline

**Increment 3 (+ User Story 3)**:
- Add ML prediction generation
- Complete feature with AI insights

### Critical Path Dependencies

1. Redis server must be running locally for Django Channels
2. MQTT broker must be accessible (configuration in .env)
3. Feature 001 (Core Backend APIs) must be deployed (Device, Patient, BiometricSession models)
4. ML model files must be available in `backend/models/` directory

### Testing Strategy

- **Unit Tests**: Mock MQTT client, mock channel layer, mock ML models
- **Integration Tests**: Use in-memory channel layer, use MQTT test broker
- **Manual Testing**: Local Redis + Mosquitto MQTT broker setup

### Security Considerations

- WebSocket connections must validate JWT tokens on connect
- Access control: verify user has access to patient's data stream
- MQTT credentials must be in .env (never committed)
- Redis connection must be localhost-only (no remote Redis in local dev)

### Performance Optimization

- Consider batching high-frequency MQTT messages before database writes
- Cache ML models in memory (load once on startup)
- Use channel layer efficiently (avoid redundant broadcasts)
- Monitor WebSocket message sizes (compress if needed)

### Deployment Notes (Local Development)

1. Start Redis: `redis-server`
2. Start Django dev server: `python manage.py runserver`
3. Start MQTT subscriber: `python manage.py run_mqtt_subscriber` (separate terminal)
4. MQTT subscriber runs as long-running process, must be restarted on code changes

### Future Enhancements (Out of Scope)

- MQTT message queuing for reliability (e.g., RabbitMQ, Kafka)
- Horizontal scaling (multiple MQTT subscribers, distributed channel layer)
- WebSocket compression for high-frequency data
- Historical data replay via WebSocket
- WebSocket client library for frontend (separate feature)
