# Research: Backend Architecture Alignment

**Branch**: `039-backend-arch-align` | **Date**: 2026-04-12

## Decision 1: Applying IsDoctorOrAdmin to InferenceAPIView

**Decision**: Replace `permission_classes = [IsAuthenticated]` with `permission_classes = [IsDoctorOrAdmin]` in `InferenceAPIView`.

**Rationale**: `IsDoctorOrAdmin` already exists in `backend/authentication/permissions.py` and correctly checks `request.user.role in ('doctor', 'admin')` while also asserting `is_authenticated`. DRF evaluates `permission_classes` before the view body executes, so the rejection happens before any model is loaded. No new class needs to be written.

**Alternatives considered**:
- Writing a new permission class in `inference/permissions.py` — rejected because the class already exists in the shared `authentication` app, which is the correct home for cross-cutting permission logic.
- Using `IsAuthenticated` + manual role check inside the view — rejected because it scatters permission logic into business code and bypasses DRF's standard guard.

**Impact**: Single-line change in `backend/inference/views.py`.

---

## Decision 2: Centralizing MQTT Config in settings.py

**Decision**: Add three settings entries to `backend/tremoai_backend/settings.py` using `python-decouple`'s `config()`:

```python
MQTT_BROKER_URL = config('MQTT_BROKER_URL', default='mqtt://localhost:1883')
MQTT_USERNAME   = config('MQTT_USERNAME', default='')
MQTT_PASSWORD   = config('MQTT_PASSWORD', default='')
```

Then update `MQTTClient.__init__` in `backend/realtime/mqtt_client.py` to read from `django.conf.settings` instead of calling `config()` directly.

**Rationale**: `python-decouple` is already the project's env-loading library (used throughout `settings.py`). Adding MQTT entries to settings.py creates a single authoritative source — other parts of the codebase (e.g., `cmg` app views that might publish commands) can import from `django.conf.settings` without needing to also depend on `decouple`. This satisfies Constitution Principle V (Security-First) and the constitution's MQTT Integration rule.

**Alternatives considered**:
- Leaving `config()` calls in `mqtt_client.py` directly — rejected because it scatters env-reading across the codebase and prevents other modules from referencing the broker address from settings.
- Using `os.environ` directly — rejected; `python-decouple` is the established pattern in this project.

**Impact**: 3-line addition to `settings.py`; 3-line change in `mqtt_client.py.__init__`.

---

## Decision 3: Adding Named Loggers for inference, cmg, realtime

**Decision**: Add three new entries to the `LOGGING['loggers']` dict in `settings.py`:

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

**Rationale**: Django's `LOGGING` dict uses named loggers that Python's `logging` module resolves by hierarchy. Setting `propagate: False` prevents double-logging to the root handler. Setting `level: DEBUG` at the logger level ensures that verbose prediction and hardware command messages are captured during development; the handler level can be tightened later. Both `console` and `file` handlers are already configured; no new handlers are needed.

**Alternatives considered**:
- Using the root logger only — rejected because all app log lines become indistinguishable in output, making it impossible to filter for inference or hardware events.
- Creating separate log files per app — rejected as over-engineering for a local development project; the shared `django.log` file is sufficient.

**Impact**: 12-line addition to `settings.py` `LOGGING['loggers']` dict.

---

## Decision 4: Bidirectional MQTT Publish Functions (Story 3)

**Decision**: Verify and document existing publish functions in `MQTTClient`; no new functions are needed. Update each function to use `settings.MQTT_*` (covered by Decision 2). Ensure the `logger` in `mqtt_client.py` is named `'realtime'` (currently calls `logging.getLogger(__name__)` which resolves to `'realtime.mqtt_client'` — this is a child of the `'realtime'` logger and will route correctly once the parent logger is added to LOGGING).

**Existing publish functions confirmed present**:
- `publish_cmg_command(serial_number, command)` → topic `devices/{serial}/cmg_command`
- `publish_servo_command(serial_number, command_data)` → topic `devices/{serial}/servo_command`
- `publish_servo_config(serial_number, calibration)` → topic `devices/{serial}/servo_config`
- `publish_pid_config(serial_number, pid_config)` → topic `devices/{serial}/pid_config`
- `publish_pid_mode(serial_number, mode)` → topic `devices/{serial}/pid_mode`

All functions already: check `self.is_connected`, return `False` on failure, log warnings. No changes needed beyond the config migration from Decision 2.

**Rationale**: The functions satisfy FR-006, FR-007, and FR-008 as-is. The only gap was config centralization (resolved by Decision 2) and logger routing (resolved by Decision 3).

**Alternatives considered**:
- Moving publish functions to a dedicated `cmg/mqtt_publisher.py` module — deferred; constitutes a refactor beyond this feature's scope.

**Impact**: No new code for publish functions; covered by Decisions 2 and 3.
