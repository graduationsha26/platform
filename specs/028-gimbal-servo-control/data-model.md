# Data Model: CMG Gimbal Servo Control (Feature 028)

**Branch**: `028-gimbal-servo-control`
**Date**: 2026-02-19

---

## Entities

### 1. GimbalCalibration

Stores the calibration parameters for the pitch and roll servo axes of a specific glove device. Exactly one record per device; persists across device power cycles and platform restarts.

**Database table**: `cmg_gimbal_calibration`
**Django app**: `cmg`
**Relationship**: OneToOne with `Device` (not time-series — single row per device)

| Field | Type | Nullable | Default | Constraints |
|-------|------|----------|---------|-------------|
| `id` | BigAutoField (PK) | No | — | Auto |
| `device` | OneToOneField → `devices.Device` | No | — | CASCADE delete, `related_name='gimbal_calibration'` |
| `pitch_center_deg` | FloatField | No | `0.0` | −180 ≤ x ≤ 180 |
| `roll_center_deg` | FloatField | No | `0.0` | −180 ≤ x ≤ 180 |
| `pitch_min_deg` | FloatField | No | `-30.0` | −180 ≤ x ≤ 180; must be < `pitch_max_deg` |
| `pitch_max_deg` | FloatField | No | `30.0` | −180 ≤ x ≤ 180; must be > `pitch_min_deg` |
| `roll_min_deg` | FloatField | No | `-20.0` | −180 ≤ x ≤ 180; must be < `roll_max_deg` |
| `roll_max_deg` | FloatField | No | `20.0` | −180 ≤ x ≤ 180; must be > `roll_min_deg` |
| `rate_limit_deg_per_sec` | FloatField | No | `45.0` | Bounded by `GIMBAL_RATE_LIMIT_MIN` / `GIMBAL_RATE_LIMIT_MAX` in `.env` |
| `updated_at` | DateTimeField | No | — | `auto_now=True` |
| `updated_by` | ForeignKey → `auth.CustomUser` | Yes | `NULL` | `SET_NULL`; nullable because initial defaults may be system-created |

**Validation rules** (enforced in `clean()` + serializer `validate()`):
- `pitch_min_deg < pitch_max_deg` (strict inequality)
- `roll_min_deg < roll_max_deg` (strict inequality)
- `GIMBAL_RATE_LIMIT_MIN ≤ rate_limit_deg_per_sec ≤ GIMBAL_RATE_LIMIT_MAX`

**Access pattern**:
- `device.gimbal_calibration` — retrieve calibration for a device
- Upserted via REST PUT; also pushed to device as retained MQTT `servo_config` message after every save

---

### 2. ServoCommand

Immutable audit record for every servo position command issued through the platform. Captures the doctor's intent, the active calibration snapshot at command time, and the MQTT delivery outcome.

**Database table**: `cmg_servo_commands`
**Django app**: `cmg`
**Relationship**: FK to `Device` and `Patient` (denormalised for query efficiency, consistent with `MotorTelemetry`)

| Field | Type | Nullable | Default | Constraints |
|-------|------|----------|---------|-------------|
| `id` | BigAutoField (PK) | No | — | Auto |
| `command_id` | UUIDField | No | `uuid4` | Unique; firmware deduplication key for QoS 1 re-delivery |
| `device` | ForeignKey → `devices.Device` | No | — | `CASCADE`, no DB index (covered by composite) |
| `patient` | ForeignKey → `patients.Patient` | No | — | `CASCADE`, no DB index (covered by composite) |
| `issued_by` | ForeignKey → `auth.CustomUser` | No | — | `PROTECT`; doctor accountability |
| `issued_at` | DateTimeField | No | — | `auto_now_add=True` |
| `target_pitch_deg` | FloatField | Yes | `NULL` | NULL if axis not commanded |
| `target_roll_deg` | FloatField | Yes | `NULL` | NULL if axis not commanded |
| `is_home_command` | BooleanField | No | `False` | True for move-to-center; when True, target angles are NULL |
| `rate_limit_snap` | FloatField | No | — | Snapshot of `rate_limit_deg_per_sec` at command time |
| `pitch_min_snap` | FloatField | No | — | Snapshot of `pitch_min_deg` at command time |
| `pitch_max_snap` | FloatField | No | — | Snapshot of `pitch_max_deg` at command time |
| `roll_min_snap` | FloatField | No | — | Snapshot of `roll_min_deg` at command time |
| `roll_max_snap` | FloatField | No | — | Snapshot of `roll_max_deg` at command time |
| `status` | CharField(12) | No | `'pending'` | Choices: `pending` / `published` / `failed` |

