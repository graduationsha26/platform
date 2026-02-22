# Quickstart: CMG Motor Feature Integration Scenarios (Feature 027)

**Branch**: `027-cmg-esc-init`

These scenarios describe how to validate the CMG motor feature end-to-end once implemented.
Each scenario is independently testable.

---

## Scenario 1: MQTT Telemetry → Database Storage

**What it tests**: CMG telemetry ingestion via MQTT is stored correctly as `MotorTelemetry` records.

**Prerequisites**: Django server running, MQTT broker running, device `GLOVE00001` registered and paired to patient.

**Steps**:
1. Open a Django shell: `python manage.py shell`
2. Publish a simulated CMG telemetry MQTT message:
   ```python
   import paho.mqtt.client as mqtt, json
   c = mqtt.Client()
   c.connect("localhost", 1883)
   payload = {
       "timestamp": "2026-02-18T12:00:00.000Z",
       "rpm": 15000,
       "current_a": 2.5,
       "status": "running",
       "fault_type": None
   }
   c.publish("devices/GLOVE00001/cmg_telemetry", json.dumps(payload))
   c.disconnect()
   ```
3. Verify DB record:
   ```python
   from cmg.models import MotorTelemetry
   t = MotorTelemetry.objects.last()
   assert t.rpm == 15000
   assert t.current_a == 2.5
   assert t.status == 'running'
   assert t.fault_type is None
   print("PASS: Telemetry stored")
   ```

**Expected**: 1 new `MotorTelemetry` row with correct field values.

---

## Scenario 2: MQTT Fault Event → Database + Unacknowledged State

**What it tests**: CMG fault events are stored as `MotorFaultEvent` with `acknowledged=False`.

**Steps**:
1. Publish a simulated fault event:
   ```python
   fault = {
       "timestamp": "2026-02-18T12:01:00.000Z",
       "fault_type": "overcurrent",
       "rpm_at_fault": 14800,
       "current_at_fault": 8.2
   }
   c.publish("devices/GLOVE00001/cmg_fault", json.dumps(fault))
   ```
2. Verify:
   ```python
   from cmg.models import MotorFaultEvent
   f = MotorFaultEvent.objects.last()
   assert f.fault_type == 'overcurrent'
   assert f.acknowledged is False
   assert f.acknowledged_at is None
   print("PASS: Fault stored, unacknowledged")
   ```

**Expected**: 1 new `MotorFaultEvent` row, `acknowledged=False`.

---

## Scenario 3: REST API — Latest Telemetry

**What it tests**: `GET /api/cmg/telemetry/latest/?device_id=1` returns the most recent telemetry record.

**Prerequisites**: At least one `MotorTelemetry` row exists (from Scenario 1). Doctor JWT token available.

**Steps** (using httpie or curl):
```bash
curl -H "Authorization: Bearer <doctor_jwt>" \
     "http://localhost:8000/api/cmg/telemetry/latest/?device_id=1"
```

**Expected response** (`200 OK`):
```json
{
  "id": 1,
  "device_id": 1,
  "patient_id": 5,
  "timestamp": "2026-02-18T12:00:00.000Z",
  "rpm": 15000,
  "current_a": 2.5,
  "status": "running",
  "fault_type": null
}
```

---

## Scenario 4: REST API — Fault Acknowledgment

**What it tests**: `POST /api/cmg/faults/{id}/acknowledge/` marks a fault as acknowledged.

**Steps**:
```bash
# List unacknowledged faults
curl -H "Authorization: Bearer <doctor_jwt>" \
     "http://localhost:8000/api/cmg/faults/?device_id=1&acknowledged=false"

# Acknowledge fault ID 1
curl -X POST \
     -H "Authorization: Bearer <doctor_jwt>" \
     "http://localhost:8000/api/cmg/faults/1/acknowledge/"
```

**Expected**: Response includes `"acknowledged": true` and non-null `acknowledged_at`.

---

## Scenario 5: REST API — Motor Command (Start)

**What it tests**: `POST /api/cmg/commands/` publishes a start command via MQTT.

**Prerequisites**: MQTT broker connected, doctor JWT token.

