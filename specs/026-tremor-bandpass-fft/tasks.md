# Tasks: Tremor Signal Filtering & Frequency Analysis

**Input**: Design documents from `/specs/026-tremor-bandpass-fft/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same phase)
- **[Story]**: Which user story this task belongs to (US1, US2)
- All file paths are relative to repository root

---

## Phase 1: Setup

**Purpose**: Confirm the signal processing library is available before any code is written.

- [X] T001 Verify scipy.signal and numpy are importable by running `cd backend && python -c "from scipy.signal import butter, sosfilt, sosfilt_zi; import numpy; print('scipy OK, numpy OK')"` — if it fails, run `pip install scipy numpy` (should not be required since scikit-learn is already installed)

**Checkpoint**: scipy and numpy confirmed available — implementation can proceed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the TremorMetrics database model and run the migration. Both user stories share this schema.

**⚠️ CRITICAL**: US2 REST API and storage tasks cannot proceed without this phase complete.

- [X] T002 Create TremorMetrics Django model in `backend/biometrics/models.py` — add after the BiometricReading class with the following fields:
  - `patient = ForeignKey('patients.Patient', on_delete=CASCADE, related_name='tremor_metrics')`
  - `window_start = DateTimeField()` — ISO 8601 UTC timestamp of first sample in FFT window
  - `window_end = DateTimeField()` — ISO 8601 UTC timestamp of last sample in FFT window
  - `tremor_detected = BooleanField()` — True if any axis amplitude exceeds the no-tremor threshold
  - `dominant_axis = CharField(max_length=3, choices=[('aX','aX'),('aY','aY'),('aZ','aZ'),('gX','gX'),('gY','gY'),('gZ','gZ')])` — axis with the highest 3-8 Hz amplitude
  - `dominant_freq_hz = FloatField(null=True, blank=True)` — dominant frequency on the dominant axis; null when tremor_detected is False
  - `dominant_amplitude = FloatField()` — peak 3-8 Hz amplitude on the dominant axis
  - Six per-axis amplitude fields (non-nullable FloatField): `amp_aX`, `amp_aY`, `amp_aZ`, `amp_gX`, `amp_gY`, `amp_gZ`
  - Six per-axis frequency fields (nullable FloatField): `freq_aX`, `freq_aY`, `freq_aZ`, `freq_gX`, `freq_gY`, `freq_gZ` (null when that axis is below threshold)
  - `created_at = DateTimeField(auto_now_add=True)`
  - Meta: `db_table = 'tremor_metrics'`, `ordering = ['-window_start']`, two indexes: `(patient, window_start)` and `(window_start,)`
  - `__str__`: return `f"TremorMetrics(patient={self.patient_id}, window_start={self.window_start}, detected={self.tremor_detected})"`

- [X] T003 Generate and apply TremorMetrics database migration by running `cd backend && python manage.py makemigrations biometrics --name add_tremormetrics && python manage.py migrate` — verify the `tremor_metrics` table is created in Supabase PostgreSQL

**Checkpoint**: `tremor_metrics` table confirmed in database — both user stories can now proceed.

---

## Phase 3: User Story 1 — Tremor Signal Isolation via Band-Pass Filtering (Priority: P1) 🎯 MVP

**Goal**: Every incoming 100 Hz BiometricReading is passed through a 4th-order Butterworth band-pass IIR filter (3–8 Hz), suppressing voluntary motion (<3 Hz, ≥20 dB) and noise (>8 Hz, ≥20 dB). Filtered samples accumulate in a per-patient 256-sample circular buffer. The FFT trigger fires every 100 samples but waits for US2 implementation to compute metrics.

**Independent Test**: Run quickstart.md Integration Scenario 4 — inject a synthetic 5 Hz sine wave at 0.5 m/s² into the FilterBank and verify the output amplitude stays near 0.5 m/s²; inject 1 Hz and 15 Hz and verify output is ≤5% of input amplitude.

### Implementation for User Story 1

- [X] T004 [US1] Create `backend/realtime/filter_service.py` and implement the FilterBank class with the following:
  - Module-level imports: `import numpy as np`, `from scipy.signal import butter, sosfilt, sosfilt_zi`, `from collections import deque`, `import logging`, `from asgiref.sync import async_to_sync`, `from channels.layers import get_channel_layer`
  - Module-level constants: `SAMPLE_RATE = 100`, `BANDPASS_LOW = 3.0`, `BANDPASS_HIGH = 8.0`, `FILTER_ORDER = 4`, `FFT_WINDOW_SIZE = 256`, `FFT_STEP_SIZE = 100`, `AXES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`, `ACCEL_NO_TREMOR_THRESHOLD = 0.005`, `GYRO_NO_TREMOR_THRESHOLD = 0.1`
  - `FilterBank` class:
    - `__init__(self)`: compute `self.sos = butter(N=FILTER_ORDER, Wn=[BANDPASS_LOW, BANDPASS_HIGH], btype='bandpass', fs=SAMPLE_RATE, output='sos')` (sos.shape will be (8, 6) after LP→BP transform doubles the order); initialize `self._states: Dict[int, Dict[str, np.ndarray]] = {}`
    - `filter(self, patient_id: int, axis: str, value: float) -> float`: if patient_id not in _states, create empty dict; if axis not in _states[patient_id], initialize `zi = sosfilt_zi(self.sos) * value` (shape (8,2)); then `y, zi = sosfilt(self.sos, np.array([value]), zi=self._states[patient_id][axis])`; update state; return `float(y[0])`
    - `reset(self, patient_id: int)`: remove patient_id from _states if present
  - Module-level logger: `logger = logging.getLogger(__name__)`

- [X] T005 [US1] Add TremorFilterService class to `backend/realtime/filter_service.py` (below FilterBank) with the following:
  - `__init__(self)`: create `self.filter_bank = FilterBank()`, `self.channel_layer = get_channel_layer()`, `self._buffers: Dict[int, deque] = {}`, `self._sample_counters: Dict[int, int] = {}`, `self._warmed_up: Dict[int, bool] = {}`
  - `process(self, reading) -> None`: for each axis in AXES, get `getattr(reading, axis)` and apply `self.filter_bank.filter(patient_id, axis, raw)` to get filtered value; lazy-initialize per-patient buffer (deque(maxlen=FFT_WINDOW_SIZE)), counter (0), and warmed_up (False); append `{'timestamp': reading.timestamp, 'aX': ..., 'aY': ..., 'aZ': ..., 'gX': ..., 'gY': ..., 'gZ': ...}` dict to buffer; increment counter; if `self._sample_counters[patient_id] >= FFT_STEP_SIZE and len(self._buffers[patient_id]) >= FFT_WINDOW_SIZE`: reset counter to 0; if not warmed_up: set warmed_up=True and return (discard first window per FR-011); else call `self._run_fft_and_store(patient_id, reading)`
  - `_run_fft_and_store(self, patient_id: int, reading) -> None`: leave as a `pass` stub for now (implemented in T007)

- [X] T006 [US1] Integrate TremorFilterService into `backend/realtime/mqtt_client.py`:
  - Add import at top: `from realtime.filter_service import TremorFilterService`
  - In `MQTTClient.__init__`: add `self.tremor_service = TremorFilterService()` after `self.ml_service = MLPredictionService()`
  - In `_handle_reading_message`, directly after `logger.info(f"Stored BiometricReading: id=...")` and before the `return biometric_reading` statement, add a try/except block: `if biometric_reading: try: self.tremor_service.process(biometric_reading) except Exception as e: logger.error(f"Tremor filter pipeline error: {e}", exc_info=True)` — the block must be non-fatal (MQTT processing must continue even if the filter fails)

**Checkpoint**: US1 complete — glove data flows through the FilterBank and accumulates in sliding buffers. Filter correctness verifiable via quickstart.md Scenario 4.

---

## Phase 4: User Story 2 — Real-Time Tremor Frequency & Amplitude Extraction via FFT (Priority: P2)

**Goal**: Every 100 filtered samples (~1 Hz), the system runs an FFT on the 256-sample Hann-windowed buffer, extracts dominant tremor frequency and amplitude for all 6 axes, stores a TremorMetrics row, and broadcasts a `tremor_metrics_update` message via WebSocket to the patient's channel group. A REST API exposes historical TremorMetrics to authenticated doctors.

**Independent Test**: Run quickstart.md Integration Scenarios 1–3 (database rate, REST API, WebSocket stream) and Scenario 5 (no-tremor state).

### Implementation for User Story 2

- [X] T007 [US2] Replace the `_run_fft_and_store` stub in `backend/realtime/filter_service.py` with full FFT implementation:
  - `buf = list(self._buffers[patient_id])` — all FFT_WINDOW_SIZE samples
  - `window_start = buf[0]['timestamp']`, `window_end = buf[-1]['timestamp']`
  - `hann = np.hanning(FFT_WINDOW_SIZE)`, `coherent_gain = float(np.mean(hann))`
  - `freqs = np.fft.rfftfreq(FFT_WINDOW_SIZE, d=1.0 / SAMPLE_RATE)`
  - `band_mask = (freqs >= BANDPASS_LOW) & (freqs <= BANDPASS_HIGH)`
  - For each axis in AXES:
    - `signal = np.array([s[axis] for s in buf])`
    - `fft_mag = 2.0 * np.abs(np.fft.rfft(signal * hann)) / (FFT_WINDOW_SIZE * coherent_gain)` (correct amplitude normalization per research.md R-003)
    - `band_amp = fft_mag[band_mask]`, `band_freqs = freqs[band_mask]`
    - `peak_idx = int(np.argmax(band_amp))`, `peak_amplitude = float(band_amp[peak_idx])`, `peak_freq = float(band_freqs[peak_idx])`
    - Apply threshold: `threshold = ACCEL_NO_TREMOR_THRESHOLD if axis.startswith('a') else GYRO_NO_TREMOR_THRESHOLD`; `freq_hz = peak_freq if peak_amplitude >= threshold else None`
    - Store `axis_metrics[axis] = {'amplitude': peak_amplitude, 'frequency': freq_hz}`
  - `tremor_detected = any(m['frequency'] is not None for m in axis_metrics.values())`
  - Determine `dominant_axis`: find axis with max amplitude among detected axes (where frequency is not None); if none detected, find axis with globally max amplitude
  - `dominant_freq_hz = axis_metrics[dominant_axis]['frequency']`, `dominant_amplitude = axis_metrics[dominant_axis]['amplitude']`
  - Import TremorMetrics inside the method (deferred import to avoid circular import): `from biometrics.models import TremorMetrics`
  - `TremorMetrics.objects.create(patient_id=patient_id, window_start=window_start, window_end=window_end, tremor_detected=tremor_detected, dominant_axis=dominant_axis, dominant_freq_hz=dominant_freq_hz, dominant_amplitude=dominant_amplitude, amp_aX=..., amp_aY=..., amp_aZ=..., amp_gX=..., amp_gY=..., amp_gZ=..., freq_aX=..., freq_aY=..., freq_aZ=..., freq_gX=..., freq_gY=..., freq_gZ=...)`
  - Broadcast WebSocket message using `async_to_sync(self.channel_layer.group_send)(f'patient_{patient_id}_tremor_data', {'type': 'tremor_metrics_update', 'message': {'type': 'tremor_metrics_update', 'patient_id': patient_id, 'window_start': window_start.isoformat(), 'window_end': window_end.isoformat(), 'tremor_detected': tremor_detected, 'dominant_axis': dominant_axis, 'dominant_freq_hz': dominant_freq_hz, 'dominant_amplitude': dominant_amplitude, 'amplitudes': {axis: axis_metrics[axis]['amplitude'] for axis in AXES}, 'frequencies': {axis: axis_metrics[axis]['frequency'] for axis in AXES}}})` — wrap in try/except and log errors without raising
  - Wrap the entire method in try/except so a storage or broadcast failure does not crash the MQTT pipeline

- [X] T008 [P] [US2] Add `tremor_metrics_update` handler method to `TremorDataConsumer` class in `backend/realtime/consumers.py`:
  - Add `async def tremor_metrics_update(self, event):` below the existing `async def tremor_data(self, event):` method
  - Body: extract `message = event['message']`; `await self.send(text_data=json.dumps(message))`; log debug; wrap in try/except logging errors
  - Django Channels maps the channel layer message type `tremor_metrics_update` to this method automatically (the type string `tremor_metrics_update` maps to method name `tremor_metrics_update`)
  - Add docstring: "Handle tremor_metrics_update messages from channel layer (broadcast from TremorFilterService at ~1 Hz). Forwards the FFT analysis result to the connected WebSocket client."

- [X] T009 [P] [US2] Add TremorMetricsSerializer to `backend/biometrics/serializers.py`:
  - Update the import at line 8 from `from .models import BiometricSession, BiometricReading` to `from .models import BiometricSession, BiometricReading, TremorMetrics`
  - Append `TremorMetricsSerializer(serializers.ModelSerializer)` at the end of the file with:
    - Docstring: "Read-only serializer for TremorMetrics records. Returns all per-axis amplitude and frequency fields plus summary fields."
    - `Meta.model = TremorMetrics`
    - `Meta.fields = ['id', 'patient', 'window_start', 'window_end', 'tremor_detected', 'dominant_axis', 'dominant_freq_hz', 'dominant_amplitude', 'amp_aX', 'amp_aY', 'amp_aZ', 'amp_gX', 'amp_gY', 'amp_gZ', 'freq_aX', 'freq_aY', 'freq_aZ', 'freq_gX', 'freq_gY', 'freq_gZ', 'created_at']`
    - `Meta.read_only_fields = Meta.fields` — no API creation; records are created by TremorFilterService only

- [X] T010 [US2] Add TremorMetricsViewSet to `backend/biometrics/views.py` (depends on T009):
  - Update the import at the top: add `TremorMetrics` to the model import, add `TremorMetricsSerializer` to the serializer import
  - Add `TremorMetricsViewSet(viewsets.ReadOnlyModelViewSet)` at the end of the file:
    - `permission_classes = [IsAuthenticated, IsOwnerOrDoctor]`
    - `serializer_class = TremorMetricsSerializer`
    - `filter_backends = [DjangoFilterBackend]`
    - `filterset_fields = ['patient', 'tremor_detected']`
    - `get_queryset(self)`: doctors see metrics for accessible patients (same `Q(created_by=user) | Q(doctor_assignments__doctor=user)` pattern as BiometricReadingViewSet); patient role sees own metrics only
    - `list(self, request, ...)`: require `patient_id` query param (return 400 if missing/non-integer); filter queryset to that patient; apply access check; paginate and return
    - `@action(detail=False, methods=['get'], url_path='latest')` named `latest(self, request)`: require `patient_id`; get `.order_by('-window_start').first()`; return 404 with `{'error': 'No tremor metrics found for patient {patient_id}'}` if None; otherwise return serialized single object

- [X] T011 [US2] Create `backend/biometrics/tremor_metrics_urls.py` following the same pattern as `reading_urls.py`:
  ```python
  """URL routing for TremorMetrics endpoints."""
  from django.urls import path, include
  from rest_framework.routers import DefaultRouter
  from .views import TremorMetricsViewSet

  router = DefaultRouter()
  router.register(r'', TremorMetricsViewSet, basename='tremor-metrics')

  urlpatterns = [
      path('', include(router.urls)),
  ]
  ```

- [X] T012 [US2] Register the TremorMetrics URL route in `backend/tremoai_backend/urls.py`:
  - Add `path('api/tremor-metrics/', include('biometrics.tremor_metrics_urls')),` after the existing `path('api/biometric-readings/', include('biometrics.reading_urls')),` line

**Checkpoint**: US2 complete — TremorMetrics rows appear in DB at ~1 Hz while glove streams; WebSocket clients receive `tremor_metrics_update` messages; `GET /api/tremor-metrics/` and `GET /api/tremor-metrics/latest/` respond correctly with JWT auth.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and documentation.

- [X] T013 Validate the end-to-end pipeline by running quickstart.md Integration Scenarios 1–5 in order:
  - Scenario 1: Database row rate (~1 row/s confirmed via shell)
  - Scenario 2: REST API returns paginated results for a doctor JWT
  - Scenario 3: WebSocket receives `tremor_metrics_update` at ~1 Hz
  - Scenario 4: Synthetic 5 Hz signal → reported dominant_freq_hz within ±0.5 Hz, dominant_amplitude within ±10%
  - Scenario 5: Sub-threshold signal → tremor_detected=False, dominant_freq_hz=None

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — T003 (migrate) depends on T002 (model) being written
- **US1 (Phase 3)**: Depends on Phase 1 only (no DB needed for FilterBank/buffering); T005 depends on T004 (same file); T006 depends on T005 (must have TremorFilterService to import)
- **US2 (Phase 4)**: Depends on Phase 2 (TremorMetrics model) AND Phase 3 (TremorFilterService stub exists); T007 depends on T005; T010 depends on T009; T011 depends on T010; T012 depends on T011
- **Polish (Phase 5)**: Depends on all US1 and US2 tasks complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 1. No DB required. Independently testable via synthetic signal injection.
- **US2 (P2)**: Depends on Phase 2 (TremorMetrics table) AND US1 (TremorFilterService with process() stub). Adds FFT computation and DB storage on top of US1's filter+buffer infrastructure.

### Within Each User Story

- US1: T004 → T005 → T006 (strictly sequential — same file, then integration)
- US2: T007, T008 [P], T009 [P] can start together after Phase 3 is done; T010 after T009; T011 after T010; T012 after T011

---

## Parallel Opportunities

### Phase 2

- T002 and T003 are sequential (migration depends on model code)

### Phase 4 (US2)

```
# Once Phase 3 (US1) is complete AND T002 (TremorMetrics model) is done:
# These three tasks can run in parallel:
Task T007: Implement _run_fft_and_store() in backend/realtime/filter_service.py
Task T008: Add tremor_metrics_update handler in backend/realtime/consumers.py
Task T009: Add TremorMetricsSerializer in backend/biometrics/serializers.py