**Indexes**:
- `cmg_scmd_device_ts_idx` on (`device_id`, `-issued_at`)
- `cmg_scmd_patient_ts_idx` on (`patient_id`, `-issued_at`)

**State transitions**:
```
pending → published   (MQTT publish succeeded)
pending → failed      (MQTT broker unreachable or publish error)
```
Once `published` or `failed`, the record is immutable.

**Invariant**: Either (`is_home_command=True` AND `target_pitch_deg=NULL` AND `target_roll_deg=NULL`) OR (`is_home_command=False` AND at least one of `target_pitch_deg`, `target_roll_deg` is non-NULL).

---

### 3. GimbalState

Stores the **most recent** servo position and axis status received from a device via MQTT. One row per device, updated in-place on every `servo_state` message. Not a time-series table.

**Database table**: `cmg_gimbal_state`
**Django app**: `cmg`
**Relationship**: OneToOne with `Device` (one current-state row per device)

| Field | Type | Nullable | Default | Constraints |
|-------|------|----------|---------|-------------|
| `id` | BigAutoField (PK) | No | — | Auto |
| `device` | OneToOneField → `devices.Device` | No | — | `CASCADE`, `related_name='gimbal_state'` |
| `pitch_deg` | FloatField | No | — | Last reported pitch angle |
| `roll_deg` | FloatField | No | — | Last reported roll angle |
| `pitch_status` | CharField(8) | No | `'idle'` | Choices: `idle` / `moving` / `fault` |
| `roll_status` | CharField(8) | No | `'idle'` | Choices: `idle` / `moving` / `fault` |
| `device_timestamp` | DateTimeField | No | — | Timestamp from device payload |
| `received_at` | DateTimeField | No | — | `auto_now=True` (when platform received it) |

**Access pattern**:
- `device.gimbal_state` — retrieve latest state for a device
- Updated via `update_or_create(device=device, defaults={...})` in the MQTT handler
- Also broadcast to WebSocket channel group on every update

---

## Entity Relationships

```
devices.Device (existing)
│
├── cmg.GimbalCalibration     ── OneToOne (1:1, unique per device)
│   └── updated_by ──────────── auth.CustomUser (nullable)
│
├── cmg.ServoCommand          ── FK (1:N, audit log)
│   ├── patient ──────────────── patients.Patient
│   └── issued_by ───────────── auth.CustomUser
│
└── cmg.GimbalState           ── OneToOne (1:1, latest state per device)

Existing Feature 027 models (unchanged):
├── cmg.MotorTelemetry        ── FK (1:N, time-series)
└── cmg.MotorFaultEvent       ── FK (1:N, fault log)
```

---

## Migration Notes

- New migration file: `backend/cmg/migrations/0002_add_gimbal_models.py`
  (or next available number — check existing migrations)
- Creates tables: `cmg_gimbal_calibration`, `cmg_servo_commands`, `cmg_gimbal_state`
- No changes to existing `cmg_motor_telemetry` or `cmg_motor_fault_events` tables
- No changes to `devices.Device` model

---

## Environment Variables (new for this feature)

Add to `backend/.env` and `backend/.env.example`:

```bash
# Gimbal rate limit safety boundaries (deg/s)
GIMBAL_RATE_LIMIT_MIN_DEG_PER_SEC=5.0
GIMBAL_RATE_LIMIT_MAX_DEG_PER_SEC=180.0
```
