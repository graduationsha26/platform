# Quickstart & Integration Scenarios: Live Tremor Monitor (Feature 034)

## Prerequisites

- Backend running: `python manage.py runserver` (or `daphne` for ASGI/WebSocket)
- Frontend running: `npm run dev`
- MQTT broker running (Mosquitto on `localhost:1883`)
- At least one patient created and a device paired to that patient
- Doctor account created and assigned to that patient

---

## Scenario 1: Happy Path — Doctor Opens Live Monitor

**Goal**: Verify the page connects, receives data, and all four panels display live information.

### Steps

1. Log in as a doctor at `http://localhost:5173/login`
2. Navigate to Patients → select a patient → click "Live Monitor"
3. URL changes to `/doctor/patients/{id}/monitor`

### Expected State: Connecting
- Connection status badge shows **"Connecting..."** (grey/yellow)
- Amplitude chart shows an empty frame
- FFT chart shows empty bars
- Severity indicator shows **"No Data"** (grey)
- Raw values panel shows dashes (`—`)

### Expected State: Connected (within 3 seconds)
- Connection status badge switches to **"Connected"** (green)
- A `status` message was received: `{"type": "status", "status": "connected", ...}`

### Expected State: Data Flowing (after glove starts sending)

Trigger via MQTT simulator or real glove:
```bash
mosquitto_pub -h localhost -t "tremo/sensors/TRM-001" -m '{
  "timestamp": "2026-02-20T10:00:00.010Z",
  "aX": 0.12, "aY": -0.04, "aZ": 9.81,
  "gX": 1.20, "gY": -0.55, "gZ": 0.11,
  "battery_level": 87.0
}'
```

- **Amplitude chart**: Point appears at T=0, chart begins scrolling
- **Raw values panel**: Shows `aX: 0.12 m/s², aY: -0.04 m/s², aZ: 9.81 m/s², gX: 1.20 °/s, ...`

After ~2.56 seconds (256 samples at 100 Hz):
- **FFT chart**: Bars appear showing frequency spectrum of dominant axis
- **Severity indicator**: Remains "No Data" until a session-level message arrives

Trigger a session-level message (with ML prediction):
```bash
mosquitto_pub -h localhost -t "devices/TRM-001/data" -m '{
  "timestamp": "2026-02-20T10:00:05Z",
  "tremor_intensity": 0.45,
  "frequency": 4.5,
  "session_duration": 5000,
  "timestamps": [0, 10, 20, 30, 40]
}'
```

- **Severity indicator**: Changes to **"Moderate"** (amber) if ML model classifies as moderate

### After 60 Seconds
- Old data scrolls off the left edge of the amplitude chart
- Chart always shows the most recent 60 seconds

---

## Scenario 2: Connection Drop and Auto-Reconnect

**Goal**: Verify the page handles network interruption gracefully.

### Steps

1. Open the live monitor (connected and receiving data)
2. Stop the Django dev server: `Ctrl+C`

### Expected State: Disconnected
- Connection status badge switches to **"Disconnected"** (red)
- Amplitude chart freezes on last received data
- Severity indicator shows last known severity with `(stale)` suffix in grey
- Raw values panel shows last known values marked as stale
- No "No active stream" overlay yet (still showing stale data)

3. Restart the Django dev server

### Expected State: Auto-Reconnecting (within 5 seconds)
- Status badge shows **"Connecting..."** while reconnecting
- After successful reconnect: status returns to **"Connected"** (green)
- Stale indicators clear, data resumes

---

## Scenario 3: No Active Data Stream

**Goal**: Verify the "No active data stream" state when connected but no sensor data flows.

### Steps

1. Open the live monitor (connected to backend)
2. Stop the MQTT broker OR ensure no glove is sending data
3. Wait 5 seconds

### Expected State: Connected, No Stream
- Connection status badge: **"Connected"** (green) — backend connection is fine
- An informational overlay appears: **"No active data stream"** with "Check that the patient's device is powered on and connected."
- All charts remain blank/frozen
- Raw values panel shows dashes

4. Restart data flow (publish an MQTT reading)

### Expected State: Data Resumes
- Overlay disappears
- Chart and panels update with fresh data

---

## Scenario 4: Unauthorized Access

**Goal**: Verify that doctors cannot access monitors for patients not assigned to them.

### Steps

1. Log in as Doctor A (assigned to Patient 1)
2. Manually navigate to `/doctor/patients/999/monitor` (a patient assigned to Doctor B)

### Expected State: Access Denied
- WebSocket connection attempt is rejected with close code `4403`
- Page shows an error state: **"You do not have access to this patient's live monitor."**
- "Back to patients" link is visible

---

## Scenario 5: Severity Cycling

**Goal**: Verify all three severity states render correctly.

### Steps (using MQTT simulator)

Publish a session with severity = mild:
```bash
mosquitto_pub -t "devices/TRM-001/data" -m '{"tremor_intensity":0.1,"frequency":4.0,"session_duration":1000,"timestamp":"2026-02-20T10:01:00Z","timestamps":[0]}'
```
→ Severity indicator: **"Mild"** (green)

Publish a session with severity = severe (high intensity):
```bash
mosquitto_pub -t "devices/TRM-001/data" -m '{"tremor_intensity":0.9,"frequency":5.0,"session_duration":1000,"timestamp":"2026-02-20T10:01:05Z","timestamps":[0]}'
```
→ Severity indicator: **"Severe"** (red)

---

## Development Test Setup

### Simulating 100Hz Sensor Data (Bash loop)

```bash
for i in $(seq 1 300); do
  mosquitto_pub -h localhost -t "tremo/sensors/TRM-001" -m "{
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.${i}00Z)\",
    \"aX\": $(python3 -c 'import random; print(round(random.uniform(-0.3, 0.3), 4))'),
    \"aY\": $(python3 -c 'import random; print(round(random.uniform(-0.3, 0.3), 4))'),
    \"aZ\": $(python3 -c 'import random; print(round(9.81 + random.uniform(-0.1, 0.1), 4))'),
    \"gX\": $(python3 -c 'import random; print(round(random.uniform(-5, 5), 4))'),
    \"gY\": $(python3 -c 'import random; print(round(random.uniform(-5, 5), 4))'),
    \"gZ\": $(python3 -c 'import random; print(round(random.uniform(-5, 5), 4))'),
    \"battery_level\": 85.0
  }"
  sleep 0.01
done
```

### Checking WebSocket Message Stream (browser DevTools)

In Chrome DevTools → Network → WS → select the connection → Messages tab.
All `biometric_reading` and `tremor_metrics_update` messages will appear in real time.

### JWT Token for Manual WebSocket Testing

```js
// Run in browser console on the app:
const token = localStorage.getItem('tremo_access_token');
const ws = new WebSocket(`ws://localhost:8000/ws/tremor-data/1/?token=${token}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
