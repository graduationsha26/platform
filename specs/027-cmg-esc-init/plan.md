# Implementation Plan: CMG Brushless Motor & ESC Initialization

**Branch**: `027-cmg-esc-init` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/027-cmg-esc-init/spec.md`

## Summary

Implement CMG (Control Moment Gyroscope) motor monitoring and control on the TremoAI platform. The glove hardware manages ESC PWM, soft-start ramp, overcurrent protection, and stall detection autonomously. The platform backend ingests motor telemetry and fault events via MQTT, stores them in PostgreSQL, streams live state to doctors via WebSocket (reusing the existing `TremorDataConsumer` channel group), exposes historical data and fault management via REST API, and allows doctors to issue motor commands (start/stop/emergency_stop) back to the glove via MQTT. The React frontend adds a CMG status panel, fault alert, and control buttons to the patient monitoring page.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket — reuse existing `patient_{patient_id}_tremor_data` group; add `cmg_telemetry` and `cmg_fault` message types to `TremorDataConsumer`
**Integration**: MQTT — subscribe to `devices/+/cmg_telemetry` and `devices/+/cmg_fault`; publish to `devices/{serial}/cmg_command` (QoS 1)
**Performance Goals**: WebSocket push latency < 2s for 1 Hz telemetry; REST API < 200ms; command publish < 100ms
**Constraints**: Local development only, no Docker/CI/CD; MQTT broker running locally; same MQTT client instance for pub+sub
**Scale/Scope**: ~10 concurrent patients, 1 telemetry row/second/patient = ~36,000 rows/hour total (trivial for PostgreSQL)

## Constitution Check

- [X] **Monorepo Architecture**: New `backend/cmg/` app + `frontend/src/components/CMG/` components
- [X] **Tech Stack Immutability**: No new frameworks; uses existing Django + DRF + Channels + React + Tailwind
- [X] **Database Strategy**: Supabase PostgreSQL only; new migrations in `cmg` app
- [X] **Authentication**: All REST endpoints use `IsAuthenticated + IsOwnerOrDoctor`; WebSocket uses existing JWT auth
- [X] **Security-First**: No new secrets required (reuses `MQTT_BROKER_URL`, `MQTT_USERNAME`, `MQTT_PASSWORD` from `.env`)
- [X] **Real-time Requirements**: Reuses Django Channels `TremorDataConsumer` with new message types
- [X] **MQTT Integration**: Extends existing `MQTTClient` with new topic subscriptions and publish method
- [X] **AI Model Serving**: Not applicable for this feature
- [X] **API Standards**: REST + JSON, snake_case, standard HTTP codes, `{"error": "..."}` format
- [X] **Development Scope**: Local development only

**Result**: ✅ PASS — No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/027-cmg-esc-init/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── cmg-api.yaml     ← REST API OpenAPI spec
│   └── cmg-websocket.md ← WebSocket message contract
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code

```text
backend/
├── cmg/                         ← NEW Django app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                ← MotorTelemetry, MotorFaultEvent
│   ├── serializers.py           ← MotorTelemetrySerializer, MotorFaultEventSerializer
│   ├── views.py                 ← MotorTelemetryViewSet, MotorFaultViewSet, CMGCommandView
│   └── urls.py                  ← /api/cmg/* routing
├── realtime/
│   ├── consumers.py             ← MODIFY: add cmg_telemetry() and cmg_fault() handler methods
│   ├── mqtt_client.py           ← MODIFY: subscribe new topics, add _handle_cmg_telemetry(),
│   │                                       _handle_cmg_fault(), publish_cmg_command()
│   └── cmg_mqtt_handlers.py     ← NEW: _handle_cmg_telemetry + _handle_cmg_fault logic
│                                    (or inline in mqtt_client.py — see Decision below)
├── tremoai_backend/
│   └── urls.py                  ← MODIFY: add path('api/cmg/', include('cmg.urls'))
└── .env                         ← no changes needed (reuses existing MQTT vars)

frontend/
└── src/
    ├── components/
    │   └── CMG/                 ← NEW directory
    │       ├── CMGStatusPanel.jsx   ← Live RPM gauge, current draw, status badge
    │       ├── CMGFaultAlert.jsx    ← Unacknowledged fault card + acknowledge button
    │       └── CMGControlPanel.jsx  ← Start/Stop/E-Stop buttons (doctor role only)
    └── services/
        └── cmgService.js        ← NEW: API calls for telemetry, faults, commands
```

**Key architectural decision**: CMG MQTT handlers are added directly to `mqtt_client.py` following the existing `_handle_session_message` / `_handle_reading_message` pattern rather than creating a separate handler file. This keeps all MQTT dispatch logic in one place.

**WebSocket decision**: Reuse `TremorDataConsumer` (no new consumer class or URL route). Add `cmg_telemetry()` and `cmg_fault()` handler methods — Django Channels maps `type` → method name automatically.

## Phase 0: Research Findings

See [research.md](research.md) for full rationale. Summary of key decisions:

| Question | Decision |
|----------|----------|
| MQTT pub/sub same client? | Yes — `client.publish()` is thread-safe; check `is_connected()` before publish |
| MQTT QoS for commands? | QoS 1 (at least once) — idempotent stop/start; no QoS 2 overhead needed |
| New Django app or extend existing? | New `cmg` app — clean domain separation |
| WebSocket: new consumer or reuse? | Reuse `TremorDataConsumer` — add `cmg_telemetry` + `cmg_fault` message types |
| Time-series model complexity? | Simple append-only model; composite index sufficient at 1 Hz / 10 patients |
| Fault acknowledgment pattern? | DRF `@action(detail=True, methods=['post'])` on MotorFaultViewSet |
| Command DB record? | No — fire-and-forward via MQTT; telemetry provides indirect confirmation |

## Phase 1: Design

### Data Models (see [data-model.md](data-model.md))

**MotorTelemetry** (`cmg_motor_telemetry`):
- `device` FK, `patient` FK (denormalized), `timestamp` DateTimeField
- `rpm` IntegerField, `current_a` FloatField
- `status` CharField choices: `idle/starting/running/fault`
- `fault_type` CharField nullable: `overcurrent/stall/null`
- `received_at` auto_now_add
- Indexes: `(device, -timestamp)`, `(patient, -timestamp)`

**MotorFaultEvent** (`cmg_motor_fault_events`):
- `device` FK, `patient` FK, `occurred_at` DateTimeField
- `fault_type` CharField (overcurrent/stall)
- `rpm_at_fault` IntegerField nullable, `current_at_fault` FloatField nullable
- `acknowledged` BooleanField default=False
- `acknowledged_at` DateTimeField nullable, `acknowledged_by` FK CustomUser nullable
- Indexes: `(device, -occurred_at)`, `(patient, -occurred_at)`, `(acknowledged, -occurred_at)`

### API Contracts (see [contracts/cmg-api.yaml](contracts/cmg-api.yaml))

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cmg/telemetry/` | List telemetry records (filter by device_id or patient_id) |
| GET | `/api/cmg/telemetry/latest/` | Most recent telemetry for a device |
| GET | `/api/cmg/faults/` | List fault events (filter by device_id, patient_id, acknowledged) |
| GET | `/api/cmg/faults/{id}/` | Single fault event detail |
| POST | `/api/cmg/faults/{id}/acknowledge/` | Acknowledge a fault (doctor only) |
| POST | `/api/cmg/commands/` | Send motor command via MQTT (start/stop/emergency_stop) |

### WebSocket Contract (see [contracts/cmg-websocket.md](contracts/cmg-websocket.md))

Reuse endpoint `ws/tremor-data/{patient_id}/`. New message types pushed server→client:
- `cmg_telemetry` — motor state at 1 Hz when running
- `cmg_fault` — immediate fault notification

### MQTT Topics

| Direction | Topic | Trigger |
|-----------|-------|---------|
| Glove → Backend | `devices/{serial}/cmg_telemetry` | Every 1 second when motor active |
| Glove → Backend | `devices/{serial}/cmg_fault` | On each safety fault occurrence |
| Backend → Glove | `devices/{serial}/cmg_command` | On POST /api/cmg/commands/ |

### Frontend Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| `CMGStatusPanel` | `src/components/CMG/` | Live RPM gauge + current draw + status badge |
| `CMGFaultAlert` | `src/components/CMG/` | Fault card list with acknowledge button |
| `CMGControlPanel` | `src/components/CMG/` | Start/Stop/E-Stop buttons (doctor only) |
| `cmgService.js` | `src/services/` | REST API calls (telemetry, faults, acknowledge, commands) |

All three components are embedded in the existing patient monitoring page.

## Complexity Tracking

*No constitution violations — section not needed.*
