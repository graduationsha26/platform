# WebSocket Protocol Contract: Live Tremor Monitor

**Feature**: 034-live-tremor-monitor
**Endpoint**: `ws://localhost:8000/ws/tremor-data/{patient_id}/?token={jwt_access_token}`
**Consumer**: `backend/realtime/consumers.py` — `TremorDataConsumer`
**Channel group**: `patient_{patient_id}_tremor_data`

---

## Connection Lifecycle

### Connecting

The client connects by opening a WebSocket to the endpoint with the JWT token as a query parameter. The server validates the token and checks that the authenticated user (doctor) is assigned to the requested patient.

**Success** → Server sends a `status` message with `"status": "connected"`.

**Failure** → Server sends an `error` message and closes with code:
- `4401` — Invalid or missing JWT token
- `4403` — User does not have access to this patient
- `4500` — Internal server error

### Reconnection (Client-side)

If the connection drops for any reason, the client must automatically reconnect using exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1       | 1s    |
| 2       | 2s    |
| 3       | 4s    |
| 4       | 8s    |
| 5       | 16s   |
| 6+      | 30s   |

Maximum 10 attempts. After 10 failures, show permanent disconnect state.

### Keepalive

Client sends a `ping` every 30 seconds. Server responds with `pong`.

### Disconnecting

Client closes the WebSocket when the user navigates away from the monitor page. This must be done cleanly to free the channel group subscription.

---

## Message Specifications

All messages are UTF-8 encoded JSON text frames.

### Client → Server Messages

#### `ping`
```json
{
  "type": "ping"
}
```
Server responds with:
```json
{
  "type": "pong",
  "timestamp": "2026-02-20T10:00:30Z"
}
```

---

### Server → Client Messages

#### `status` — Connection Established
Sent immediately after successful authentication and group join.

```json
{
  "type": "status",
  "status": "connected",
  "message": "Successfully connected to patient 1 tremor data stream",
  "timestamp": "2026-02-20T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"status"` |
| `status` | string | `"connected"` on successful join |
| `message` | string | Human-readable description |
| `timestamp` | string (ISO 8601) | Server time |

---

#### `error` — Connection Rejected
Sent before closing if authentication or access check fails.

```json
{
  "type": "error",
  "error_code": "forbidden",
  "error_message": "You do not have access to this patient",
  "timestamp": "2026-02-20T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"error"` |
| `error_code` | string | `"unauthorized"` \| `"forbidden"` \| `"internal_error"` |
| `error_message` | string | Human-readable error |
| `timestamp` | string (ISO 8601) | Server time |

---

#### `biometric_reading` — Raw Sensor Data (NEW in Feature 034)
Broadcast after every `BiometricReading` is stored. Rate: ~100 Hz.

```json
{
  "type": "biometric_reading",
  "patient_id": 1,
  "device_serial": "TRM-001",
  "timestamp": "2026-02-20T10:00:00.010Z",
  "aX": 0.123,
  "aY": -0.045,
  "aZ": 9.812,
  "gX": 1.23,
  "gY": -0.56,
  "gZ": 0.12
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"biometric_reading"` |
| `patient_id` | integer | Patient database ID |
| `device_serial` | string | Glove device serial number |
| `timestamp` | string (ISO 8601) | Device-reported reading timestamp |
| `aX` | float | Accelerometer X-axis (m/s²) |
| `aY` | float | Accelerometer Y-axis (m/s²) |
| `aZ` | float | Accelerometer Z-axis (m/s²) |
| `gX` | float | Gyroscope X-axis (°/s) |
| `gY` | float | Gyroscope Y-axis (°/s) |
| `gZ` | float | Gyroscope Z-axis (°/s) |

**Frontend use**: Amplitude chart (compute `√(aX²+aY²+aZ²)`) + raw values panel.

---

#### `tremor_metrics_update` — FFT Analysis Result (ENHANCED in Feature 034)
Broadcast at ~1 Hz after each FFT window (256 samples) is computed.

```json
{
  "type": "tremor_metrics_update",
  "patient_id": 1,
  "window_start": "2026-02-20T10:00:00Z",
  "window_end": "2026-02-20T10:00:02.56Z",
  "tremor_detected": true,
  "dominant_axis": "aX",
  "dominant_freq_hz": 4.69,
  "dominant_amplitude": 0.15,
  "amplitudes": {
    "aX": 0.15, "aY": 0.08, "aZ": 0.03,
    "gX": 2.10, "gY": 0.90, "gZ": 0.40
  },
  "frequencies": {
    "aX": 4.69, "aY": 4.69, "aZ": null,
    "gX": 4.69, "gY": 4.30, "gZ": null
  },
  "dominant_band_freqs": [3.12, 3.52, 3.91, 4.30, 4.69, 5.08, 5.47, 5.86, 6.25, 6.64, 7.03, 7.42, 7.81],
  "dominant_band_amplitudes": [0.01, 0.02, 0.04, 0.08, 0.15, 0.07, 0.04, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `dominant_band_freqs` | float[] | Frequency bin centers (Hz) in 3–8 Hz band (~13 values) |
| `dominant_band_amplitudes` | float[] | FFT amplitude for each bin of the dominant axis |

**Frontend use**: FFT spectrum bar chart (freqs on X-axis, amplitudes on Y-axis).

---

#### `tremor_data` — Session-Level Data with ML Prediction (EXISTING)
Broadcast per `BiometricSession` stored (rate depends on device sending interval; typically 0.1–1 Hz).

```json
{
  "type": "tremor_data",
  "patient_id": 1,
  "device_serial": "TRM-001",
  "timestamp": "2026-02-20T10:00:00Z",
  "tremor_intensity": 0.45,
  "frequency": 4.5,
  "session_duration": 5000,
  "prediction": {
    "severity": "moderate",
    "confidence": 0.87
  },
  "received_at": "2026-02-20T10:00:00.123Z"
}
```

**Frontend use**: Severity indicator — read `prediction.severity` (`"mild"` / `"moderate"` / `"severe"` / `null`).

---

## Frontend WebSocket Service Contract

**File**: `frontend/src/services/tremorWebSocketService.js`

```js
class TremorWebSocketService {
  constructor(patientId, handlers)
  // handlers = { onMessage, onConnected, onDisconnected, onError }

  connect()   // Opens WebSocket connection
  destroy()   // Closes connection and cancels reconnection

  // Internal: automatic reconnection with exponential backoff
  // Internal: 30s ping keepalive
}
```

**Required `handlers`**:

| Handler | Called when | Arguments |
|---------|-------------|-----------|
| `onMessage(msg)` | Any message received | Parsed JSON object |
| `onConnected()` | Connection established | — |
| `onDisconnected(code, reason)` | Connection closed | `(code: number, reason: string)` |
| `onError(error)` | WebSocket error event | `(error: Event)` |

---

## Frontend Hook Contract

**File**: `frontend/src/hooks/useTremorMonitor.js`

```js
function useTremorMonitor(patientId) {
  return {
    connectionStatus,   // 'connecting' | 'connected' | 'disconnected'
    chartData,          // AmplitudePoint[] — last 60 seconds
    spectrumData,       // SpectrumPoint[] — current FFT spectrum
    severity,           // { level, confidence, isStale }
    rawValues,          // { aX, aY, aZ, gX, gY, gZ, isStale }
    hasActiveStream,    // bool — false if no data in last 5s
  };
}
```

**Behavior**:
- Opens WebSocket on mount, closes on unmount
- Rolling buffer maintained in `useRef`, flushed to `chartData` state at 10Hz
- `hasActiveStream` goes `false` if no `biometric_reading` received for 5+ seconds
