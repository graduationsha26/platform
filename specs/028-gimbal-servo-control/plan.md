# Implementation Plan: CMG Gimbal Servo Control

**Branch**: `028-gimbal-servo-control` | **Date**: 2026-02-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/028-gimbal-servo-control/spec.md`

---

## Summary

Extend the existing `cmg` Django app (Feature 027) with dual-axis servo control for the gimbal pitch and roll axes. The platform accepts position commands from doctors, validates them against per-device calibration, and publishes them to the glove via MQTT. A retained MQTT calibration topic keeps the device in sync with platform-side calibration settings. Live gimbal state arrives from the device via MQTT and is broadcast to the doctor's dashboard via WebSocket (extending the existing `TremorDataConsumer`).

Three new database models: `GimbalCalibration` (OneToOne with Device, calibration persistence), `ServoCommand` (audit log with calibration snapshot), and `GimbalState` (latest-state-only, updated by MQTT). Three new REST endpoint groups: servo commands, calibration upsert, and gimbal state read. Three new React components for the doctor dashboard.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) — `doctor` role required for write operations
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: Django Channels WebSocket — extends existing `TremorDataConsumer` with `servo_state` handler
**Integration**: MQTT — extends existing `MQTTClient` with `servo_state` subscription + `servo_command` / `servo_config` publish methods
**Performance Goals**: WebSocket servo state updates < 1 second end-to-end; REST command API response < 200ms
**Constraints**: Local development only; no Docker/CI/CD; rate limiting enforced on device firmware, not platform
**Scale/Scope**: Same as existing CMG feature — 1 device per patient, accessed by 1 doctor at a time

---

## Constitution Check

*GATE: Must pass before implementation.*

- [X] **Monorepo Architecture**: Feature extends `backend/cmg/` and `frontend/src/components/CMG/` — no new top-level directories
- [X] **Tech Stack Immutability**: No new frameworks or libraries — extends DRF, Django Channels, paho-mqtt, React, Tailwind CSS
- [X] **Database Strategy**: Three new models in `cmg` app via Django ORM → Supabase PostgreSQL; no local SQLite
- [X] **Authentication**: JWT doctor role enforced at every write endpoint; GET endpoints accessible to doctors and their patients
- [X] **Security-First**: Two new `.env` variables (`GIMBAL_RATE_LIMIT_MIN_DEG_PER_SEC`, `GIMBAL_RATE_LIMIT_MAX_DEG_PER_SEC`); no secrets hardcoded
- [X] **Real-time Requirements**: Django Channels WebSocket used for live gimbal state — adds `servo_state()` handler to existing `TremorDataConsumer`
- [X] **MQTT Integration**: Extends existing `MQTTClient` — new subscription (`devices/+/servo_state`) and two new publish methods
- [X] **AI Model Serving**: Not applicable — no ML models in this feature
- [X] **API Standards**: REST + JSON, snake_case keys, standard HTTP codes (200/201/400/403/404/503), `{"error": "..."}` format
- [X] **Development Scope**: Local development only — no Docker/CI/CD additions

**Result**: ✅ PASS — No constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/028-gimbal-servo-control/
├── plan.md              ← This file
├── research.md          ← Phase 0 decisions (10 decisions)
├── data-model.md        ← Three new entities
├── quickstart.md        ← Three integration test scenarios
└── contracts/
    ├── servo-command.yaml      ← POST /api/cmg/servo/commands/
    ├── servo-calibration.yaml  ← GET+PUT /api/cmg/servo/calibration/{device_pk}/
    └── gimbal-state.yaml       ← GET /api/cmg/servo/state/{device_pk}/
```

### Source Code

```text
backend/
├── cmg/
│   ├── models.py              MODIFY — add GimbalCalibration, ServoCommand, GimbalState
│   ├── serializers.py         MODIFY — add three new serializers
│   ├── views.py               MODIFY — add GimbalCalibrationView, ServoCommandView, GimbalStateView
│   ├── urls.py                MODIFY — add servo URL patterns under servo/ prefix
│   ├── validators.py          NEW — angle range and calibration validation helpers
│   └── migrations/
│       └── 0002_add_gimbal_models.py   NEW — three new tables
│
└── realtime/
    ├── mqtt_client.py         MODIFY — subscribe servo_state, add publish_servo_command + publish_servo_config
    └── consumers.py           MODIFY — add servo_state() WebSocket handler

frontend/
└── src/
    ├── components/CMG/
    │   ├── GimbalControlPanel.jsx     NEW — pitch/roll position command + home button (doctor only)
    │   ├── GimbalCalibrationPanel.jsx NEW — calibration form for both axes (doctor only)
    │   └── GimbalStatusDisplay.jsx   NEW — live pitch/roll/status display (all roles)
    └── services/
        └── cmgService.js              MODIFY — add servo API functions
```

