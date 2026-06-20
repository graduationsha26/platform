# WebSocket Contract: CMG Motor Telemetry (Feature 027)

**Endpoint**: `ws/tremor-data/{patient_id}/?token=<JWT>`
**Channel group**: `patient_{patient_id}_tremor_data` (shared with existing tremor data stream)

CMG telemetry is delivered via the existing TremorDataConsumer WebSocket endpoint.
The `cmg_telemetry` message type is added alongside the existing `tremor_data` and `tremor_metrics_update` types.

---

## Server → Client: `cmg_telemetry`

Sent at ~1 Hz when the CMG motor is active. Triggered by MQTT `devices/{serial}/cmg_telemetry` messages received by the backend.

```json
{
  "type": "cmg_telemetry",
  "device_serial": "GLOVE00001",
  "patient_id": 5,
  "timestamp": "2026-02-18T12:00:02.000Z",
  "rpm": 15000,
  "current_a": 2.5,
  "status": "running",
  "fault_type": null
}
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `type` | `"cmg_telemetry"` | Message type discriminator |
| `device_serial` | string | Device serial number |
| `patient_id` | integer | Patient ID |
| `timestamp` | ISO 8601 | Glove-side timestamp |
| `rpm` | integer | Rotor speed in RPM |
| `current_a` | float | Current draw in amperes |
| `status` | string | `idle` / `starting` / `running` / `fault` |
| `fault_type` | string\|null | `overcurrent` / `stall` / null |

---

## Server → Client: `cmg_fault`

Sent once when a fault event is stored. Allows the frontend to immediately display the fault alert without polling.

```json
{
  "type": "cmg_fault",
  "fault_event_id": 7,
  "device_serial": "GLOVE00001",
  "patient_id": 5,
  "occurred_at": "2026-02-18T12:01:00.000Z",
  "fault_type": "overcurrent",
  "rpm_at_fault": 14800,
  "current_at_fault": 8.2
}
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `type` | `"cmg_fault"` | Message type discriminator |
| `fault_event_id` | integer | DB ID of the MotorFaultEvent record |
| `device_serial` | string | Device serial number |
| `patient_id` | integer | Patient ID |
| `occurred_at` | ISO 8601 | Fault timestamp from glove |
| `fault_type` | string | `overcurrent` or `stall` |
| `rpm_at_fault` | integer\|null | RPM at time of fault |
| `current_at_fault` | float\|null | Current at time of fault |

---

## Client → Server: `ping`

Existing keepalive message — no changes. Server responds with `pong`.

---

## Channel Layer Message Types (backend-internal)

These are messages sent by `MQTTClient` → channel layer → `TremorDataConsumer`:

### `cmg_telemetry` (MQTT handler → consumer)
```python
{
    'type': 'cmg_telemetry',
    'message': {
        'type': 'cmg_telemetry',
        'device_serial': 'GLOVE00001',
        'patient_id': 5,
        'timestamp': '2026-02-18T12:00:02.000Z',
        'rpm': 15000,
        'current_a': 2.5,
        'status': 'running',
        'fault_type': None,
    }
}
```

### `cmg_fault` (MQTT handler → consumer)
```python
{
    'type': 'cmg_fault',
    'message': {
        'type': 'cmg_fault',
        'fault_event_id': 7,
        'device_serial': 'GLOVE00001',
        'patient_id': 5,
        'occurred_at': '2026-02-18T12:01:00.000Z',
        'fault_type': 'overcurrent',
        'rpm_at_fault': 14800,
        'current_at_fault': 8.2,
    }
}
```
