# Data Model: Real-Time Pipeline

**Feature**: Real-Time Pipeline (002-realtime-pipeline)
**Date**: 2026-02-15
**Purpose**: Define entity extensions, message schemas, and relationships for real-time data pipeline

---

## Model Extensions

### BiometricSession (Extended)

**Location**: `backend/biometrics/models.py` (from Feature 001)

**New Fields**:
```python
class BiometricSession(models.Model):
    # Existing fields from Feature 001:
    # - patient (ForeignKey to Patient)
    # - device (ForeignKey to Device)
    # - session_start (DateTimeField)
    # - session_duration (DurationField)
    # - sensor_data (JSONField)
    # - created_at (DateTimeField)

    # NEW FIELDS for Feature 002:
    ml_prediction = models.JSONField(
        null=True,
        blank=True,
        help_text="ML model prediction results (severity, confidence)"
    )
    ml_predicted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when ML prediction was generated"
    )
    received_via_mqtt = models.BooleanField(
        default=False,
        help_text="True if session data arrived via MQTT real-time pipeline"
    )
```

**Field Specifications**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `ml_prediction` | JSONField | Nullable, schema below | Stores ML prediction result |
| `ml_predicted_at` | DateTimeField | Nullable, auto-set on prediction | When prediction was made |
| `received_via_mqtt` | BooleanField | Default False | Distinguishes MQTT vs API-created sessions |

**ML Prediction JSON Schema**:
```json
{
  "severity": "mild" | "moderate" | "severe",
  "confidence": 0.92,
  "model_version": "v1.0",
  "features_used": ["tremor_intensity_avg", "frequency", "duration"]
}
```

**Validation Rules**:
1. If `ml_prediction` is not null, `ml_predicted_at` must be set
2. `severity` must be one of: "mild", "moderate", "severe"
3. `confidence` must be float in range [0.0, 1.0]
4. `ml_predicted_at` must be >= `session_start`

**Indexes** (existing from Feature 001):
```python
class Meta:
    indexes = [
        models.Index(fields=['patient', 'session_start']),
        models.Index(fields=['device', 'session_start']),
    ]
```
(No new indexes required for Feature 002)

---

## MQTT Message Schema

### Incoming Device Data

**MQTT Topic Pattern**: `devices/{serial_number}/data`

**Example Topic**: `devices/GLV123456789/data`

**Message Payload** (JSON):
```json
{
  "serial_number": "GLV123456789",
  "timestamp": "2026-02-15T14:30:00.000Z",
  "tremor_intensity": [0.12, 0.15, 0.18, 0.14, 0.11, 0.13],
  "frequency": 4.5,
  "timestamps": [
    "2026-02-15T14:30:00.000Z",
    "2026-02-15T14:30:00.020Z",
    "2026-02-15T14:30:00.040Z",
    "2026-02-15T14:30:00.060Z",
    "2026-02-15T14:30:00.080Z",
    "2026-02-15T14:30:00.100Z"
  ],
  "session_duration": 100
}
```

**Field Specifications**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `serial_number` | string | Yes | 8-20 alphanumeric | Device serial number (must match topic) |
| `timestamp` | string (ISO 8601) | Yes | Valid UTC datetime | Session start time |
| `tremor_intensity` | array[float] | Yes | Length > 0, values in [0.0, 1.0] | Normalized tremor magnitude readings |
| `frequency` | float | Yes | > 0 | Dominant tremor frequency in Hz |
| `timestamps` | array[string] | Yes | Same length as tremor_intensity, chronologically ordered | Timestamp for each intensity reading |
| `session_duration` | integer | Yes | > 0 | Total session duration in milliseconds |

**Validation Rules**:
1. All fields required (reject message if any missing)
2. `serial_number` must match registered Device in database
3. Device must be paired to a patient (`device.patient` not null)
4. `tremor_intensity` and `timestamps` must have equal length
5. `tremor_intensity` values must be in range [0.0, 1.0]
6. `timestamps` must be chronologically ordered (each >= previous)
7. First timestamp should match `timestamp` field
8. `session_duration` should approximately match time span of `timestamps` array

**Error Handling**:
- **Invalid serial number**: Log warning, reject message
- **Unpaired device**: Log warning, reject message
- **Schema validation failure**: Log error with details, reject message
- **Database write failure**: Log error, retry once, then discard message

---

## WebSocket Message Schemas

### Connection URL Pattern