---

## Architecture Details

### Backend Architecture

#### 1. Models (`backend/cmg/models.py`)

**GimbalCalibration**
- `OneToOneField(Device, CASCADE, related_name='gimbal_calibration')`
- Fields: `pitch_center_deg`, `roll_center_deg`, `pitch_min_deg`, `pitch_max_deg`, `roll_min_deg`, `roll_max_deg`, `rate_limit_deg_per_sec`, `updated_at` (auto_now), `updated_by` (nullable FK)
- Defaults: centers=0.0, pitch ±30°, roll ±20°, rate=45 deg/s
- `clean()`: validates min < max (both axes), rate limit within .env bounds; `save()` calls `full_clean()`

**ServoCommand**
- `ForeignKey(Device, CASCADE)`, `ForeignKey(Patient, CASCADE)` (denormalised)
- `ForeignKey(CustomUser, PROTECT)` as `issued_by`
- `command_id` (UUIDField, unique, default=uuid4)
- `target_pitch_deg` (nullable), `target_roll_deg` (nullable)
- `is_home_command` (BooleanField, default=False)
- Snapshot fields: `rate_limit_snap`, `pitch_min_snap`, `pitch_max_snap`, `roll_min_snap`, `roll_max_snap`
- `status` (pending / published / failed)
- Indexes on (device, -issued_at) and (patient, -issued_at)

**GimbalState**
- `OneToOneField(Device, CASCADE, related_name='gimbal_state')`
- `pitch_deg`, `roll_deg` (FloatField)
- `pitch_status`, `roll_status` (CharField, choices: idle/moving/fault)
- `device_timestamp` (DateTimeField)
- `received_at` (DateTimeField, auto_now)

#### 2. Validators (`backend/cmg/validators.py`)

Extracted validation helpers used by both `GimbalCalibration.clean()` and the DRF serializers:
- `validate_angle_in_range(value, min_deg, max_deg, axis_name)` — raises ValidationError if out of bounds
- `validate_calibration_bounds(data)` — checks min < max for both axes, rate_limit within system bounds

#### 3. Views (`backend/cmg/views.py`)

**GimbalCalibrationView** (`GET`, `PUT` at `/api/cmg/servo/calibration/{device_pk}/`):
- GET: Return calibration or synthetic defaults if no record exists
- PUT: `update_or_create`; 201 on create, 200 on update; after save, call `mqtt_client.publish_servo_config()`; doctor only for PUT

**ServoCommandView** (`POST` at `/api/cmg/servo/commands/`):
- Validate doctor role
- Validate device exists, is paired, doctor has access to patient
- Load (or synthesise) `GimbalCalibration` for the device
- For `set_position`: validate angles within calibrated range; for `home`: no angle validation
- Create `ServoCommand` record with `status='pending'`, snapshot calibration fields
- Call `mqtt_client.publish_servo_command(serial, command_data)`
- Update `ServoCommand.status` to `published` or `failed`
- Return command response

**GimbalStateView** (`GET` at `/api/cmg/servo/state/{device_pk}/`):
- Return `device.gimbal_state` or 404 if no state received yet
- Doctor + patient access (same pattern as `MotorTelemetryViewSet`)

#### 4. URL Routing (`backend/cmg/urls.py`)

```python
# New servo prefix
urlpatterns += [
    path('servo/commands/', ServoCommandView.as_view(), name='cmg-servo-commands'),
    path('servo/calibration/<int:device_pk>/', GimbalCalibrationView.as_view(), name='cmg-servo-calibration'),
    path('servo/state/<int:device_pk>/', GimbalStateView.as_view(), name='cmg-servo-state'),
]
```

#### 5. MQTT Extensions (`backend/realtime/mqtt_client.py`)

**New subscription** (in `on_connect`):
```python
client.subscribe("devices/+/servo_state", qos=0)
```

**New dispatch branch** (in `on_message`):
```python
elif message_type == 'servo_state':
    self._handle_servo_state(payload, serial_number)
```

**`_handle_servo_state(payload, serial_number)`**:
1. `validate_device_pairing(serial_number)` → (device, patient)
2. Parse timestamp
3. `GimbalState.objects.update_or_create(device=device, defaults={...})`
4. `channel_layer.group_send(f'patient_{patient.id}_tremor_data', {'type': 'servo_state', 'message': {...}})`
5. Non-fatal error handling (consistent with existing handlers)

