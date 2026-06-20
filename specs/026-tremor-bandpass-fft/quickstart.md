# Quickstart & Integration Scenarios: Tremor Signal Filtering & Frequency Analysis

**Feature**: 026-tremor-bandpass-fft
**Date**: 2026-02-18

---

## Prerequisites

- Feature 025-imu-kalman-fusion firmware running on ESP32 (publishing to MQTT at 100 Hz)
- Django backend running: `python manage.py runserver`
- MQTT client running: `python manage.py run_mqtt_client`
- Mosquitto broker running: `mosquitto -v`
- A Device and Patient registered in Django admin, device paired to patient

---

## Integration Scenario 1: End-to-End Real Glove Streaming

**Goal**: Verify that TremorMetrics records are created in the database while the glove streams at 100 Hz.

### Steps

1. Start the glove (ESP32 powers on, completes calibration, connects to MQTT).

2. Wait ~5 seconds (3 seconds for warmup window + 2 seconds for second window to fully accumulate).

3. Run the following Django shell command:

```bash
python manage.py shell -c "
from biometrics.models import TremorMetrics
import time
c1 = TremorMetrics.objects.count()
print(f'Initial count: {c1}')
time.sleep(10)
c2 = TremorMetrics.objects.count()
print(f'Count after 10s: {c2}')
print(f'Rate: {(c2-c1)/10:.2f} rows/s (expected ~1/s)')
"
```

**Expected output**:
```
Initial count: 3
Count after 10s: 13
Rate: 1.00 rows/s (expected ~1/s)
```

4. Inspect the latest record:

```bash
python manage.py shell -c "
from biometrics.models import TremorMetrics
m = TremorMetrics.objects.order_by('-window_start').first()
print(f'tremor_detected: {m.tremor_detected}')
print(f'dominant_axis: {m.dominant_axis}')
print(f'dominant_freq_hz: {m.dominant_freq_hz}')
print(f'dominant_amplitude: {m.dominant_amplitude:.4f}')
print(f'Amplitudes: aX={m.amp_aX:.4f} aY={m.amp_aY:.4f} aZ={m.amp_aZ:.4f}')
print(f'Amplitudes: gX={m.amp_gX:.4f} gY={m.amp_gY:.4f} gZ={m.amp_gZ:.4f}')
"
```

---

## Integration Scenario 2: REST API — List Tremor Metrics

**Goal**: Verify the `/api/tremor-metrics/` endpoint returns paginated results for a doctor.

### Steps

1. Obtain a JWT token for a doctor user:

```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@example.com", "password": "yourpassword"}' \
  | python -m json.tool
```

Save the `access` token as `$TOKEN`.

2. List tremor metrics for patient ID 1:

```bash
curl -s http://localhost:8000/api/tremor-metrics/?patient_id=1 \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
```

**Expected response** (excerpt):
```json
{
  "count": 47,
  "next": "http://localhost:8000/api/tremor-metrics/?patient_id=1&limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 47,
      "patient": 1,
      "window_start": "2026-02-18T10:30:02.000Z",
      "window_end": "2026-02-18T10:30:04.560Z",
      "tremor_detected": true,
      "dominant_axis": "aX",
      "dominant_freq_hz": 5.27,
      "dominant_amplitude": 0.31,
      ...
    }
  ]
}
```

3. Fetch the latest metric:

```bash
curl -s "http://localhost:8000/api/tremor-metrics/latest/?patient_id=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
```

**Expected**: Single TremorMetrics object (not an array).

---

## Integration Scenario 3: WebSocket — Live tremor_metrics_update Messages

**Goal**: Verify that WebSocket clients receive `tremor_metrics_update` messages at ~1 Hz while the glove streams.

### Steps

Install `websockets` if not already available:

```bash
pip install websockets
```

Run this Python script from the backend directory:

```python
import asyncio, websockets, json

async def monitor():
    uri = "ws://localhost:8000/ws/tremor/"
    async with websockets.connect(uri) as ws:
        print("Connected. Waiting for messages...")
        count = 0
        async for msg in ws:
            data = json.loads(msg)
            if data.get("type") == "tremor_metrics_update":
                count += 1
                print(
                    f"[{count}] freq={data['dominant_freq_hz']} Hz  "
                    f"amp={data['dominant_amplitude']:.3f}  "
                    f"detected={data['tremor_detected']}"
                )
                if count >= 10:
                    break

asyncio.run(monitor())
```