**URL**: `/ws/tremor-data/{patient_id}/?token={jwt_token}`

**Example**: `/ws/tremor-data/123/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Path Parameters**:
- `patient_id`: Integer (patient primary key)

**Query Parameters**:
- `token`: String (JWT access token for authentication)

---

### Message Type 1: Tremor Data (Backend → Client)

**Sent when**: MQTT message received and validated

**Payload** (JSON):
```json
{
  "type": "tremor_data",
  "patient_id": 123,
  "device_serial": "GLV123456789",
  "timestamp": "2026-02-15T14:30:00.000Z",
  "tremor_intensity": [0.12, 0.15, 0.18, 0.14, 0.11, 0.13],
  "frequency": 4.5,
  "session_duration": 100,
  "prediction": {
    "severity": "moderate",
    "confidence": 0.92
  },
  "received_at": "2026-02-15T14:30:00.250Z"
}
```

**Field Specifications**:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `type` | string | Yes | Always "tremor_data" |
| `patient_id` | integer | Yes | Patient primary key |
| `device_serial` | string | Yes | Device serial number |
| `timestamp` | string (ISO 8601) | Yes | Session start time (from device) |
| `tremor_intensity` | array[float] | Yes | Normalized tremor readings |
| `frequency` | float | Yes | Tremor frequency in Hz |
| `session_duration` | integer | Yes | Duration in milliseconds |
| `prediction` | object | **No** (only if ML available) | ML prediction result |
| `prediction.severity` | string | If prediction present | "mild" \| "moderate" \| "severe" |
| `prediction.confidence` | float | If prediction present | Confidence score [0.0, 1.0] |
| `received_at` | string (ISO 8601) | Yes | Server timestamp when data received |

**Notes**:
- `prediction` field omitted if ML service unavailable or prediction failed
- Frontend should gracefully handle absence of `prediction`
- `received_at` allows client to measure end-to-end latency

---

### Message Type 2: Status Update (Backend → Client)

**Sent when**: Connection established, device paired/unpaired, errors

**Payload** (JSON):
```json
{
  "type": "status",
  "status": "connected" | "waiting" | "device_unpaired" | "error",
  "message": "Connected to live monitoring. Waiting for device data...",
  "timestamp": "2026-02-15T14:30:00.000Z"
}
```

**Field Specifications**:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `type` | string | Yes | Always "status" |
| `status` | string | Yes | Status code (see values below) |
| `message` | string | Yes | Human-readable status message |
| `timestamp` | string (ISO 8601) | Yes | Server timestamp |

**Status Values**:
- `"connected"`: WebSocket connection established successfully
- `"waiting"`: Connected, waiting for device to send data
- `"device_unpaired"`: Device was unpaired from patient mid-session
- `"error"`: General error (see message for details)

**Example Status Messages**:

**On Connect**:
```json
{
  "type": "status",
  "status": "connected",
  "message": "Connected to live monitoring for patient 123. Waiting for device data...",
  "timestamp": "2026-02-15T14:30:00.000Z"
}
```

**Device Unpaired**:
```json
{
  "type": "status",
  "status": "device_unpaired",
  "message": "Device GLV123456789 was unpaired from patient. Live monitoring stopped.",
  "timestamp": "2026-02-15T14:35:00.000Z"
}
```

---

### Message Type 3: Error (Backend → Client)

**Sent when**: Authentication failure, authorization failure, internal error

**Payload** (JSON):
```json
{
  "type": "error",
  "error_code": "unauthorized" | "forbidden" | "internal_error",
  "error_message": "Invalid or expired authentication token",
  "timestamp": "2026-02-15T14:30:00.000Z"
}
```

**Field Specifications**:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `type` | string | Yes | Always "error" |
| `error_code` | string | Yes | Machine-readable error code |
| `error_message` | string | Yes | Human-readable error description |
| `timestamp` | string (ISO 8601) | Yes | Server timestamp |

**Error Codes**:
- `"unauthorized"`: Invalid or expired JWT token (close code 4401)
- `"forbidden"`: User lacks access to patient data (close code 4403)
- `"internal_error"`: Server-side error (close code 4500)

**Note**: Error message is sent before closing connection.

---

### Message Type 4: Ping/Pong (Client ↔ Backend)

**Sent when**: Client periodically pings to keep connection alive

**Client → Backend (Ping)**:
```json
{
  "type": "ping",
  "timestamp": "2026-02-15T14:30:00.000Z"
}
```

**Backend → Client (Pong)**:
```json
{
  "type": "pong",
  "timestamp": "2026-02-15T14:30:00.050Z"
}
```

**Purpose**: Keeps WebSocket connection alive, detects dead connections

**Frequency**: Client should ping every 30 seconds if no data received

---

## Channel Layer Group Naming

### Group Name Pattern

**Format**: `patient_{patient_id}_tremor_data`

**Examples**:
- Patient 123: `patient_123_tremor_data`
- Patient 456: `patient_456_tremor_data`

### Group Lifecycle

**Join Group** (in WebSocket consumer `connect()`):
```python
await self.channel_layer.group_add(
    f"patient_{patient_id}_tremor_data",
    self.channel_name
)
```

**Send to Group** (in MQTT subscriber):
```python
async_to_sync(channel_layer.group_send)(
    f"patient_{patient_id}_tremor_data",
    {
        "type": "tremor.data",  # Maps to tremor_data() method
        "message": json.dumps(sensor_data)
    }
)
```

**Leave Group** (in WebSocket consumer `disconnect()`):
```python
await self.channel_layer.group_discard(
    f"patient_{patient_id}_tremor_data",
    self.channel_name
)
```

---

## Data Flow Diagram

```
[Glove Device]
     |
     | MQTT publish to devices/{serial}/data
     v
