# Quickstart Guide: Real-Time Pipeline Integration

**Feature**: Real-Time Pipeline (002-realtime-pipeline)
**Date**: 2026-02-15
**Purpose**: Integration scenarios for testing MQTT + WebSocket real-time data pipeline

---

## Prerequisites

Before running these integration scenarios, ensure:

1. **Feature 001 deployed**: Device, Patient, BiometricSession models available
2. **Redis running**: `redis-server` on localhost:6379
3. **MQTT broker running**: Mosquitto or equivalent on configured host/port
4. **Django configured**: Django Channels, channel layer, ASGI application configured
5. **Environment variables set** in `.env`:
   ```
   MQTT_BROKER_URL=mqtt://localhost:1883
   MQTT_USERNAME=your_username
   MQTT_PASSWORD=your_password
   REDIS_URL=redis://localhost:6379/0
   ```
6. **MQTT subscriber running**: `python manage.py run_mqtt_subscriber` in separate terminal
7. **Django dev server running**: `python manage.py runserver`

---

## Scenario 1: End-to-End Data Flow (Happy Path)

**Objective**: Validate complete pipeline from device → MQTT → database → WebSocket → client

### Setup

1. Create test patient and device (via Feature 001 API):
   ```bash
   # Create patient
   curl -X POST http://localhost:8000/api/patients/ \
     -H "Authorization: Bearer $DOCTOR_JWT" \
     -H "Content-Type: application/json" \
     -d '{
       "full_name": "Test Patient",
       "date_of_birth": "1980-01-01",
       "contact_email": "test@example.com"
     }'
   # Response: {"id": 123, ...}

   # Create device
   curl -X POST http://localhost:8000/api/devices/ \
     -H "Authorization: Bearer $DOCTOR_JWT" \
     -H "Content-Type: application/json" \
     -d '{
       "serial_number": "GLV123456789"
     }'
   # Response: {"id": 456, "serial_number": "GLV123456789", ...}

   # Pair device to patient
   curl -X POST http://localhost:8000/api/devices/456/pair/ \
     -H "Authorization: Bearer $DOCTOR_JWT" \
     -H "Content-Type: application/json" \
     -d '{"patient_id": 123}'
   ```

### Execute

**Step 1**: Establish WebSocket connection (use browser console or `websocat` CLI):
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + jwt_token);

ws.onopen = () => console.log('WebSocket connected');
ws.onmessage = (event) => console.log('Received:', JSON.parse(event.data));
ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = (event) => console.log('WebSocket closed:', event.code, event.reason);
```

**Step 2**: Publish MQTT message (use `mosquitto_pub` CLI):
```bash
mosquitto_pub -h localhost -p 1883 \
  -u your_username -P your_password \
  -t "devices/GLV123456789/data" \
  -m '{
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
  }'
```

### Expected Results

1. **MQTT Subscriber logs** (in `run_mqtt_subscriber` terminal):
   ```
   INFO: Received MQTT message on topic: devices/GLV123456789/data
   INFO: Validated device: GLV123456789 (paired to patient 123)
   INFO: Generated ML prediction: severity=moderate, confidence=0.92
   INFO: Stored BiometricSession: id=789
   INFO: Broadcasting to channel group: patient_123_tremor_data
   ```

2. **Database record created**:
   ```sql
   SELECT * FROM biometric_sessions WHERE id = 789;
   -- patient_id: 123
   -- device_id: 456
   -- sensor_data: {"tremor_intensity": [0.12, 0.15, ...], ...}
   -- ml_prediction: {"severity": "moderate", "confidence": 0.92}
   -- received_via_mqtt: true
   ```

3. **WebSocket client receives message**:
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

4. **Latency metrics**:
   - MQTT publish → Database write: <100ms
   - Database write → WebSocket receive: <400ms
   - **Total end-to-end latency: <500ms** (meets SC-002)

---

## Scenario 2: Multiple Concurrent Viewers

**Objective**: Validate that multiple doctors can monitor the same patient simultaneously

### Setup

Use patient 123 and device GLV123456789 from Scenario 1.

### Execute

**Step 1**: Open 3 WebSocket connections (simulate 3 doctors):
```javascript
// Doctor 1
const ws1 = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + doctor1_jwt);
ws1.onmessage = (e) => console.log('Doctor 1:', JSON.parse(e.data));

