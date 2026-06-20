# Research: Live Tremor Monitor Page (Feature 034)

## R-001: Existing WebSocket Infrastructure

**Decision**: Use the existing `TremorDataConsumer` on `ws/tremor-data/<patient_id>/` — no new WebSocket consumer needed.

**Findings**:
- Consumer lives in `backend/realtime/consumers.py`
- Route registered in `backend/realtime/routing.py` as `path('ws/tremor-data/<int:patient_id>/', ...)`
- Full URL: `ws://localhost:8000/ws/tremor-data/{patient_id}/?token=<JWT>`
- Auth: JWT access token passed as query param `?token=`
- Channel group: `patient_{patient_id}_tremor_data`
- Already handles: connect/disconnect, ping/pong keepalive, and forwards all group messages

**Note**: The feature description mentions `ws://localhost:8000/ws/tremor/{patient_id}/` but the actual implementation uses `/ws/tremor-data/{patient_id}/`. The frontend must use the real URL.

**Rationale**: Avoids creating a duplicate consumer. All message routing is already done via Django Channels group broadcast.

---

## R-002: Existing WebSocket Message Types

**Findings from codebase**:

### `status` (connection lifecycle)
Sent on `connect()`. Also sent implicitly on `disconnect` state changes.
```json
{
  "type": "status",
  "status": "connected",
  "message": "Successfully connected to patient 1 tremor data stream",
  "timestamp": "2026-02-20T10:00:00Z"
}
```

### `tremor_data` (~per BiometricSession, 0.1–1 Hz)
Broadcast from `mqtt_client._broadcast_to_websocket()` when a session-level MQTT message arrives on `devices/{serial}/data`. Contains ML severity prediction.
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

### `tremor_metrics_update` (~1 Hz)
Broadcast from `filter_service._run_fft_and_store()` every ~100 samples (at 100Hz sampling rate = ~1Hz). Contains per-axis FFT results from the Butterworth 3–8Hz bandpass filter.
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
  }
}
```

---

## R-003: Backend Gaps — New Broadcasts Needed

**Gap 1: Raw 6-axis readings not broadcast**

The MQTT handler `_handle_reading_message` stores `BiometricReading` (aX, aY, aZ, gX, gY, gZ) and passes it to `tremor_service.process()`, but does **not** broadcast the raw values via WebSocket. A new `biometric_reading` message must be added.

**Decision**: Add a `biometric_reading` broadcast at the end of `_handle_reading_message` in `backend/realtime/mqtt_client.py`, and add the corresponding handler method in `backend/realtime/consumers.py`.

```json
{
  "type": "biometric_reading",
  "patient_id": 1,
  "device_serial": "TRM-001",
  "timestamp": "2026-02-20T10:00:00.010Z",
  "aX": 0.123, "aY": -0.045, "aZ": 9.812,
  "gX": 1.23,  "gY": -0.56,  "gZ": 0.12
}
```

Rate: ~100 Hz (glove firmware ODR = 100 Hz per `filter_service.SAMPLE_RATE = 100`).

**Gap 2: Full FFT band spectrum not broadcast**

The `tremor_metrics_update` contains only peak amplitudes and dominant frequencies per axis, not the full frequency-bin spectrum. For a proper FFT bar chart (frequency on X-axis), the dominant axis's in-band power spectrum is needed.

**Decision**: Add `dominant_band_freqs` (list of ~13 Hz values) and `dominant_band_amplitudes` (list of ~13 amplitude values) to the `tremor_metrics_update` broadcast in `filter_service._run_fft_and_store()`. These arrays are already computed (`band_freqs`, `band_amp` on the dominant axis) — just include them in the message.

```json
{
  "dominant_band_freqs": [3.12, 3.52, 3.91, 4.30, 4.69, 5.08, 5.47, 5.86, 6.25, 6.64, 7.03, 7.42, 7.81],
  "dominant_band_amplitudes": [0.01, 0.02, 0.04, 0.08, 0.15, 0.07, 0.04, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01]
}
```

---

## R-004: Frontend WebSocket Client Pattern

**Decision**: Implement a plain class `TremorWebSocketService` (not a React hook) wrapping the native browser `WebSocket` API, with automatic exponential-backoff reconnection.

**Rationale**:
- Class-based service is easier to reuse across hook lifecycles
- React `useRef` holds the service instance to survive re-renders
- The hook (`useTremorMonitor`) orchestrates state updates from callbacks

**Reconnection strategy**:
- Delays: 1s → 2s → 4s → 8s → 16s → 30s (capped), max 10 attempts
- On page unmount, call `destroy()` to prevent reconnection loops

**JWT authentication**:
```js
const token = getToken(); // from frontend/src/utils/tokenStorage.js
const url = `${WS_BASE_URL}/ws/tremor-data/${patientId}/?token=${token}`;
```
Where `WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'`.

