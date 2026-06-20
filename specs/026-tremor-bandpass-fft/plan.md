# Implementation Plan: Tremor Signal Filtering & Frequency Analysis

**Branch**: `026-tremor-bandpass-fft` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)

## Summary

Implement a real-time Parkinsonian tremor signal processing pipeline in the Django backend. The pipeline hooks into the existing MQTT reading ingestion flow (`_handle_reading_message`): each 100 Hz `BiometricReading` is passed through a per-patient 4th-order Butterworth band-pass IIR filter (3–8 Hz, SOS form, scipy), buffered in a 256-sample sliding window, and analyzed by FFT every 100 samples (~1 Hz). The FFT extracts dominant tremor frequency (±0.39 Hz resolution) and peak amplitude for all six axes. Results are stored as `TremorMetrics` records in PostgreSQL and broadcast as `tremor_metrics_update` WebSocket messages to the existing `patient_{id}_tremor_data` channel group.

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts (no frontend changes in this feature)
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with `doctor` role for API access
**Testing**: pytest (backend)
**Project Type**: web (monorepo: `backend/` and `frontend/`)
**Real-time**: Django Channels WebSocket — `patient_{patient_id}_tremor_data` group
**Integration**: Hooks into existing `backend/realtime/mqtt_client.py` MQTT pipeline
**Signal Processing**: scipy.signal (Butterworth IIR, SOS form) + numpy FFT — already installed as scikit-learn transitive deps
**Performance Goals**: Filter service adds <1 ms per 100 Hz sample; FFT runs in <5 ms per 256-sample window; total metric-to-broadcast latency <2 s
**Constraints**: Local development only; in-memory filter state (no Redis needed)
**Scale/Scope**: Supports multiple simultaneous patients (per-patient state isolation in dictionaries); ~1 row/s per active patient in TremorMetrics table

---

## Constitution Check

- [X] **Monorepo Architecture**: All new code in `backend/` — `biometrics/` and `realtime/` apps
- [X] **Tech Stack Immutability**: scipy/numpy are transitive deps of scikit-learn (already installed); no new frameworks
- [X] **Database Strategy**: `TremorMetrics` model in Supabase PostgreSQL; no alternative DB used
- [X] **Authentication**: `GET /api/tremor-metrics/` protected by `IsAuthenticated + IsOwnerOrDoctor`
- [X] **Security-First**: No new secrets; all existing `.env` configuration is reused
- [X] **Real-time Requirements**: `tremor_metrics_update` broadcast via Django Channels to existing WebSocket group
- [X] **MQTT Integration**: Filter service called from `_handle_reading_message` in `mqtt_client.py`
- [X] **AI Model Serving**: N/A — this is deterministic DSP, not ML model serving
- [X] **API Standards**: REST + JSON, snake_case, standard HTTP codes, pagination
- [X] **Development Scope**: Local development only; no Docker/CI/CD

**Result**: ✅ PASS — no constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/026-tremor-bandpass-fft/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── tremor-metrics.yaml   ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── biometrics/
│   ├── models.py                    ← MODIFY: add TremorMetrics model
│   ├── serializers.py               ← MODIFY: add TremorMetricsSerializer
│   ├── views.py                     ← MODIFY: add TremorMetricsViewSet
│   ├── tremor_metrics_urls.py       ← NEW: URL routing for /api/tremor-metrics/
│   └── migrations/
│       └── 0004_add_tremormetrics.py ← NEW: database migration
│
├── realtime/
│   ├── filter_service.py            ← NEW: FilterBank + TremorFilterService
│   ├── mqtt_client.py               ← MODIFY: integrate TremorFilterService
│   └── consumers.py                 ← MODIFY: handle tremor_metrics_update message type
│
└── tremoai_backend/
    └── urls.py                      ← MODIFY: add /api/tremor-metrics/ route
```

**No frontend changes**: This feature provides data infrastructure only. Dashboard UI visualization is a separate feature.

---

## Filter Service Architecture

### FilterBank

```text
FilterBank
├── sos: np.ndarray(4, 6)
│     4th-order Butterworth band-pass [3, 8] Hz at fs=100 Hz, SOS form
│     Computed once at import time via butter()
│
└── _states: Dict[patient_id, Dict[axis, zi: np.ndarray(4, 2)]]
      Per-patient, per-axis IIR filter delay-line state
      Lazy-initialized from first sample value (sosfilt_zi * x0)
