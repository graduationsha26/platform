# Data Model: Tremor Signal Filtering & Frequency Analysis

**Feature**: 026-tremor-bandpass-fft
**Date**: 2026-02-18

---

## New Entity: TremorMetrics

**Description**: Stores the output of one FFT analysis window for a patient. Created approximately once per second per active patient while the glove is streaming. Represents tremor frequency and amplitude metrics derived from band-pass filtered sensor data.

**Django app**: `biometrics`
**DB table**: `tremor_metrics`

### Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | AutoField (PK) | No | Auto-incrementing primary key |
| `patient` | FK → patients.Patient | No | The patient whose glove produced this reading (CASCADE delete) |
| `window_start` | DateTimeField | No | Timestamp of the first sample in the FFT analysis window |
| `window_end` | DateTimeField | No | Timestamp of the last sample in the FFT analysis window |
| `tremor_detected` | BooleanField | No | True if any axis shows amplitude above the no-tremor threshold |
| `dominant_axis` | CharField(3) | No | Which axis has the highest 3-8 Hz amplitude (one of: aX, aY, aZ, gX, gY, gZ) |
| `dominant_freq_hz` | FloatField | Yes | Dominant frequency (Hz) on the dominant axis; null if no tremor |
| `dominant_amplitude` | FloatField | No | Peak amplitude on the dominant axis (m/s² for accel, °/s for gyro) |
| `amp_aX` | FloatField | No | Peak 3-8 Hz amplitude on accelerometer X-axis (m/s²) |
| `amp_aY` | FloatField | No | Peak 3-8 Hz amplitude on accelerometer Y-axis (m/s²) |
| `amp_aZ` | FloatField | No | Peak 3-8 Hz amplitude on accelerometer Z-axis (m/s²) |
| `amp_gX` | FloatField | No | Peak 3-8 Hz amplitude on gyroscope X-axis (°/s) |
| `amp_gY` | FloatField | No | Peak 3-8 Hz amplitude on gyroscope Y-axis (°/s) |
| `amp_gZ` | FloatField | No | Peak 3-8 Hz amplitude on gyroscope Z-axis (°/s) |
| `freq_aX` | FloatField | Yes | Dominant frequency on aX (Hz); null if below threshold |
| `freq_aY` | FloatField | Yes | Dominant frequency on aY (Hz); null if below threshold |
| `freq_aZ` | FloatField | Yes | Dominant frequency on aZ (Hz); null if below threshold |
| `freq_gX` | FloatField | Yes | Dominant frequency on gX (Hz); null if below threshold |
| `freq_gY` | FloatField | Yes | Dominant frequency on gY (Hz); null if below threshold |
| `freq_gZ` | FloatField | Yes | Dominant frequency on gZ (Hz); null if below threshold |
| `created_at` | DateTimeField | No | Auto-set to now() at insert time |

### Indexes

- `(patient, window_start)` — primary access pattern for dashboard queries (latest metrics for a patient)
- `(window_start)` — secondary access for time-range queries

### Constraints

- `window_end > window_start` — enforced at service layer
- `dominant_axis` — restricted to `['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']` via choices
- `dominant_freq_hz` IS NULL when `tremor_detected` is False

### Relationships

```
patients.Patient ──(1:N)──► TremorMetrics
biometrics.BiometricReading ──(source, no FK)──► TremorMetrics
```

TremorMetrics is derived from BiometricReading data but does not have a direct FK to individual readings (it represents a window aggregation over 256 readings). The temporal relationship is captured by `window_start`/`window_end` timestamps which overlap with BiometricReading timestamps for the same patient.

---

## In-Memory State (not persisted)

These are runtime data structures maintained in the `TremorFilterService` singleton within the MQTT client process:

### FilterBank State

| Structure | Key | Value | Description |
|---|---|---|---|
| `_states` | `patient_id: int` | `Dict[axis: str, zi: np.ndarray(4, 2)]` | Per-patient, per-axis IIR filter state (scipy sosfilt zi format) |

### TremorFilterService State

| Structure | Key | Value | Description |
|---|---|---|---|
| `_buffers` | `patient_id: int` | `deque(maxlen=256)` of `{axis: float, timestamp: datetime}` | Circular buffer of last 256 filtered samples |
| `_sample_counters` | `patient_id: int` | `int` | Samples received since last FFT run |
| `_warmed_up` | `patient_id: int` | `bool` | Whether the first warmup window has been discarded |

---

## Existing Entities (unchanged)

### BiometricReading (existing, modified)

No schema changes. The `_handle_reading_message` method in `mqtt_client.py` is modified to call `TremorFilterService.process(reading)` after creating the BiometricReading — but the model itself is not changed.

### BiometricSession (existing, unchanged)

No changes.

---

## Migration

One new migration required:

- **0004_add_tremormetrics**: Creates the `tremor_metrics` table with all fields and indexes listed above.

Migration goes in: `backend/biometrics/migrations/0004_add_tremormetrics.py`

> Note: Migration numbering must be verified against the actual latest migration in the biometrics app at implementation time.