---

## R-005: Rolling 60-Second Amplitude Buffer

**Decision**: Use a `useRef` for the rolling buffer array to avoid re-render on every sample at 100Hz. A `setInterval` at ~10Hz drives state updates (flushes from the ref buffer to React state).

**Rolling window logic**:
```js
// On each biometric_reading message (100Hz):
const point = { t: Date.parse(msg.timestamp), amplitude: mag };
bufferRef.current.push(point);

// In the 10Hz interval:
const cutoff = Date.now() - 60_000;
bufferRef.current = bufferRef.current.filter(p => p.t >= cutoff);
setChartData([...bufferRef.current]);
```

**Amplitude value**: `sqrt(aX² + aY² + aZ²)` — the Euclidean acceleration magnitude in m/s².

**Recharts configuration**:
- `isAnimationActive={false}` on `<Line>` to prevent reflow on each update
- `xAxisId` with `type="number"` and custom `tickFormatter` to show relative time ("-60s" → "0s")
- `dot={false}` on the line for performance with dense data

---

## R-006: Severity Mapping

**Decision**: Severity is driven by `tremor_data.prediction.severity` (ML model output). Three values:
- `"mild"` → green (`bg-green-100 text-green-800 border-green-300`)
- `"moderate"` → amber (`bg-amber-100 text-amber-800 border-amber-300`)
- `"severe"` → red (`bg-red-100 text-red-800 border-red-300`)
- `null` / no data → grey (`bg-neutral-100 text-neutral-600 border-neutral-300`) with label "No Data"

When connection is lost, display last known severity with a "(stale)" suffix in grey text.

---

## R-007: Frontend Route & Navigation

**Decision**: Route = `/doctor/patients/:id/monitor`. Add a "Live Monitor" button/link on `PatientDetailPage` that navigates to this route.

Do **not** add a global Sidebar menu item — this is a patient-scoped page, not a top-level section.

**Rationale**: The monitor is always accessed in the context of a specific patient, so it belongs in the patient detail flow.

---

## R-008: No Active Session State

**Decision**: Show "No active data stream" state if no `biometric_reading` or `tremor_metrics_update` has been received within a 5-second window after connecting (or after the last message).

Implemented as a `lastDataAt` timestamp in the hook; a 5-second timeout checker shows the inactive overlay.

**Alternatives considered**: Polling the REST API to check for recent BiometricReadings — rejected because it adds unnecessary complexity and latency.

---

## R-009: Constitution Compliance Check

All constitutional requirements are satisfied:
- ✅ Monorepo: All code in `backend/` and `frontend/`
- ✅ Tech Stack: Django Channels (existing), React 18, Tailwind CSS, Recharts
- ✅ Database: No migrations needed for this feature
- ✅ Auth: JWT token via query param (existing pattern in TremorDataConsumer)
- ✅ Security: Token from `tokenStorage.js` (not hardcoded); WS URL from env var
- ✅ Real-time: Django Channels WebSocket (already configured)
- ✅ MQTT: No new MQTT subscriptions needed
- ✅ AI/ML: ML prediction already in `tremor_data.prediction` — no changes needed
- ✅ API Standards: WebSocket messages follow existing snake_case convention
- ✅ Dev Scope: Local development only (`daphne` or `uvicorn` dev server)