[MQTT Broker] (external)
     |
     | MQTT subscribe
     v
[Django MQTT Subscriber] (management command)
     |
     |-- Validate serial_number, device pairing
     |-- Query Device/Patient models
     |-- Generate ML prediction (optional)
     |-- Store to BiometricSession (extended model)
     |-- Send to channel layer group
     v
[Redis Channel Layer]
     |
     | group_send to patient_{id}_tremor_data
     v
[Django Channels WebSocket Consumer]
     |
     |-- Authenticate JWT token
     |-- Authorize patient access
     |-- Join channel group
     |-- Receive from group
     |-- Serialize to JSON
     v
[Frontend Client] (browser WebSocket)
     |
     v
[React Live Monitoring Component] (out of scope for Feature 002)
```

---

## Database Migrations

### Migration 002-01: Extend BiometricSession

**File**: `backend/biometrics/migrations/0002_biometric_session_ml_fields.py`

**Operations**:
1. Add `ml_prediction` JSONField (nullable)
2. Add `ml_predicted_at` DateTimeField (nullable)
3. Add `received_via_mqtt` BooleanField (default False)

**Rollback**: Safe - fields are nullable, no data loss on rollback

---

## Entity Relationships

```
+------------------+
|    CustomUser    |
|   (Feature 001)  |
+------------------+
        |
        | patient/doctor roles
        v
+------------------+       +------------------+
|     Patient      |       |      Device      |
|  (Feature 001)   |       |  (Feature 001)   |
+------------------+       +------------------+
        |                           |
        | patient FK                | device FK
        |                           |
        +------------+--------------+
                     |
                     v
          +----------------------+
          | BiometricSession     |
          | (Feature 001)        |
          |----------------------|
          | + ml_prediction      | <-- NEW (Feature 002)
          | + ml_predicted_at    | <-- NEW (Feature 002)
          | + received_via_mqtt  | <-- NEW (Feature 002)
          +----------------------+
                     ^
                     |
              Stored by MQTT subscriber
              (Feature 002 runtime component)
```

**Relationships**:
- BiometricSession → Patient (many-to-one, from Feature 001)
- BiometricSession → Device (many-to-one, from Feature 001)
- No new database relationships added in Feature 002
- ML prediction stored as JSON within BiometricSession

---

## Summary

**New Models**: 0 (no new Django models)
**Extended Models**: 1 (BiometricSession + 3 fields)
**MQTT Topics**: 1 (`devices/{serial}/data`)
**WebSocket Endpoints**: 1 (`/ws/tremor-data/{patient_id}/`)
**Message Types**: 4 (tremor_data, status, error, ping/pong)
**Channel Groups**: 1 per patient (`patient_{id}_tremor_data`)

**Key Design Decisions**:
1. Extend existing BiometricSession instead of creating new model
2. Store ML predictions as JSON for flexibility (avoid new tables)
3. Use channel groups for patient isolation
4. Use JWT query parameter for WebSocket auth
5. JSON message format for universal compatibility