```

### TremorFilterService

```text
TremorFilterService
├── filter_bank: FilterBank
│
├── _buffers: Dict[patient_id, deque(maxlen=256)]
│     Stores latest 256 filtered {axis: float, timestamp: datetime} dicts
│
├── _sample_counters: Dict[patient_id, int]
│     Counts samples since last FFT trigger
│
└── _warmed_up: Dict[patient_id, bool]
      True after the first full 256-sample window is discarded (warmup)

process(BiometricReading):
  1. Apply FilterBank to all 6 axes → filtered dict
  2. Append to _buffers[patient_id]
  3. Increment _sample_counters[patient_id]
  4. If counter >= 100 AND buffer has >= 256 samples:
       Reset counter
       If not warmed_up: set warmed_up=True; return
       Call _run_fft_and_store(patient_id, reading)

_run_fft_and_store(patient_id, reading):
  1. Get last 256 filtered samples from buffer
  2. Apply Hann window
  3. rfft → magnitudes (normalized: 2.0 * |rfft(windowed)| / (N * mean(hann)))
  4. For each axis: find peak in 3-8 Hz bins → (freq_hz, amplitude)
  5. Apply threshold → freq_hz=None if below threshold
  6. Find dominant_axis (highest amplitude among detected axes, else highest overall)
  7. TremorMetrics.objects.create(...)
  8. Broadcast via channel_layer to patient_{patient_id}_tremor_data
```

### MQTT Integration Point

```python
# In MQTTClient._handle_reading_message(), after BiometricReading.objects.create():
if biometric_reading:
    try:
        self.tremor_service.process(biometric_reading)
    except Exception as e:
        logger.error(f"Tremor filter pipeline error: {e}", exc_info=True)
        # Non-fatal: MQTT processing continues even if filter fails
```

---

## API Design

### REST Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/tremor-metrics/` | JWT (doctor) | List metrics for a patient, ordered by `window_start` desc |
| GET | `/api/tremor-metrics/latest/` | JWT (doctor) | Most recent metric for a patient |

### Query Parameters

`GET /api/tremor-metrics/?patient_id={id}&limit=100&offset=0&tremor_detected=true`

### WebSocket Message (new type)

```json
{
  "type": "tremor_metrics_update",
  "patient_id": 7,
  "window_start": "2026-02-18T10:30:02.560Z",
  "window_end":   "2026-02-18T10:30:05.120Z",
  "tremor_detected": true,
  "dominant_axis": "aX",
  "dominant_freq_hz": 5.27,
  "dominant_amplitude": 0.312,
  "amplitudes": {
    "aX": 0.312, "aY": 0.089, "aZ": 0.041,
    "gX": 3.7,   "gY": 1.2,   "gZ": 0.4
  },
  "frequencies": {
    "aX": 5.27, "aY": null, "aZ": null,
    "gX": 5.08, "gY": null, "gZ": null
  }
}
```

The existing WebSocket consumer in `realtime/consumers.py` must handle this message type by forwarding it to connected clients (same pattern as the existing `tremor_data` handler).

---

## Key Algorithm Constants

| Constant | Value | Rationale |
|---|---|---|
| `SAMPLE_RATE` | 100 Hz | Glove firmware ODR |
| `BANDPASS_LOW` | 3.0 Hz | Clinical lower bound for Parkinsonian tremor |
| `BANDPASS_HIGH` | 8.0 Hz | Clinical upper bound |
| `FILTER_ORDER` | 4 | 80 dB/decade roll-off; meets 20 dB attenuation requirement |
| `FFT_WINDOW_SIZE` | 256 | Power of 2; gives 0.39 Hz frequency resolution |
| `FFT_STEP_SIZE` | 100 | 1 Hz update rate; 61% window overlap |
| `ACCEL_NO_TREMOR_THRESHOLD` | 0.005 m/s² | ~1.5× accel noise floor |
| `GYRO_NO_TREMOR_THRESHOLD` | 0.1 °/s | ~6× gyro noise floor |

---

## Complexity Tracking

> No constitution violations — this section is provided for completeness only.

| Item | Decision | Justification |
|---|---|---|
| scipy.signal | Used for butter() + sosfilt() | Transitive dep of scikit-learn; no new installation needed |
| In-memory filter state | Python dict in MQTT process | Local dev only; no multi-process deployment |
| TremorMetrics in biometrics app | Not a new Django app | Closely related to BiometricReading; keeps app count low |
