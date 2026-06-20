# Data Model: CMG PID Controller Tuning (Feature 029)

**Branch**: `029-pid-tuning` | **Date**: 2026-02-19

All entities are added to the existing `backend/cmg/` Django app and stored in Supabase PostgreSQL.

---

## Entities

### PIDConfig

Per-device PID gain configuration. One record per device (OneToOneField). If no record exists, consumers use system defaults read from environment variables.

Mirrors the `GimbalCalibration` pattern from Feature 028.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | Auto PK | — | |
| `device` | OneToOneField → `devices.Device` | CASCADE | One config per device |
| `kp_pitch` | FloatField | 0.0 – 0.20 | Proportional gain, pitch axis |
| `ki_pitch` | FloatField | 0.0 – 0.020 | Integral gain, pitch axis |
| `kd_pitch` | FloatField | 0.0 – 0.050 | Derivative gain, pitch axis |
| `kp_roll` | FloatField | 0.0 – 0.15 | Proportional gain, roll axis |
| `ki_roll` | FloatField | 0.0 – 0.015 | Integral gain, roll axis |
| `kd_roll` | FloatField | 0.0 – 0.040 | Derivative gain, roll axis |
| `config_version` | PositiveIntegerField | default=1, increment on save | Device deduplication |
| `updated_at` | DateTimeField | auto_now | Last save timestamp |
| `updated_by` | FK → `authentication.CustomUser` | SET_NULL, nullable | Audit: who changed |

**DB table**: `cmg_pid_config`

**Validation** (server-side, before persist):
- Each gain must be within its axis-specific max bound from `.env`.
- All values ≥ 0.

**State transitions**: None — single retained record, overwritten on each PUT.

---

### SuppressionSession

A bounded period during which automatic PID suppression was active on a device. Each doctor-initiated enable creates a new session. Provides the audit trail for FR-012 and the session context for SuppressionMetric records.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | Auto PK | — | |
| `session_uuid` | UUIDField | unique, editable=False, default=uuid4 | Shared with device firmware for metric association |
| `device` | ForeignKey → `devices.Device` | CASCADE, db_index=False | Covered by composite index |
| `patient` | ForeignKey → `patients.Patient` | CASCADE, db_index=False | Covered by composite index |
| `started_by` | FK → `authentication.CustomUser` | PROTECT | Doctor who enabled suppression |
| `status` | CharField(12) | choices: active/completed/interrupted | Current session state |
| `started_at` | DateTimeField | auto_now_add | Session start timestamp |
| `ended_at` | DateTimeField | nullable | Set on stop or interrupt |
| `kp_pitch_snap` | FloatField | — | PIDConfig snapshot at start |
| `ki_pitch_snap` | FloatField | — | PIDConfig snapshot at start |
| `kd_pitch_snap` | FloatField | — | PIDConfig snapshot at start |
| `kp_roll_snap` | FloatField | — | PIDConfig snapshot at start |
| `ki_roll_snap` | FloatField | — | PIDConfig snapshot at start |
| `kd_roll_snap` | FloatField | — | PIDConfig snapshot at start |

**DB table**: `cmg_suppression_sessions`

**Indexes**:
- `(device, -started_at)` — list sessions per device
- `(patient, -started_at)` — list sessions per patient
- `(status, -started_at)` — find active sessions efficiently

**State machine**:
```
→ active → completed  (doctor stops session)
         → interrupted (device goes offline, or device reports fault mode)
```
At most one `active` session per device at a time. Starting a second session auto-interrupts the first.

---

### SuppressionMetric

Time-series amplitude readings captured during a suppression session at ~1 Hz (downsampled from device's ~10 Hz stream). Used for aggregate effectiveness reporting and live chart display.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | Auto PK | — | |
| `session` | ForeignKey → `SuppressionSession` | CASCADE, db_index=False | Covered by composite index |
| `device` | ForeignKey → `devices.Device` | PROTECT, db_index=False | Covered by composite index |
| `device_timestamp` | DateTimeField | — | Device-side clock, used for ordering |
| `raw_amplitude_deg` | FloatField | — | RMS tremor amplitude before suppression (degrees) |
| `residual_amplitude_deg` | FloatField | — | RMS tremor amplitude after suppression (degrees) |
| `created_at` | DateTimeField | auto_now_add | Platform receipt time; used for retention cleanup |

**DB table**: `cmg_suppression_metrics`

**Indexes**:
- `(session, device_timestamp)` — per-session aggregate query + live chart fetch
- `(device, device_timestamp)` — device-scoped recent-readings query
- `(created_at)` — 30-day retention cleanup

**Retention**: Delete rows where `created_at < NOW() - 30 days` via `cleanup_pid_metrics` management command.

---

## Relationships

```
devices.Device (1) ──── (0..1) PIDConfig
devices.Device (1) ──── (0..N) SuppressionSession ──── (0..N) SuppressionMetric
patients.Patient (1) ─── (0..N) SuppressionSession
auth.CustomUser (1) ──── (0..N) SuppressionSession  [started_by]
auth.CustomUser (1) ──── (0..1) PIDConfig  [updated_by, nullable]
```

---

## Django App Placement

All three models go in `backend/cmg/models.py`, added after the Feature 028 models under a `# Feature 029: PID Controller Tuning` section comment.

**Migration**: `python manage.py makemigrations cmg --name add_pid_models` → creates `0003_add_pid_models.py`.

---

## Environment Variables (New for Feature 029)

Added to `backend/.env` and `backend/.env.example`:

```bash
# PID gain safe operating bounds — Feature 029
# Pitch axis
PID_KP_PITCH_MAX=0.20
PID_KI_PITCH_MAX=0.020
PID_KD_PITCH_MAX=0.050
# Roll axis
PID_KP_ROLL_MAX=0.15
PID_KI_ROLL_MAX=0.015
PID_KD_ROLL_MAX=0.040
```

Default values (used when no `PIDConfig` record exists):

```bash
PID_KP_PITCH_DEFAULT=0.08
PID_KI_PITCH_DEFAULT=0.002
PID_KD_PITCH_DEFAULT=0.012
PID_KP_ROLL_DEFAULT=0.06
PID_KI_ROLL_DEFAULT=0.001
PID_KD_ROLL_DEFAULT=0.008
```
