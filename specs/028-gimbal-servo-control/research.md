# Research: CMG Gimbal Servo Control (Feature 028)

**Branch**: `028-gimbal-servo-control`
**Date**: 2026-02-19
**Status**: Complete — all unknowns resolved

---

## Decision 1: GimbalCalibration Model Relationship

**Decision**: Use `OneToOneField(Device, on_delete=CASCADE, related_name='gimbal_calibration')`

**Rationale**: The invariant is structural — each physical glove has exactly one calibration configuration. A `OneToOneField` enforces this at the database level via a unique constraint, making duplicate calibration rows impossible even under concurrent writes. A `ForeignKey` + `get_or_create` alternative shifts that constraint into application code, creating a surface for silent bugs on any code path that calls `.create()` directly.

**Alternatives considered**:
- `ForeignKey` + `get_or_create` in views — rejected because enforcing uniqueness in application code is error-prone; the database constraint is the authoritative gate
- Per-patient (rather than per-device) calibration — rejected because calibration reflects physical hardware variation between individual glove units (manufacturing tolerances), not patient anatomy; devices may be shared or reassigned

---

## Decision 2: Calibration Validation Strategy

**Decision**: Cross-field validation in model `clean()` + DRF serializer `validate()`, called via `full_clean()` in overridden `save()`. Field-level `MinValueValidator`/`MaxValueValidator` for physical plausibility bounds (−180° to +180°).

**Rationale**: Consistent with the established pattern in `Device.clean()` and `BiometricReading` in this codebase. `save()` calling `full_clean()` ensures the gate fires regardless of write path (REST API, management commands, MQTT pipeline in future). Serializer `validate()` provides user-facing structured error responses. Strict inequality (`min < max`) — not `≤` — because a zero-width range causes downstream division-by-zero in normalization and is physically meaningless.

**Alternatives considered**:
- Validation only in serializer — rejected because it allows bypassed writes via shell/management commands
- Validation only in model — rejected because DRF does not automatically call `full_clean()`, producing unhelpful 500 errors instead of structured 400 responses

---

## Decision 3: Calibration Upsert Pattern

**Decision**: `PUT /api/cmg/servo/calibration/{device_pk}/` using Django ORM `update_or_create`, returning HTTP 201 on first creation and HTTP 200 on update.

**Rationale**: The API consumer always intends "set the calibration for this device", not "create a new record." `PUT` with full-document replacement semantics is the correct REST mapping. `update_or_create` is atomic on PostgreSQL, eliminating race conditions. `PATCH` (partial update) is deliberately avoided — partial calibration is dangerous in a medical device context because it creates implicit dependency on the existing persisted state; a doctor updating calibration must always submit a complete configuration.

**Alternatives considered**:
- `@action` on `DeviceViewSet` — rejected to avoid modifying the `devices` app, which is outside this feature's scope; the CMG app's own URL space at `/api/cmg/servo/` is the correct home
- `POST` with explicit create + `PATCH` for updates — rejected for the partial-update safety reason above

---

## Decision 4: Calibration Default Values

**Decision**: `pitch_center=0.0°`, `roll_center=0.0°`, `pitch_min=-30.0°`, `pitch_max=+30.0°`, `roll_min=-20.0°`, `roll_max=+20.0°`, `rate_limit=45.0 deg/s`

**Rationale**: Defaults must be safe enough to use without clinical measurement. Conservative travel ranges (±30° pitch, ±20° roll) force a deliberate calibration step before expanding range. The 45 deg/s default rate limit prevents startling the patient on first use. `center=0.0°` represents anatomical neutral wrist position.

**Alternatives considered**:
- ±45° defaults (matching the spec assumption) — rejected in favor of more conservative ±30°/±20° to enforce explicit clinical calibration; doctor can always widen the range after assessing the patient
- System-wide defaults only (no per-device overrides) — rejected because clinical individualization requires per-device parameters

