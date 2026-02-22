# Quickstart: CMG PID Controller Tuning (Feature 029)

**Branch**: `029-pid-tuning` | **Date**: 2026-02-19

This document describes the end-to-end integration scenarios for each user story.
It is intended as a manual integration test guide and a reference for task generation.

---

## Prerequisites

- Feature 028 (Gimbal Servo Control) is fully implemented.
- At least one `Device` exists and is paired to a `Patient`.
- A `doctor` JWT is available. The doctor is assigned to the patient.
- The MQTT broker is running and the Django backend MQTT client is connected.

---

## Scenario 1: Doctor Configures PID Gains (US1)

### 1.1 Get default gains (no prior config)

```http
GET /api/cmg/pid/config/42/
Authorization: Bearer <doctor_jwt>
```

Expected response `200`:
```json
{
  "device_id": 42,
  "kp_pitch": 0.08,
  "ki_pitch": 0.002,
  "kd_pitch": 0.012,
  "kp_roll": 0.06,
  "ki_roll": 0.001,
  "kd_roll": 0.008,
  "config_version": 0,
  "updated_at": null,
  "updated_by_id": null
}
```

*(config_version=0 signals these are synthetic defaults, not a saved record)*

### 1.2 Save first PID configuration

```http
PUT /api/cmg/pid/config/42/
Authorization: Bearer <doctor_jwt>
Content-Type: application/json

{
  "kp_pitch": 0.10,
  "ki_pitch": 0.003,
  "kd_pitch": 0.015,
  "kp_roll": 0.07,
  "ki_roll": 0.002,
  "kd_roll": 0.010
}
```

Expected response `201` (created):
```json
{
  "device_id": 42,
  "kp_pitch": 0.10,
  "ki_pitch": 0.003,
  "kd_pitch": 0.015,
  "kp_roll": 0.07,
  "ki_roll": 0.002,
  "kd_roll": 0.010,
  "config_version": 1,
  "updated_at": "2026-02-19T10:00:00Z",
  "updated_by_id": 7
}
```

Verify MQTT: broker should have a retained message on `devices/{serial}/pid_config` with the gain values.

### 1.3 Update gains (second save)

Repeat PUT with different values. Expected response `200` (updated). Verify `config_version` is now `2`.

### 1.4 Validation rejection

```json
{ "kp_pitch": 0.99, "ki_pitch": 0.003, "kd_pitch": 0.015, "kp_roll": 0.07, "ki_roll": 0.002, "kd_roll": 0.010 }
```

Expected response `400`:
```json
{ "kp_pitch": ["kp_pitch (0.99) exceeds maximum of 0.20."] }
```

Device gains must not change.

### 1.5 Patient role can read (but not write)

```http
GET /api/cmg/pid/config/42/
Authorization: Bearer <patient_jwt>
```
Expected `200`. Same values.

```http
PUT /api/cmg/pid/config/42/
Authorization: Bearer <patient_jwt>
```
Expected `403`.

---

## Scenario 2: Doctor Enables and Disables Suppression (US2)

### 2.1 Check current mode (none active)

```http
GET /api/cmg/pid/mode/42/
Authorization: Bearer <doctor_jwt>
```

Expected `200`:
```json
{
  "device_id": 42,
  "is_active": false,
  "session_id": null,
  "session_uuid": null,
  "started_at": null
}
```

### 2.2 Attempt to enable without PID config

*Requires device 42 to have NO PIDConfig saved.*

```http
POST /api/cmg/pid/sessions/
Authorization: Bearer <doctor_jwt>
Content-Type: application/json

{ "device_id": 42 }
```

Expected `400`:
```json
{ "error": "PID configuration required before enabling suppression. Please configure gains first." }
```

### 2.3 Enable suppression (with gains saved)

*(Ensure gains are saved from Scenario 1 first.)*

```http
POST /api/cmg/pid/sessions/
Authorization: Bearer <doctor_jwt>
Content-Type: application/json

{ "device_id": 42 }
```

Expected `201`:
```json
{
  "id": 1,
  "session_uuid": "a3f7c1e2-...",
  "device_id": 42,
  "patient_id": 15,
  "started_by_id": 7,
  "status": "active",
  "started_at": "2026-02-19T10:05:00Z",
  "ended_at": null,
  "kp_pitch_snap": 0.10,
  "ki_pitch_snap": 0.003,
  ...
}
```