**Expected output** (approximately once per second):
```
Connected. Waiting for messages...
[1] freq=5.27 Hz  amp=0.312  detected=True
[2] freq=5.31 Hz  amp=0.318  detected=True
[3] freq=5.19 Hz  amp=0.301  detected=True
...
```

---

## Integration Scenario 4: Signal Injection Test (No Hardware Required)

**Goal**: Verify filter correctness using synthetic signals without a physical glove.

Run this Django shell command to simulate 300 samples (3 seconds) of a 5 Hz sine wave at 100 Hz and check the resulting TremorMetrics:

```python
python manage.py shell -c "
import numpy as np
from django.utils import timezone
from biometrics.models import BiometricReading
from patients.models import Patient
from realtime.filter_service import TremorFilterService

# Get any patient for testing
patient = Patient.objects.first()
if not patient:
    print('ERROR: No patient found. Add a patient in Django admin first.')
    exit()

# Generate 300 samples of a 5 Hz sine wave at 0.5 m/s2 amplitude
svc = TremorFilterService()
t = np.arange(300) / 100.0  # 0..2.99 seconds at 100 Hz
sine_5hz = 0.5 * np.sin(2 * np.pi * 5.0 * t)

for i, v in enumerate(sine_5hz):
    ts = timezone.now()
    # Inject into filter service directly (bypassing MQTT)
    class FakeReading:
        patient_id = patient.id
        timestamp = ts
        aX = float(v)
        aY = 0.0; aZ = 0.0
        gX = 0.0; gY = 0.0; gZ = 0.0
    svc.process(FakeReading())

from biometrics.models import TremorMetrics
m = TremorMetrics.objects.filter(patient=patient).order_by('-window_start').first()
if m:
    print(f'tremor_detected: {m.tremor_detected}   (expected: True)')
    print(f'dominant_freq_hz: {m.dominant_freq_hz:.2f} Hz  (expected: ~5.0 Hz)')
    print(f'dominant_amplitude: {m.dominant_amplitude:.3f} m/s2  (expected: ~0.5)')
else:
    print('No TremorMetrics created — check sample count (need >256 samples to trigger FFT)')
"
```

**Expected output**:
```
tremor_detected: True   (expected: True)
dominant_freq_hz: 5.08 Hz  (expected: ~5.0 Hz)
dominant_amplitude: 0.487 m/s2  (expected: ~0.5)
```

Note: 5.08 Hz is the nearest FFT bin to 5 Hz with 0.39 Hz resolution (within the ±0.5 Hz tolerance of SC-002).

---

## Integration Scenario 5: "No Tremor" State Verification

**Goal**: Verify the system reports `tremor_detected=False` when signal amplitude is below the threshold.

Similar to Scenario 4, but inject a 0.001 m/s² amplitude signal (below the 0.005 m/s² threshold):

```python
# amplitude = 0.001  (below ACCEL_NO_TREMOR_THRESHOLD = 0.005)
sine_very_low = 0.001 * np.sin(2 * np.pi * 5.0 * t)
```

**Expected output**:
```
tremor_detected: False   (expected: False)
dominant_freq_hz: None
dominant_amplitude: 0.001 m/s2
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No TremorMetrics records created | MQTT client not running | Run `python manage.py run_mqtt_client` |
| Rate << 1 row/s | Filter not yet warmed up | Wait 5 seconds after glove starts streaming |
| `dominant_freq_hz` always null | Signal below threshold | Check `filter_service.ACCEL_NO_TREMOR_THRESHOLD` |
| WebSocket not receiving `tremor_metrics_update` | Consumer missing handler | Verify `consumers.py` handles `tremor_metrics_update` type |
| `ImportError: scipy.signal` | scipy not installed | Run `pip install scipy` |
| `freq_aX` is 4.69 instead of 5.0 | Expected — FFT bin quantization | Resolution is 0.39 Hz; ±0.5 Hz is within spec |
