# Quickstart: CMG Gimbal Servo Control (Feature 028)

**Branch**: `028-gimbal-servo-control`
**Date**: 2026-02-19

This guide covers the three independently testable integration scenarios that correspond to the three user stories.

---

## Prerequisites

- Backend running: `python manage.py runserver` in `backend/`
- Frontend running: `npm run dev` in `frontend/`
- MQTT broker running (Mosquitto on `localhost:1883`)
- Redis running on `localhost:6379`
- A device with `serial_number = "TESTDEV01"` registered and paired to a patient
- A doctor user with `role = 'doctor'` and access to that patient
- JWT access token for the doctor stored as `$TOKEN`

---

## Scenario 1: US1 — Gimbal Position Control

**Goal**: Doctor sends a position command; the system validates angles against calibration and publishes to MQTT.

### Step 1.1 — Send a valid set_position command

```bash
curl -X POST http://localhost:8000/api/cmg/servo/commands/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": 5, "command": "set_position", "pitch_deg": 20.0, "roll_deg": -5.0}'
```

**Expected response** (HTTP 200):
```json
{
  "success": true,
  "command_id": "a3f7c1e2-...",
  "device_id": 5,
  "command": "set_position",
  "target_pitch_deg": 20.0,
  "target_roll_deg": -5.0,
  "message": "Command published to device"
}
```

**Verify in MQTT broker** (Mosquitto subscriber):
```bash
mosquitto_sub -h localhost -t "devices/TESTDEV01/servo_command" -v
```
Expected payload:
```json
{
  "command": "set_position",
  "pitch_deg": 20.0,
  "roll_deg": -5.0,
  "rate_limit_deg_per_sec": 45.0,
  "pitch_min_deg": -30.0,
  "pitch_max_deg": 30.0,
  "roll_min_deg": -20.0,
  "roll_max_deg": 20.0,
  "command_id": "...",
  "issued_at": "..."
}
```

### Step 1.2 — Send a command that exceeds travel range

```bash
curl -X POST http://localhost:8000/api/cmg/servo/commands/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": 5, "command": "set_position", "pitch_deg": 60.0}'
```

**Expected response** (HTTP 400):
```json
{ "error": "pitch_deg 60.0 exceeds configured maximum of 30.0 for this device." }
```

### Step 1.3 — Send a home command

```bash
curl -X POST http://localhost:8000/api/cmg/servo/commands/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": 5, "command": "home"}'
```

**Expected response** (HTTP 200):
```json
{
  "success": true,
  "command_id": "...",
  "device_id": 5,
  "command": "home",
  "target_pitch_deg": null,
  "target_roll_deg": null,
  "message": "Home command published to device"
}
```

**Verify MQTT payload**:
```json
{
  "command": "home",
  "rate_limit_deg_per_sec": 45.0,
  "pitch_min_deg": -30.0,
  "pitch_max_deg": 30.0,
  "roll_min_deg": -20.0,
  "roll_max_deg": 20.0,
  "command_id": "...",
  "issued_at": "..."
}
```

### Step 1.4 — Verify ServoCommand audit record

```bash
# Via Django shell
python manage.py shell -c "
from cmg.models import ServoCommand
cmd = ServoCommand.objects.latest('issued_at')
print(cmd.command_id, cmd.status, cmd.target_pitch_deg, cmd.rate_limit_snap)
"
```

Expected: `status='published'`, `rate_limit_snap=45.0`

---

## Scenario 2: US2 — Servo Calibration

**Goal**: Doctor sets calibration; values persist and constrain subsequent commands.

### Step 2.1 — Get default calibration (before any calibration set)

```bash
curl http://localhost:8000/api/cmg/servo/calibration/5/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response** (HTTP 200, system defaults):
```json
{
  "device_id": 5,
  "pitch_center_deg": 0.0,
  "roll_center_deg": 0.0,
  "pitch_min_deg": -30.0,
  "pitch_max_deg": 30.0,
  "roll_min_deg": -20.0,
  "roll_max_deg": 20.0,
  "rate_limit_deg_per_sec": 45.0,
  "updated_at": null,
  "updated_by_id": null
}
```

### Step 2.2 — Set calibration

```bash
curl -X PUT http://localhost:8000/api/cmg/servo/calibration/5/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pitch_center_deg": 2.5,
    "roll_center_deg": -1.0,
    "pitch_min_deg": -40.0,
    "pitch_max_deg": 40.0,
    "roll_min_deg": -25.0,
    "roll_max_deg": 25.0,
    "rate_limit_deg_per_sec": 60.0
  }'
