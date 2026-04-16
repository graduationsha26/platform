# Implementation Plan: Backend Architecture Alignment

**Branch**: `039-backend-arch-align` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/039-backend-arch-align/spec.md`

## Summary

Three targeted hardening changes to the Django backend that align it with the TremoAI constitution's security, configuration, and bidirectional MQTT requirements:

1. Replace `IsAuthenticated` with `IsDoctorOrAdmin` on `InferenceAPIView` to enforce role-based access on the ML inference endpoint.
2. Centralize MQTT broker configuration in `settings.py` and add `inference`, `cmg`, and `realtime` named loggers to the `LOGGING` dict.
3. Verify and surface the existing bidirectional MQTT publish functions by migrating their config reads to `django.conf.settings`.

No new apps, no database migrations, no frontend changes.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels  
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts (no frontend changes in this feature)  
**Database**: Supabase PostgreSQL (remote) — no schema changes  
**Authentication**: JWT (SimpleJWT) with roles `doctor`/`admin`  
**Testing**: pytest (backend)  
**Project Type**: monorepo (`backend/`, `frontend/`, `firmware/`)  
**Real-time**: Django Channels WebSocket — no changes  
**Integration**: Bidirectional MQTT (verifying publish path; subscribe path already works)  
**AI/ML**: scikit-learn (`.pkl`) and TensorFlow/Keras (`.h5`) served via `inference` app — endpoint permission change only  
**Performance Goals**: No change — permission check adds <1ms per request  
**Constraints**: Local development only; no Docker/CI/CD  
**Scale/Scope**: Single backend process; changes are code-only (no infra)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes in `backend/` — no new directories
- [x] **Tech Stack Immutability**: Uses only DRF permission classes + Django LOGGING + `python-decouple` — all already in stack
- [x] **Database Strategy**: No model or migration changes
- [x] **Authentication**: Strengthening JWT role enforcement (`IsDoctorOrAdmin`) — fully aligned
- [x] **Security-First**: Story 2 moves MQTT credentials out of scattered `config()` calls into `settings.py` — directly satisfies Principle V
- [x] **Real-time Requirements**: No WebSocket changes; existing Django Channels setup unchanged
- [x] **MQTT Integration**: Story 3 verifies and wires bidirectional publish functions — directly satisfies constitution's MQTT bidirectionality rule
- [x] **AI Model Serving**: Inference app structure unchanged; only permission class changes
- [x] **API Standards**: Existing endpoint contract preserved; adds 403 response code which was always correct per REST standards
- [x] **Development Scope**: Local development only — no Docker, no CI/CD

**Result**: ✅ PASS — no violations

## Project Structure

### Documentation (this feature)

```text
specs/039-backend-arch-align/
├── plan.md              ← this file
├── spec.md              ← feature specification
├── research.md          ← Phase 0 decisions
├── data-model.md        ← config entities (no DB schema changes)
├── quickstart.md        ← integration verification scenarios
├── contracts/
│   └── inference-api.yaml  ← inference endpoint with 403 documented
└── checklists/
    └── requirements.md  ← spec quality checklist (all pass)
```

### Source Code — Files Modified

```text
backend/
├── inference/
│   └── views.py                  ← MODIFY: IsAuthenticated → IsDoctorOrAdmin
├── realtime/
│   └── mqtt_client.py            ← MODIFY: __init__ reads from django.conf.settings
│                                   (publish functions already correct — no change)
└── tremoai_backend/
    └── settings.py               ← MODIFY: add MQTT_* entries + inference/cmg/realtime loggers