// Doctor 2
const ws2 = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + doctor2_jwt);
ws2.onmessage = (e) => console.log('Doctor 2:', JSON.parse(e.data));

// Patient
const ws3 = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + patient_jwt);
ws3.onmessage = (e) => console.log('Patient:', JSON.parse(e.data));
```

**Step 2**: Publish single MQTT message:
```bash
mosquitto_pub -h localhost -p 1883 \
  -u your_username -P your_password \
  -t "devices/GLV123456789/data" \
  -m '{...same payload as Scenario 1...}'
```

### Expected Results

1. **All 3 WebSocket connections receive the same message simultaneously**:
   ```
   Doctor 1: {"type": "tremor_data", "patient_id": 123, ...}
   Doctor 2: {"type": "tremor_data", "patient_id": 123, ...}
   Patient:  {"type": "tremor_data", "patient_id": 123, ...}
   ```

2. **MQTT Subscriber logs show single broadcast to channel group**:
   ```
   INFO: Broadcasting to channel group: patient_123_tremor_data
   INFO: 3 consumers in group received message
   ```

3. **Validates FR-009**: Multiple concurrent viewers per patient

---

## Scenario 3: Patient Data Isolation

**Objective**: Validate that doctors only receive data for their assigned patients

### Setup

1. Create two patients (123, 456) and two devices (GLV1, GLV2)
2. Pair GLV1 to patient 123, GLV2 to patient 456
3. Doctor 1 assigned to patient 123 only
4. Doctor 2 assigned to patient 456 only

### Execute

**Step 1**: Doctor 1 connects to patient 123, Doctor 2 connects to patient 456:
```javascript
// Doctor 1 → Patient 123
const ws1 = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + doctor1_jwt);
ws1.onmessage = (e) => console.log('Doctor 1 (P123):', JSON.parse(e.data));

// Doctor 2 → Patient 456
const ws2 = new WebSocket('ws://localhost:8000/ws/tremor-data/456/?token=' + doctor2_jwt);
ws2.onmessage = (e) => console.log('Doctor 2 (P456):', JSON.parse(e.data));
```

**Step 2**: Publish data for patient 123:
```bash
mosquitto_pub -t "devices/GLV1/data" -m '{...patient 123 data...}'
```

**Step 3**: Publish data for patient 456:
```bash
mosquitto_pub -t "devices/GLV2/data" -m '{...patient 456 data...}'
```

### Expected Results

1. **Doctor 1 receives only patient 123 data**:
   ```
   Doctor 1 (P123): {"type": "tremor_data", "patient_id": 123, ...}
   (No message for patient 456)
   ```

2. **Doctor 2 receives only patient 456 data**:
   ```
   Doctor 2 (P456): {"type": "tremor_data", "patient_id": 456, ...}
   (No message for patient 123)
   ```

3. **Validates FR-007 and SC-007**: Proper patient data isolation

---

## Scenario 4: Unauthorized Access Rejection

**Objective**: Validate that unauthorized users cannot connect to patient streams

### Setup

Use patient 123 from Scenario 1.

### Execute

**Test Case 1**: Invalid JWT token
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=invalid_token');
```