```

**Expected response** (HTTP 201 on first call, 200 on update):
```json
{
  "device_id": 5,
  "pitch_center_deg": 2.5,
  "roll_center_deg": -1.0,
  "pitch_min_deg": -40.0,
  "pitch_max_deg": 40.0,
  "roll_min_deg": -25.0,
  "roll_max_deg": 25.0,
  "rate_limit_deg_per_sec": 60.0,
  "updated_at": "2026-02-19T10:00:00Z",
  "updated_by_id": 12
}
```

**Verify MQTT retained message** (calibration pushed to device):
```bash
mosquitto_sub -h localhost -t "devices/TESTDEV01/servo_config" -v --retained-only
```

Expected: retained payload with updated calibration fields.

### Step 2.3 — Verify calibration constrains subsequent command

```bash
# pitch 45° is within new range (±40°)... wait, 45 > 40, should be rejected
curl -X POST http://localhost:8000/api/cmg/servo/commands/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": 5, "command": "set_position", "pitch_deg": 45.0}'
```

**Expected response** (HTTP 400 — 45° exceeds the ±40° range):
```json
{ "error": "pitch_deg 45.0 exceeds configured maximum of 40.0 for this device." }
```

### Step 2.4 — Validation rejects min >= max

```bash
curl -X PUT http://localhost:8000/api/cmg/servo/calibration/5/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pitch_center_deg": 0.0,
    "roll_center_deg": 0.0,
    "pitch_min_deg": 30.0,
    "pitch_max_deg": 30.0,
    "roll_min_deg": -20.0,
    "roll_max_deg": 20.0,
    "rate_limit_deg_per_sec": 45.0
  }'
```

**Expected response** (HTTP 400):
```json
{
  "pitch_min_deg": ["pitch_min_deg (30.0) must be strictly less than pitch_max_deg (30.0)."]
}
```

---

## Scenario 3: US3 — Real-time Gimbal Monitoring

**Goal**: Device publishes servo state; platform stores latest state and broadcasts via WebSocket.

### Step 3.1 — Simulate device publishing servo state

```bash
mosquitto_pub -h localhost -t "devices/TESTDEV01/servo_state" \
  -m '{"timestamp": "2026-02-19T10:30:00.000Z", "pitch_deg": 12.4, "roll_deg": -3.1, "pitch_status": "moving", "roll_status": "idle"}'
```

### Step 3.2 — Verify latest state stored and retrievable via REST

```bash
curl http://localhost:8000/api/cmg/servo/state/5/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response** (HTTP 200):
```json
{
  "device_id": 5,
  "pitch_deg": 12.4,
  "roll_deg": -3.1,
  "pitch_status": "moving",
  "roll_status": "idle",
  "device_timestamp": "2026-02-19T10:30:00.000Z",
  "received_at": "2026-02-19T10:30:00.050Z"
}
```

### Step 3.3 — Verify real-time WebSocket broadcast

Connect to WebSocket (in browser console or wscat):

```bash
wscat -c "ws://localhost:8000/ws/tremor/" \
  -H "Authorization: Bearer $TOKEN"
```

Then publish another servo_state MQTT message (Step 3.1 variant) and observe the WebSocket message:

```json
{
  "type": "servo_state",
  "device_serial": "TESTDEV01",
  "patient_id": 3,
  "pitch_deg": 15.0,
  "roll_deg": -2.0,
  "pitch_status": "idle",
  "roll_status": "idle",
  "device_timestamp": "2026-02-19T10:30:01.000Z"
}
```

### Step 3.4 — Verify fault status via servo_state

```bash
mosquitto_pub -h localhost -t "devices/TESTDEV01/servo_state" \
  -m '{"timestamp": "2026-02-19T10:31:00.000Z", "pitch_deg": 12.4, "roll_deg": -3.1, "pitch_status": "fault", "roll_status": "idle"}'
```

REST response for `/api/cmg/servo/state/5/` should now show `pitch_status: "fault"`.

---

## Error Cases Summary

| Scenario | Input | Expected Response |
|----------|-------|-------------------|
| Angle > max travel | `pitch_deg: 60` with `pitch_max: 30` | 400 out-of-range error |
| Angle < min travel | `pitch_deg: -60` with `pitch_min: -30` | 400 out-of-range error |
| No angles for set_position | `command: set_position` only | 400 missing angle error |
| Patient role issues command | `role: patient` | 403 forbidden |
| Device not paired | device with `patient=null` | 400 not-paired error |
| MQTT broker offline | — | 503 broker unavailable |
| Calibration min >= max | `pitch_min: 30, pitch_max: 30` | 400 validation error |
| Rate limit > system max | `rate_limit_deg_per_sec: 250` | 400 validation error |
| No state yet for device | `GET /servo/state/{id}/` before MQTT | 404 no state yet |
