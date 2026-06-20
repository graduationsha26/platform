# Research: CMG Brushless Motor & ESC Initialization (027)

**Date**: 2026-02-18
**Branch**: `027-cmg-esc-init`

---

## Decision 1: MQTT Bidirectional Communication (Publish Motor Commands)

**Decision**: Use the existing `MQTTClient` singleton's paho-mqtt `Client` instance for both subscribing (motor telemetry in) and publishing (motor commands out). Add a `publish_cmg_command(serial_number, command)` method to `MQTTClient`.

**Rationale**:
- MQTT protocol permits one client to both subscribe and publish simultaneously — standard bidirectional design.
- A single client avoids double connection management, double authentication, and double reconnection logic.
- `client.publish()` enqueues messages into the client's internal outgoing queue; `loop_forever()` drains that queue on the next iteration — this is the intended cross-thread publish pattern.
- QoS 1 ("at least once") + idempotent `command_id` UUID achieves the same safety guarantee as QoS 2 without the paho QoS 2 reconnect bug (Issue #276: QoS 2 in-flight publishes during reconnect cause infinite reconnect loop).

**Alternatives considered**:
- Separate publisher client: Rejected — doubles connection overhead, complicates reconnect logic, client_id collision risk.
- QoS 0 (fire-and-forget): Rejected — a dropped stop command could leave the motor running.
- QoS 2 (exactly once): Rejected — paho Issue #276 makes QoS 2 unreliable under reconnects; QoS 1 + deduplication is safer.

**Critical implementation notes**:

1. **External `threading.Lock()` for publish** — paho Issue #354 documents a deadlock when multiple threads call `publish()` concurrently while a callback holds `_callback_mutex`. Wrap all `publish()` calls in an external lock:
   ```python
   self._publish_lock = threading.Lock()
   # ...
   with self._publish_lock:
       result = self.client.publish(topic, payload, qos=1)
   ```

2. **`is_connected` boolean flag** — maintain `self.is_connected = False` updated in `on_connect`/`on_disconnect`. Check before publishing; return `503` to the API caller if disconnected rather than silently enqueuing.

3. **`command_id` UUID in every command payload** — for QoS 1 duplicate deduplication on the glove firmware side:
   ```json
   {"command": "start", "command_id": "<uuid4>", "issued_at": "<ISO timestamp>"}
   ```

4. **NEVER publish from inside MQTT callbacks** (`on_message`, `on_connect`, etc.) — callbacks hold `_callback_mutex`; publishing would cause a deadlock. The existing code already correctly avoids this by using `async_to_sync` for WebSocket broadcasting only.

5. **paho-mqtt 2.x migration** — the existing `mqtt.Client()` constructor without `CallbackAPIVersion` is deprecated in paho-mqtt ≥ 2.0. When adding the publish method, also upgrade: `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)` and update callback signatures. This avoids a breaking change in paho-mqtt 3.0.

6. **`result.rc` check** — `publish()` returns `MQTTMessageInfo`; check `result.rc != mqtt.MQTT_ERR_SUCCESS` immediately and log/return failure. For emergency_stop, implement a short retry loop (max 3 attempts, 1s interval) in a background thread to avoid blocking the HTTP response.

**Topic conventions** (consistent with existing `devices/+/data`, `devices/+/reading`):
- Subscribe for CMG telemetry: `devices/{serial}/cmg_telemetry`
- Subscribe for fault events: `devices/{serial}/cmg_fault`
- Publish motor commands: `devices/{serial}/cmg_command`

**MQTT `on_connect` additions**:
```python
client.subscribe("devices/+/cmg_telemetry")
client.subscribe("devices/+/cmg_fault")
```

**`on_message` dispatch additions** (existing pattern):
```python
elif message_type == 'cmg_telemetry':
    self._handle_cmg_telemetry(payload, serial_number)
elif message_type == 'cmg_fault':
    self._handle_cmg_fault(payload, serial_number)
```

---

## Decision 2: Time-Series Model Design for 1 Hz Motor Telemetry

**Decision**: Simple append-only Django model `MotorTelemetry` with a composite index on `(device_id, timestamp DESC)`. No separate "current state" denormalized table needed at this scale.

**Rationale**:
- At 1 Hz per patient, with ~10 concurrent patients, ingestion rate is ≈10 rows/second = 36,000 rows/hour. PostgreSQL handles millions of rows/second; this is trivial.
- A `ORDER BY timestamp DESC LIMIT 1` query on an indexed `(device_id, timestamp)` composite index returns instantly — no materialized "latest" view needed.
- For charting the last 5 minutes: `filter(device=d, timestamp__gte=now-5min)` on the same index = at most 300 rows; fast.
- Data retention: keep telemetry for 30 days; older rows can be deleted in a background management command. Fault events are kept indefinitely (medical record).

**Index design**:
```python
indexes = [
    models.Index(fields=['device', '-timestamp']),   # latest-by-device query
    models.Index(fields=['patient', '-timestamp']),  # patient history queries
]
```

**Alternatives considered**:
- TimescaleDB hypertable: Rejected — no Docker, no custom PostgreSQL extensions on Supabase free tier; unnecessary at this data volume.
- Denormalized "current state" table: Rejected — adds write complexity (upsert on every 1 Hz tick); a simple indexed query is fast enough.
- Storing telemetry in a JSONField on BiometricSession: Rejected — telemetry arrives continuously, not session-bounded; separate table is cleaner.

---

## Decision 3: New Django App vs. Extending Existing Apps

**Decision**: Create a new `cmg` Django app under `backend/cmg/`.

**Rationale**:
- CMG motor domain (motor state, fault events, commands) is distinct from biometric sensor data (`biometrics`), device registration (`devices`), and MQTT/WebSocket transport (`realtime`).
- Following the existing pattern: each bounded domain has its own app (`biometrics`, `analytics`, `inference`, `patients`).
- Avoids polluting `biometrics` with motor control concepts.
- Migrations stay isolated; no risk of conflicts with existing migrations.

**Alternatives considered**:
- Extend `biometrics`: Rejected — motor state is not a biometric reading; mixing domains makes queries and permissions harder.
- Extend `devices`: Rejected — `devices` is about hardware registration, not operational telemetry.
- Extend `realtime`: Rejected — `realtime` handles transport (MQTT + WebSocket), not data models.

---

## Decision 4: WebSocket Integration — Reuse or New Consumer

**Decision**: Reuse the existing `TremorDataConsumer` and `patient_{patient_id}_tremor_data` channel group. Add a `cmg_telemetry` channel-layer message type and corresponding `cmg_telemetry()` handler method.

**Rationale**:
- The frontend already connects to `ws/tremor-data/{patient_id}/` for IMU + tremor metrics. Adding CMG telemetry to the same stream avoids requiring the frontend to manage a second WebSocket connection per patient.
- Django Channels dispatches channel-layer messages to consumer methods by `type` field: adding `cmg_telemetry` type → `cmg_telemetry()` method is the standard pattern (already used for `tremor_data` and `tremor_metrics_update`).
- Consistent access control: the same JWT + patient access check that guards the existing consumer also gates CMG data.

**Alternatives considered**:
- New `CMGConsumer` on `/ws/cmg-status/{patient_id}/`: Rejected — doubles frontend WebSocket connections; same auth model anyway.
- HTTP polling instead of WebSocket push: Rejected — 1 Hz polling creates unnecessary HTTP overhead; WebSocket push is already in place.

---

## Decision 5: Fault Acknowledgment API Design

**Decision**: REST `POST /api/cmg/faults/{id}/acknowledge/` endpoint (custom action on `MotorFaultViewSet`). Updates `acknowledged=True`, `acknowledged_at=timezone.now()`, `acknowledged_by=request.user`. Returns updated fault record.

**Rationale**:
- Using a dedicated sub-action (`/acknowledge/`) is clearer than a generic PATCH, which could accidentally modify other fields.
- Consistent with DRF `@action(detail=True, methods=['post'])` pattern.
- Only doctors can acknowledge faults (permission enforced by `IsOwnerOrDoctor`).
- Idempotent: acknowledging an already-acknowledged fault is a no-op (returns 200 with current state).

**Alternatives considered**:
- PATCH `{"acknowledged": true}`: Rejected — allows partial update of all fields; less explicit.
- WebSocket command for acknowledgment: Rejected — REST is more appropriate for state-changing operations; WebSocket is for live data push.

---

## Decision 6: Motor Command API Design

**Decision**: REST `POST /api/cmg/commands/` endpoint. Validates device access, publishes MQTT command, returns `{"status": "published", "command": "start", "device_serial": "..."}`. No DB record for commands (fire-and-forward pattern).

**Rationale**:
- Commands are ephemeral — the important artifacts are the resulting telemetry and fault records, not the commands themselves.
- Avoids creating a `MotorCommand` database table for MVP; can be added later if command audit trail is needed.
- The endpoint validates that the requesting doctor has access to the device's patient before publishing.

**Implementation note**: If the MQTT broker is disconnected when a command arrives, return `503 Service Unavailable` with `{"error": "MQTT broker not connected"}` — never silently drop safety commands.

---

## Decision 7: Frontend Component Scope

**Decision**: Three focused components under `frontend/src/components/CMG/`:
1. `CMGStatusPanel.jsx` — live RPM gauge, current draw bar, status badge (receives WebSocket `cmg_telemetry` messages)
2. `CMGFaultAlert.jsx` — dismissible alert card for each unacknowledged fault with "Acknowledge" button
3. `CMGControlPanel.jsx` — Start / Stop / E-Stop buttons (doctor role only; hidden for patient role)

All three are embedded in the patient's monitoring page (existing doctor dashboard page).

**Rationale**: Small, focused components are independently testable. `CMGStatusPanel` works without `CMGControlPanel` (read-only monitoring). `CMGFaultAlert` works independently (fault acknowledgment workflow).

---

## Payload Schemas (MQTT ↔ Glove)

### `devices/{serial}/cmg_telemetry` (glove → backend, 1 Hz)
```json
{
  "timestamp": "2026-02-18T12:00:00.000Z",
  "rpm": 15000,
  "current_a": 2.5,
  "status": "running",
  "fault_type": null
}
```

### `devices/{serial}/cmg_fault` (glove → backend, on fault)
```json
{
  "timestamp": "2026-02-18T12:00:01.000Z",
  "fault_type": "overcurrent",
  "rpm_at_fault": 14800,
  "current_at_fault": 8.2
}
```

### `devices/{serial}/cmg_command` (backend → glove, on doctor action)
```json
{
  "command": "start",
  "timestamp": "2026-02-18T12:00:00.000Z"
}
```
Valid `command` values: `"start"`, `"stop"`, `"emergency_stop"`