# Then sequentially:
T010 (views.py) → T011 (tremor_metrics_urls.py) → T012 (urls.py)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: US1 — FilterBank + buffering + MQTT integration (T004, T005, T006)
4. **STOP and VALIDATE**: Run quickstart.md Scenario 4 to verify filter correctness
5. US1 delivers the signal isolation prerequisite for all downstream tremor analysis

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Clean filtered signal in buffers → verifiable independently
3. Phase 4 (US2) → TremorMetrics in DB + WebSocket + REST API → full clinical data pipeline
4. Phase 5 → End-to-end validated

---

## Notes

- `filter_service.py` is a NEW file — T004 creates it, T005 adds to it, T007 replaces a stub in it
- `mqtt_client.py`, `consumers.py`, `serializers.py`, `views.py`, `urls.py` are all MODIFICATIONS to existing files
- The `sosfilt_zi` initialization with `* initial_value` (not just `* 1.0`) is critical to suppress the startup transient (FR-011)
- The `sos.shape = (8, 6)` NOT `(4, 6)` — the LP→BP transform doubles the filter order from 4 to 8
- Amplitude normalization: `2.0 * |rfft(signal * hann)| / (FFT_WINDOW_SIZE * mean(hann))` — the `mean(hann)` coherent gain correction is essential; without it, amplitudes are underestimated ~2×
- The `_run_fft_and_store` deferred import of TremorMetrics (`from biometrics.models import TremorMetrics` inside the method body) avoids a circular import between `realtime.filter_service` and `biometrics.models`
- `tremor_metrics_update` in consumers.py is registered automatically by Django Channels: the channel layer message `type` field value maps directly to the consumer method name
