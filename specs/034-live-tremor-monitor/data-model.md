# Data Model: Live Tremor Monitor Page (Feature 034)

## Overview

This feature is **frontend-dominant** with **minor backend additions**. No new database models or migrations are required. All data is sourced from:

1. **Existing database models** (read-only by this feature): `BiometricReading`, `TremorMetrics`, `BiometricSession`
2. **WebSocket message stream** (real-time): `biometric_reading`, `tremor_metrics_update`, `tremor_data`

---

## Frontend Data Entities (In-Memory Only)

These are transient data structures maintained in the hook — not persisted.

### AmplitudePoint

Represents one point on the rolling amplitude line chart.

| Field | Type | Description |
|-------|------|-------------|
| `t` | number (Unix ms) | Timestamp of the sensor reading |
| `amplitude` | number (m/s²) | Euclidean acceleration magnitude: √(aX² + aY² + aZ²) |

**Rolling window**: last 60 seconds by `t` value. Buffer capped at `60 × 100 = 6000` points max.

### SpectrumPoint

Represents one frequency bin in the FFT spectrum bar chart.

| Field | Type | Description |
|-------|------|-------------|
| `freq` | number (Hz) | Center frequency of this bin (e.g., 3.12, 3.52...) |
| `amplitude` | number | Band-pass filtered amplitude at this frequency |

**Source**: `tremor_metrics_update.dominant_band_freqs` and `dominant_band_amplitudes` arrays (~13 points in the 3–8 Hz band).

### ConnectionState

| Field | Type | Values |
|-------|------|--------|
| `status` | string | `'connecting'` \| `'connected'` \| `'disconnected'` |
| `lastConnectedAt` | Date \| null | When the last successful connection was established |
| `error` | string \| null | Human-readable error for the disconnected state |

### SeverityState

| Field | Type | Description |
|-------|------|-------------|
| `level` | string \| null | `'mild'` \| `'moderate'` \| `'severe'` \| `null` |
| `confidence` | number \| null | ML confidence score (0–1) |
| `receivedAt` | Date \| null | When the last severity update was received |
| `isStale` | boolean | True if connection is lost; severity shown but marked stale |

### RawAxisValues

| Field | Type | Description |
|-------|------|-------------|
| `aX` | number | Accelerometer X-axis (m/s²) |
| `aY` | number | Accelerometer Y-axis (m/s²) |
| `aZ` | number | Accelerometer Z-axis (m/s²) |
| `gX` | number | Gyroscope X-axis (°/s) |
| `gY` | number | Gyroscope Y-axis (°/s) |
| `gZ` | number | Gyroscope Z-axis (°/s) |
| `timestamp` | string | ISO timestamp of the reading |
| `isStale` | boolean | True when connection is lost |

---

## WebSocket Message Contracts

### Incoming: `biometric_reading` (NEW — added in this feature)

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

**Frontend usage**: Push `AmplitudePoint` to rolling buffer; update `RawAxisValues`.

### Incoming: `tremor_metrics_update` (ENHANCED — adds band spectrum)

Broadcast at ~1 Hz after each FFT window is computed.

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

**Frontend usage**: Update `SpectrumPoint[]` array for FFT chart.

### Incoming: `tremor_data` (EXISTING — no changes)

Broadcast per BiometricSession record. Contains ML prediction.

```json
{
  "type": "tremor_data",
  "patient_id": 1,
  "device_serial": "TRM-001",
  "timestamp": "2026-02-20T10:00:00Z",
  "tremor_intensity": 0.45,
  "frequency": 4.5,
  "session_duration": 5000,
  "prediction": {"severity": "moderate", "confidence": 0.87},
  "received_at": "2026-02-20T10:00:00.123Z"
}
```

**Frontend usage**: Update `SeverityState` from `prediction.severity`.

### Incoming: `status` (EXISTING — no changes)

Sent on connection established.

```json
{
  "type": "status",
  "status": "connected",
  "message": "Successfully connected to patient 1 tremor data stream",
  "timestamp": "2026-02-20T10:00:00Z"
}
```

**Frontend usage**: Set `ConnectionState.status = 'connected'`.

### Outgoing: `ping` (EXISTING — no changes)

Sent every 30 seconds by the frontend to keep the connection alive.

```json
{"type": "ping"}
```

---

## Backend Changes (Minimal)

### `backend/realtime/mqtt_client.py`

**Method modified**: `_handle_reading_message`

After `biometric_reading = BiometricReading.objects.create(...)` and before the tremor service call, add:
```python
# Broadcast raw reading to WebSocket clients
self._broadcast_reading_to_websocket(biometric_reading, device, patient)
```

**New helper method**: `_broadcast_reading_to_websocket(reading, device, patient)` — sends `biometric_reading` message to `patient_{patient_id}_tremor_data` channel group.

### `backend/realtime/consumers.py`

**New handler method**: `biometric_reading(self, event)` — mirrors existing handlers like `tremor_data()`, forwards `event['message']` to the WebSocket client.

### `backend/realtime/filter_service.py`

**Method modified**: `_run_fft_and_store` — add `dominant_band_freqs` and `dominant_band_amplitudes` to the broadcast message. Both arrays are already computed in the method (`band_freqs` and `band_amp` for the dominant axis) — just serialize and include them.

---

## No New Database Models

No migrations are needed. Existing models used:
- `BiometricReading` — source of raw axis data
- `BiometricSession` — source of ML prediction severity
- `TremorMetrics` — source of FFT analysis (stored by filter_service, also broadcast)