Verify MQTT: broker should have a retained message on `devices/{serial}/pid_mode` with `"mode": "enabled"`.

### 2.4 Verify mode shows active

```http
GET /api/cmg/pid/mode/42/
Authorization: Bearer <doctor_jwt>
```

Expected `200`:
```json
{
  "device_id": 42,
  "is_active": true,
  "session_id": 1,
  "session_uuid": "a3f7c1e2-...",
  "started_at": "2026-02-19T10:05:00Z"
}
```

### 2.5 Attempt duplicate session (conflict)

```http
POST /api/cmg/pid/sessions/
Authorization: Bearer <doctor_jwt>
Content-Type: application/json

{ "device_id": 42 }
```

Expected `409`:
```json
{ "error": "Suppression session already active for this device. Stop it first." }
```

### 2.6 Stop suppression

```http
DELETE /api/cmg/pid/sessions/1/
Authorization: Bearer <doctor_jwt>
```

Expected `200`:
```json
{
  "id": 1,
  "status": "completed",
  "ended_at": "2026-02-19T10:35:00Z",
  ...
}
```

Verify MQTT: `devices/{serial}/pid_mode` retained message updated to `"mode": "disabled"`.

### 2.7 Mode returns inactive

```http
GET /api/cmg/pid/mode/42/
```
Expected `is_active: false`.

---

## Scenario 3: Effectiveness Monitoring (US3)

### 3.1 Device publishes pid_status metrics

*Simulated: MQTT broker receives messages on `devices/{serial}/pid_status`:*
```json
{
  "mode": "enabled",
  "session_id": "a3f7c1e2-...",
  "raw_amplitude_deg": 2.4,
  "residual_amplitude_deg": 0.8,
  "timestamp": "2026-02-19T10:10:00Z"
}
```

After ~10 messages (10 Hz device rate), 1 SuppressionMetric row should be stored (1 Hz downsampling).

The metric should be forwarded immediately to WebSocket clients as `suppression_metric` type.

### 3.2 List sessions with aggregate

After at least 1 minute of active session with metrics:

```http
GET /api/cmg/pid/sessions/?device_id=42
Authorization: Bearer <doctor_jwt>
```

Expected `200`:
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "status": "active",
      "started_at": "2026-02-19T10:05:00Z",
      "avg_raw_amplitude_deg": 2.4,
      "avg_residual_amplitude_deg": 0.8,
      "reduction_pct": 66.7,
      ...
    }
  ]
}
```

`reduction_pct` ≥ 60 should be highlighted as meeting target in the frontend.

### 3.3 Get time-series metrics for a session

```http
GET /api/cmg/pid/sessions/1/metrics/
Authorization: Bearer <doctor_jwt>
```

Expected `200`:
```json
{
  "session_id": 1,
  "session_status": "active",
  "aggregate": {
    "avg_raw_amplitude_deg": 2.4,
    "avg_residual_amplitude_deg": 0.8,
    "reduction_pct": 66.7
  },
  "metrics": [
    { "device_timestamp": "2026-02-19T10:10:00Z", "raw_amplitude_deg": 2.4, "residual_amplitude_deg": 0.8 },
    ...
  ]
}
```

### 3.4 WebSocket live updates

Connect to WebSocket as doctor. After connecting, verify `suppression_metric` messages arrive approximately every second while a session is active.

```json
{
  "type": "suppression_metric",
  "session_id": "a3f7c1e2-...",
  "raw_amplitude_deg": 2.3,
  "residual_amplitude_deg": 0.7,
  "timestamp": "2026-02-19T10:10:01Z"
}
```

---

## Error Scenarios

| Situation | Expected |
|-----------|----------|
| Non-doctor tries PUT /pid/config/ | 403 |
| Non-doctor tries POST /pid/sessions/ | 403 |
| Doctor without patient access tries any endpoint | 403 |
| Unauthenticated request | 401 |
| Device not found | 404 |
| Starting session without PID config | 400 |
| Starting session when one already active | 409 |
| MQTT broker offline on mode change | 503 from session start; session record still created in DB as `active` with MQTT pending |