**Steps**:
```bash
curl -X POST \
     -H "Authorization: Bearer <doctor_jwt>" \
     -H "Content-Type: application/json" \
     -d '{"device_id": 1, "command": "start"}' \
     "http://localhost:8000/api/cmg/commands/"
```

**Expected**:
```json
{
  "status": "published",
  "command": "start",
  "device_serial": "GLOVE00001",
  "published_at": "2026-02-18T12:00:00.000Z"
}
```
Verify on glove simulator/subscriber that the MQTT message arrived on `devices/GLOVE00001/cmg_command`.

---

## Scenario 6: WebSocket — Live CMG Telemetry Stream

**What it tests**: Live `cmg_telemetry` messages arrive on the WebSocket within 2 seconds of MQTT publish.

**Prerequisites**: Doctor authenticated, patient 5 exists, WebSocket connection established.

**Steps**:
1. Connect to WebSocket:
   ```
   ws://localhost:8000/ws/tremor-data/5/?token=<doctor_jwt>
   ```
2. Wait for `{"type": "connected", ...}` message.
3. Publish CMG telemetry via MQTT (as in Scenario 1).
4. Observe that a `cmg_telemetry` message arrives in the WebSocket stream within 2 seconds.

**Expected message**:
```json
{
  "type": "cmg_telemetry",
  "device_serial": "GLOVE00001",
  "patient_id": 5,
  "timestamp": "...",
  "rpm": 15000,
  "current_a": 2.5,
  "status": "running",
  "fault_type": null
}
```

---

## Scenario 7: WebSocket — Fault Alert Push

**What it tests**: A `cmg_fault` message arrives on the WebSocket immediately when a fault event is published via MQTT.

**Steps**:
1. Connect to WebSocket (same as Scenario 6).
2. Publish a fault event via MQTT (as in Scenario 2).
3. Observe that a `cmg_fault` message arrives in the WebSocket stream.

**Expected**:
```json
{
  "type": "cmg_fault",
  "fault_event_id": 7,
  "device_serial": "GLOVE00001",
  "patient_id": 5,
  "occurred_at": "...",
  "fault_type": "overcurrent",
  "rpm_at_fault": 14800,
  "current_at_fault": 8.2
}
```

---

## Scenario 8: Motor Command — MQTT Broker Disconnected

**What it tests**: `POST /api/cmg/commands/` returns `503` when the MQTT broker is not reachable.

**Steps**:
1. Stop the MQTT broker (kill mosquitto process).
2. Wait ~5 seconds for the MQTT client to detect disconnect.
3. Send a motor command:
   ```bash
   curl -X POST \
        -H "Authorization: Bearer <doctor_jwt>" \
        -H "Content-Type: application/json" \
        -d '{"device_id": 1, "command": "stop"}' \
        "http://localhost:8000/api/cmg/commands/"
   ```
4. Expected: `503 Service Unavailable` with `{"error": "MQTT broker not connected. Command not sent."}`.

**Expected**: Command is NOT silently dropped; caller receives explicit error.

---

## Scenario 9: Access Control — Patient Cannot Send Commands

**What it tests**: Patient-role users cannot issue motor commands.

**Steps**:
```bash
curl -X POST \
     -H "Authorization: Bearer <patient_jwt>" \
     -H "Content-Type: application/json" \
     -d '{"device_id": 1, "command": "start"}' \
     "http://localhost:8000/api/cmg/commands/"
```

**Expected**: `403 Forbidden`.

---

## Scenario 10: Frontend CMG Status Panel

**What it tests**: The `CMGStatusPanel` React component displays live RPM and status.

**Steps**:
1. Navigate to patient monitoring page in the browser.
2. Open browser DevTools → Network → WS tab.
3. Confirm `cmg_telemetry` messages arrive and the panel updates within 2 seconds.
4. Verify: RPM gauge shows current RPM, current draw bar shows amperes, status badge updates.
5. Simulate a fault → verify `CMGFaultAlert` appears with "Acknowledge" button.
6. Click "Acknowledge" → verify alert disappears and `POST /api/cmg/faults/{id}/acknowledge/` returned 200.