**`publish_servo_command(serial_number, command_data) → bool`**:
- Topic: `devices/{serial}/servo_command`
- Payload: command, pitch_deg, roll_deg (if applicable), rate_limit_deg_per_sec, travel bounds, command_id UUID, issued_at
- QoS 1, retain=False
- Pattern: identical to `publish_cmg_command`

**`publish_servo_config(serial_number, calibration) → bool`**:
- Topic: `devices/{serial}/servo_config`
- Payload: all calibration fields + config_version + updated_at
- QoS 1, retain=**True**
- `config_version`: stored on `GimbalCalibration` model (incrementing integer)

#### 6. WebSocket Extension (`backend/realtime/consumers.py`)

Add `servo_state(self, event)` handler to `TremorDataConsumer`:
```python
async def servo_state(self, event):
    await self.send(text_data=json.dumps(event['message']))
```
Pattern identical to existing `cmg_telemetry` and `cmg_fault` handlers.

### Frontend Architecture

#### `GimbalControlPanel.jsx`
- Doctor-only (`user?.role !== 'doctor'` guard, returns null otherwise)
- Two number inputs (pitch_deg, roll_deg) with min/max pulled from calibration props
- "Set Position" button calls `sendServoCommand(deviceId, 'set_position', { pitch_deg, roll_deg })`
- "Home" button calls `sendServoCommand(deviceId, 'home')`
- Per-button loading state; error display for API failures

#### `GimbalCalibrationPanel.jsx`
- Doctor-only
- Pre-populated form with current calibration (fetched on mount via `getGimbalCalibration(deviceId)`)
- Fields: pitch center, roll center, pitch min/max, roll min/max, rate limit
- Submit calls `setGimbalCalibration(deviceId, data)` (PUT)
- Inline validation: min < max before submit
- Success/error feedback

#### `GimbalStatusDisplay.jsx`
- All roles (no role guard)
- REST fetch on mount: `getGimbalState(deviceId)`
- WebSocket merging: `useEffect` on `latestMessage` prop — applies messages with `type === 'servo_state'`
- Displays: pitch angle (large number), roll angle, per-axis status badge (idle/moving/fault with colors)
- Shows "disconnected" indicator if no state available (null state)

#### `cmgService.js` additions

```javascript
export const sendServoCommand   = (deviceId, command, angles = {}) => api.post('/cmg/servo/commands/', { device_id: deviceId, command, ...angles });
export const getGimbalCalibration = (deviceId) => api.get(`/cmg/servo/calibration/${deviceId}/`);
export const setGimbalCalibration = (deviceId, data) => api.put(`/cmg/servo/calibration/${deviceId}/`, data);
export const getGimbalState       = (deviceId) => api.get(`/cmg/servo/state/${deviceId}/`);
```

---

## Migration Plan

**File**: `backend/cmg/migrations/0002_add_gimbal_models.py`

Creates:
- `cmg_gimbal_calibration` (OneToOne with devices, all calibration fields)
- `cmg_servo_commands` (FK to device + patient, audit fields, snapshot fields)
- `cmg_gimbal_state` (OneToOne with devices, latest state fields)

No existing table modifications.

---

## Environment Variables

Add to `backend/.env` (and `backend/.env.example` with placeholder comments):

```bash
# Gimbal servo safety boundaries (deg/s)
GIMBAL_RATE_LIMIT_MIN_DEG_PER_SEC=5.0
GIMBAL_RATE_LIMIT_MAX_DEG_PER_SEC=180.0
```

---

## Key Technical Decisions (cross-references to research.md)

| Decision | Summary | Research ref |
|----------|---------|-------------|
| Relationship type | OneToOneField for GimbalCalibration | Decision 1 |
| Calibration validation | `clean()` + serializer `validate()` + `full_clean()` in `save()` | Decision 2 |
| Upsert pattern | `PUT` + `update_or_create`, 201/200 response codes | Decision 3 |
| Default values | Conservative defaults (±30°/±20°, 45 deg/s) | Decision 4 |
| Rate limit enforcement | Device firmware only; platform sends rate_limit in every command | Decision 5 |
| Rate limit storage | Per-device in GimbalCalibration, bounded by .env | Decision 6 |
| ServoCommand design | Audit snapshot — no FK to calibration | Decision 7 |
| GimbalState persistence | Latest-state-only (not time-series) | Decision 8 |
| MQTT topics | servo_state (QoS 0), servo_command (QoS 1 no retain), servo_config (QoS 1 retained) | Decision 9 |
| Payload schemas | command_id UUID in commands; config_version in config | Decision 10 |