```

**No files created. No migrations. No frontend changes.**

## Phase 0: Research Findings

*See `research.md` for full decision rationale.*

| # | Decision | Outcome |
|---|----------|---------|
| 1 | Apply `IsDoctorOrAdmin` to `InferenceAPIView` | Use existing class from `authentication/permissions.py`; single-line change |
| 2 | Centralize MQTT config in `settings.py` | Add 3 `config()` entries; update `MQTTClient.__init__` to read from `settings` |
| 3 | Add named loggers for `inference`, `cmg`, `realtime` | 12-line addition to `LOGGING['loggers']`; child loggers auto-route correctly |
| 4 | Bidirectional publish functions | Already implemented; no new code needed; covered by Decision 2 config fix |

## Phase 1: Design

### User Story 1 — Secure the ML Inference API

**File**: `backend/inference/views.py`

**Change**: Line 5 — replace import and line 41 — replace `permission_classes`:

```python
# Before
from rest_framework.permissions import IsAuthenticated
...
permission_classes = [IsAuthenticated]

# After
from authentication.permissions import IsDoctorOrAdmin
...
permission_classes = [IsDoctorOrAdmin]
```

**Verification**: DRF calls `check_permissions()` before `post()` executes. `IsDoctorOrAdmin.has_permission()` returns `False` for any role not in `('doctor', 'admin')`, causing DRF to return 403. Unauthenticated requests fail the `is_authenticated` check and return 401.

---

### User Story 2 — Centralize Hardware Config and Logging

**File**: `backend/tremoai_backend/settings.py`

**Addition 1** — MQTT settings (after existing CHANNEL_LAYERS or just before LOGGING):

```python
# MQTT Broker Configuration (Bidirectional — Feature 039)
MQTT_BROKER_URL = config('MQTT_BROKER_URL', default='mqtt://localhost:1883')
MQTT_USERNAME   = config('MQTT_USERNAME', default='')
MQTT_PASSWORD   = config('MQTT_PASSWORD', default='')
```

**Addition 2** — Three new entries in `LOGGING['loggers']` dict (after existing `biometrics` entry):

```python
'inference': {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
    'propagate': False,
},
'cmg': {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
    'propagate': False,
},
'realtime': {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
    'propagate': False,
},
```

---

### User Story 3 — Establish the Bidirectional MQTT Bridge

**File**: `backend/realtime/mqtt_client.py`

**Change**: `MQTTClient.__init__` — replace direct `config()` calls with `settings` references:

```python
# Before
from decouple import config
...
self.broker_url = config('MQTT_BROKER_URL', default='mqtt://localhost:1883')
self.username   = config('MQTT_USERNAME', default='')
self.password   = config('MQTT_PASSWORD', default='')

# After
from django.conf import settings
...
self.broker_url = settings.MQTT_BROKER_URL
self.username   = settings.MQTT_USERNAME
self.password   = settings.MQTT_PASSWORD
```

**Publish functions** (already implemented, no changes needed):
- `publish_cmg_command(serial_number, command)` → `devices/{serial}/cmg_command`
- `publish_servo_command(serial_number, command_data)` → `devices/{serial}/servo_command`
- `publish_servo_config(serial_number, calibration)` → `devices/{serial}/servo_config`
- `publish_pid_config(serial_number, pid_config)` → `devices/{serial}/pid_config`
- `publish_pid_mode(serial_number, mode)` → `devices/{serial}/pid_mode`

All functions: check `self.is_connected`, use `self._publish_lock`, return `False` on failure, log warnings. Fully compliant with FR-006, FR-007, FR-008.

**Logger routing**: `logging.getLogger(__name__)` in `mqtt_client.py` resolves to `realtime.mqtt_client` — a child of the new `realtime` parent logger. Python's logging hierarchy routes child loggers to their parent's handlers automatically when `propagate=True` on the child (default). Since we set `propagate=False` on the parent (`realtime`), the parent handles it and does not further propagate to root. This is correct.

## Post-Design Constitution Check

- [x] All changes fit within existing `backend/` apps
- [x] No new dependencies introduced
- [x] MQTT credentials move into `.env` → settings path — constitution Principle V satisfied
- [x] Permission class uses JWT role field — constitution Principle IV satisfied
- [x] Bidirectional MQTT publish confirmed — constitution MQTT Integration section satisfied

**Result**: ✅ PASS

## Complexity Tracking

No constitution violations. This section is intentionally empty.