---

## Decision 5: Rate Limit Enforcement Location

**Decision**: Device firmware enforces rate limiting exclusively. The platform communicates the configured rate limit to the device in every MQTT command payload.

**Rationale**: MQTT QoS 1 guarantees at-least-once delivery but makes no timing guarantees. Platform-side interpolation of intermediate waypoints would produce a burst of stale angles if a network hiccup occurred, defeating the purpose of rate limiting. The only enforcement that can be guaranteed is in the firmware's own control loop (50–100 Hz). The spec assumption (line 105) already documents this explicitly: "The glove device firmware...enforces the rate limit on its side."

**Alternatives considered**:
- Platform-side interpolation via timed waypoints — rejected: QoS 1 re-delivery and out-of-order arrival can cause waypoints to execute in a burst, producing higher velocity than intended
- Dual enforcement (platform + firmware) — rejected: adds complexity with no safety gain since platform-side enforcement provides no guarantee

---

## Decision 6: Rate Limit Storage Location

**Decision**: `rate_limit_deg_per_sec` stored in `GimbalCalibration` (per-device). System-enforced floor and ceiling in `settings.py` sourced from `.env`.

**Rationale**: The spec assumption reads "can be adjusted per device by a doctor" — per-device means it belongs in the calibration record. The system-wide floor/ceiling (e.g., `GIMBAL_RATE_LIMIT_MIN=5.0`, `GIMBAL_RATE_LIMIT_MAX=180.0` in `.env`) provides a safety boundary that no individual device configuration can violate.

**Alternatives considered**:
- System-wide setting only — rejected: does not satisfy FR-003 ("configurable rate limit") and ignores per-device hardware variation
- Separate RateLimit model — rejected: over-engineering for a single scalar value that conceptually belongs with other per-device mechanical parameters

---

## Decision 7: ServoCommand Audit Record Design

**Decision**: `ServoCommand` is a point-in-time snapshot audit record. It stores target angles, a `command_id` UUID, `issued_by`, `issued_at`, `status` (pending/published/failed), and a **snapshot** of the active rate limit and travel range calibration at command time.

**Rationale**: FK to `GimbalCalibration` is insufficient for audit integrity — if a doctor changes the rate limit from 60 to 90 deg/s, historical commands would appear to have used the new limit, falsifying the record. Consistent with the existing `MotorFaultEvent` pattern which snapshots `rpm_at_fault` and `current_at_fault` rather than joining to a mutable config table.

**`is_home_command` flag**: A boolean field marks "move to center" commands, which have no explicit target angles (the firmware uses its own calibrated center). This avoids overloading `target_pitch_deg=0.0` (which would be ambiguous with an explicit 0° command).

**Alternatives considered**:
- FK to GimbalCalibration in ServoCommand — rejected: audit record would reflect current calibration, not calibration at time of command
- Separate HomeCommand model — rejected: over-engineering; a flag on ServoCommand is sufficient

---

## Decision 8: GimbalState — Latest-State-Only Model

**Decision**: A `GimbalState` model stores only the **most recent** servo position per device, updated via `update_or_create` on each MQTT `servo_state` message. Not a time-series table.

**Rationale**: The `servo_state` MQTT topic arrives at 10–50 Hz. Storing every reading would generate 36,000–180,000 records per device per hour. Unlike `MotorTelemetry` (1 Hz, 30-day retention), gimbal position history has no defined clinical use case and no retention requirement in the spec. The latest state is sufficient for the REST "current state" endpoint; historical position data comes from the device firmware or is inferred from servo commands.

**Alternatives considered**:
- Time-series table (like MotorTelemetry) — rejected: 10-50 Hz would create 100× more data than motor telemetry with no clinical justification; management command overhead for purging is disproportionate
- In-memory cache only (no DB) — rejected: a REST endpoint for current state must survive server restarts; the DB row provides that persistence cheaply

---