**Test Case 2**: Expired JWT token
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + expired_jwt);
```

**Test Case 3**: Valid JWT but not assigned to patient
```javascript
// Doctor 3 not assigned to patient 123
const ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + doctor3_jwt);
```

### Expected Results

**Test Case 1 & 2** (Invalid/expired token):
1. WebSocket connection rejected with close code **4401**
2. Error message received before close:
   ```json
   {
     "type": "error",
     "error_code": "unauthorized",
     "error_message": "Invalid or expired authentication token",
     "timestamp": "2026-02-15T14:30:00.000Z"
   }
   ```
3. Connection closes immediately

**Test Case 3** (Valid token, no access):
1. WebSocket connection rejected with close code **4403**
2. Error message received before close:
   ```json
   {
     "type": "error",
     "error_code": "forbidden",
     "error_message": "You do not have access to this patient's data",
     "timestamp": "2026-02-15T14:30:00.000Z"
   }
   ```
3. Connection closes immediately

**Validates FR-007**: Access control enforcement

---

## Scenario 5: Device Unpaired Mid-Session

**Objective**: Validate behavior when device is unpaired while WebSocket connections are active

### Setup

Use patient 123 and device GLV123456789 from Scenario 1, with active WebSocket connection.

### Execute

**Step 1**: Establish WebSocket connection and verify data streaming:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + doctor_jwt);
ws.onmessage = (e) => console.log('Received:', JSON.parse(e.data));

// Publish MQTT message → verify message received
```

**Step 2**: Unpair device via REST API:
```bash
curl -X POST http://localhost:8000/api/devices/456/unpair/ \
  -H "Authorization: Bearer $DOCTOR_JWT"
```

**Step 3**: Publish another MQTT message:
```bash
mosquitto_pub -t "devices/GLV123456789/data" -m '{...payload...}'
```

### Expected Results

1. **After unpairing, WebSocket receives status message**:
   ```json
   {
     "type": "status",
     "status": "device_unpaired",
     "message": "Device GLV123456789 was unpaired from patient. Live monitoring stopped.",
     "timestamp": "2026-02-15T14:35:00.000Z"
   }
   ```

2. **MQTT subscriber rejects message**:
   ```
   WARNING: Received MQTT message from unpaired device: GLV123456789
   INFO: Message rejected (device not paired to any patient)
   ```

3. **WebSocket connection remains open but no data broadcast**

4. **Validates edge case**: Device unpaired mid-session

---

## Scenario 6: ML Prediction Unavailable

**Objective**: Validate graceful handling when ML service fails

### Setup

1. Temporarily break ML model loading (e.g., delete model file or introduce error)
2. Restart MQTT subscriber

### Execute

**Step 1**: Establish WebSocket connection
**Step 2**: Publish MQTT message

### Expected Results

1. **MQTT Subscriber logs warning**:
   ```
   WARNING: ML prediction failed: Model not loaded
   INFO: Broadcasting data without prediction
   ```

2. **WebSocket receives message without `prediction` field**:
   ```json
   {
     "type": "tremor_data",
     "patient_id": 123,
     "device_serial": "GLV123456789",
     "timestamp": "2026-02-15T14:30:00.000Z",
     "tremor_intensity": [0.12, 0.15, 0.18],
     "frequency": 4.5,
     "session_duration": 100,
     "received_at": "2026-02-15T14:30:00.250Z"
   }
   ```
   (Note: `prediction` field omitted)

3. **Database record has `ml_prediction = NULL`**

4. **Frontend must handle missing prediction gracefully**

5. **Validates FR-013**: Graceful ML failure handling

---

## Scenario 7: High-Frequency Data Stream

**Objective**: Validate system handles high-frequency device data (50Hz)

### Setup

Use patient 123 and device GLV123456789 from Scenario 1.

### Execute

**Step 1**: Establish WebSocket connection
**Step 2**: Publish 50 MQTT messages in 1 second (simulating 50Hz stream):
```bash
# Bash script to publish 50 messages
for i in {1..50}; do
  mosquitto_pub -t "devices/GLV123456789/data" -m '{...payload with timestamp $i...}'
  sleep 0.02  # 20ms delay = 50Hz
done
```

### Expected Results