## Decision 9: MQTT Topic Structure

**Decision**:

| Topic | Direction | QoS | Retain | Purpose |
|-------|-----------|-----|--------|---------|
| `devices/{serial}/servo_state` | Device → Platform | 0 | false | Live position stream (10–50 Hz) |
| `devices/{serial}/servo_command` | Platform → Device | 1 | false | Position setpoint |
| `devices/{serial}/servo_config` | Platform → Device | 1 | true | Calibration settings push |

**Rationale**:
- `servo_state` (QoS 0): High-frequency position stream; a dropped frame is inconsequential; QoS 1 at this rate would flood the broker with ACKs.
- `servo_command` (QoS 1, no retain): Must not be lost; must not be retained (a reconnecting glove must not re-execute a stale setpoint). `command_id` UUID handles QoS 1 duplicate delivery, mirroring `cmg_command`.
- `servo_config` (QoS 1, retained): Configuration is long-lived desired state. Retained message ensures a glove that reconnects immediately receives current calibration without waiting for the platform to re-publish. A `config_version` field in the payload lets the firmware skip re-applying if unchanged.

**Topic naming**: Uses `servo_` prefix consistent with `cmg_` prefix for motor topics. Single `snake_case` token as the third path segment, required by the three-segment dispatcher in `mqtt_client.py:on_message`.

**Alternatives considered**:
- Four-segment topics (e.g., `devices/{serial}/servo/state`) — rejected: would break the existing `on_message` dispatcher which asserts `topic_parts[2]` as the message type
- Dedicated calibration REST-only (no MQTT config push) — rejected: retained MQTT config eliminates the race condition where a glove boots before the platform re-publishes calibration

---

## Decision 10: JSON Payload Schemas

**`servo_state` payload** (device → platform, ~10–50 Hz):
```json
{
  "timestamp": "2026-02-19T10:30:00.000Z",
  "pitch_deg": 12.4,
  "roll_deg": -3.1,
  "pitch_status": "moving",
  "roll_status": "idle"
}
```

**`servo_command` payload** (platform → device, QoS 1):
```json
{
  "command": "set_position",
  "pitch_deg": 15.0,
  "roll_deg": 0.0,
  "command_id": "a3f7c1e2-84b0-4d9e-b1a2-0123456789ab",
  "issued_at": "2026-02-19T10:30:00.000Z"
}
```
For `"home"` command: `"command": "home"`, no angle fields.

**`servo_config` payload** (platform → device, QoS 1, retained):
```json
{
  "pitch_offset_deg": 0.5,
  "roll_offset_deg": -1.2,
  "pitch_max_deg": 45.0,
  "pitch_min_deg": -45.0,
  "roll_max_deg": 30.0,
  "roll_min_deg": -30.0,
  "rate_limit_deg_per_sec": 60.0,
  "config_version": "3",
  "updated_at": "2026-02-19T09:00:00.000Z"
}
```

---

## Existing CMG App Gaps (from codebase exploration)

The following are confirmed missing and must be created in Feature 028:

**Backend (backend/cmg/)**:
- Models: `GimbalCalibration`, `ServoCommand`, `GimbalState`
- Serializers for the three new models
- Views: calibration upsert, servo position/home command, gimbal state read
- URLs: servo URL namespace in `cmg/urls.py`
- Migration: new table definitions

**Backend (backend/realtime/)**:
- `mqtt_client.py`: subscribe to `devices/+/servo_state`, `_handle_servo_state()`, `publish_servo_command()`, `publish_servo_config()`
- `consumers.py`: `servo_state()` WebSocket handler

**Frontend (frontend/src/)**:
- `components/CMG/GimbalControlPanel.jsx` — position command UI
- `components/CMG/GimbalCalibrationPanel.jsx` — calibration form UI
- `components/CMG/GimbalStatusDisplay.jsx` — real-time position monitor
- `services/cmgService.js` — extend with servo API functions