1. **All 50 messages processed without loss**:
   ```
   INFO: Processed 50 MQTT messages in 1.05 seconds
   INFO: Average processing time: 21ms/message
   ```

2. **WebSocket receives all 50 messages** (client may throttle display)

3. **Database contains 50 new BiometricSession records** (or fewer if batching enabled)

4. **Validates SC-001**: System handles 50Hz data stream from device

---

## Scenario 8: WebSocket Reconnection

**Objective**: Validate client reconnection after network interruption

### Setup

Use patient 123 from Scenario 1 with active WebSocket connection.

### Execute

**Step 1**: Establish WebSocket connection
**Step 2**: Simulate network interruption (e.g., kill WiFi, close connection manually)
**Step 3**: Client detects disconnect and attempts reconnect:
```javascript
let ws;

function connect() {
  ws = new WebSocket('ws://localhost:8000/ws/tremor-data/123/?token=' + jwt_token);

  ws.onclose = () => {
    console.log('Disconnected, reconnecting in 5 seconds...');
    setTimeout(connect, 5000);
  };
}

connect();
```

### Expected Results

1. **Client detects disconnect via `onclose` event**
2. **Client attempts reconnect after 5 seconds**
3. **Server accepts reconnection (new WebSocket, same JWT)**
4. **Client resumes receiving data**
5. **Validates SC-006**: Automatic reconnection within 5 seconds

---

## Performance Benchmarks

**Latency Goals** (from spec SC-002, SC-004):
- MQTT → Database: <100ms
- MQTT → WebSocket client: <500ms
- ML prediction: <200ms additional

**Concurrency Goals** (from spec SC-001, SC-003):
- 10 concurrent devices at 50Hz
- 50 concurrent WebSocket connections

**Uptime Goal** (from spec SC-005):
- 99% uptime for MQTT subscriber
- Auto-recovery within 2 minutes

---

## Troubleshooting

**Problem**: WebSocket connection fails with code 4401
- **Solution**: Check JWT token validity, regenerate if expired

**Problem**: MQTT messages not received by subscriber
- **Solution**: Verify MQTT broker running, check credentials in .env, check topic subscription

**Problem**: WebSocket receives no data despite MQTT publishing
- **Solution**: Check Redis connection, verify channel layer configured, check channel group names

**Problem**: ML predictions missing from all messages
- **Solution**: Check ML model files in `backend/models/`, check model loading logs, verify model format

**Problem**: High CPU usage during 50Hz streaming
- **Solution**: Enable batching in MQTT subscriber, optimize database writes, profile Python code

---

## Clean Up

After testing, clean up test data:

```bash
# Delete test biometric sessions
curl -X DELETE http://localhost:8000/api/biometric-sessions/789/ \
  -H "Authorization: Bearer $DOCTOR_JWT"

# Unpair device
curl -X POST http://localhost:8000/api/devices/456/unpair/ \
  -H "Authorization: Bearer $DOCTOR_JWT"

# Delete device
curl -X DELETE http://localhost:8000/api/devices/456/ \
  -H "Authorization: Bearer $DOCTOR_JWT"

# Delete patient
curl -X DELETE http://localhost:8000/api/patients/123/ \
  -H "Authorization: Bearer $DOCTOR_JWT"
```

---

## Summary

**Scenarios Covered**:
1. ✅ End-to-end data flow (happy path)
2. ✅ Multiple concurrent viewers
3. ✅ Patient data isolation
4. ✅ Unauthorized access rejection
5. ✅ Device unpaired mid-session
6. ✅ ML prediction unavailable
7. ✅ High-frequency data stream (50Hz)
8. ✅ WebSocket reconnection

**Validated Requirements**:
- FR-001 through FR-015 (all functional requirements)
- SC-001 through SC-007 (success criteria)
- All acceptance scenarios from user stories 1-3

**Next Steps**: Proceed to `/speckit.tasks` to generate task breakdown for implementation.
