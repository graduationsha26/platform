# Tasks: CMG PID Controller Tuning

**Input**: Design documents from `specs/029-pid-tuning/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in this phase)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)
- All file paths are absolute from the repository root

---

## Phase 1: Setup

**Purpose**: Environment configuration and shared validation infrastructure.

- [X] T001 Add 12 PID gain env vars to `backend/.env` and `backend/.env.example`: `PID_KP_PITCH_MAX=0.20`, `PID_KI_PITCH_MAX=0.020`, `PID_KD_PITCH_MAX=0.050`, `PID_KP_ROLL_MAX=0.15`, `PID_KI_ROLL_MAX=0.015`, `PID_KD_ROLL_MAX=0.040`, and 6 matching `PID_K*_*_DEFAULT` vars (pitch defaults: 0.08/0.002/0.012, roll defaults: 0.06/0.001/0.008); group under `# PID gain bounds — Feature 029` comment
- [X] T002 Add `validate_pid_gains(data)` function to `backend/cmg/validators.py`; reads per-axis max bounds from `decouple.config`; raises `ValidationError` with field-level messages if any of the 6 gain values is negative or exceeds its axis-specific max (Kp pitch >0.20, Ki pitch >0.020, Kd pitch >0.050, Kp roll >0.15, Ki roll >0.015, Kd roll >0.040)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All three Django models added and migrated before any user story implements serializers or views. `SuppressionSession` depends on `PIDConfig` (snapshot fields), and `SuppressionMetric` depends on `SuppressionSession`. Models must be written sequentially into the same file.

**⚠️ CRITICAL**: No user story work can begin until T006 (migration) is complete.

- [X] T003 Add `PIDConfig` model to `backend/cmg/models.py` after the Feature 028 block under `# Feature 029: PID Controller Tuning` comment; fields: `device` (OneToOneField → `devices.Device`, CASCADE, `related_name='pid_config'`), `kp_pitch`/`ki_pitch`/`kd_pitch`/`kp_roll`/`ki_roll`/`kd_roll` (FloatField, all default=0.0), `config_version` (PositiveIntegerField, default=1), `updated_at` (auto_now), `updated_by` (FK → `authentication.CustomUser`, SET_NULL, null=True, blank=True); `Meta.db_table='cmg_pid_config'`; override `save()` to call `full_clean()`; override `clean()` to call `from .validators import validate_pid_gains` with a dict of the 6 gain fields
- [X] T004 Add `SuppressionSession` model to `backend/cmg/models.py` after `PIDConfig`; status choices: `active`/`completed`/`interrupted`; fields: `session_uuid` (UUIDField, unique, editable=False, default=uuid4), `device` (FK → `devices.Device`, CASCADE, db_index=False), `patient` (FK → `patients.Patient`, CASCADE, db_index=False), `started_by` (FK → `authentication.CustomUser`, PROTECT), `status` (CharField(12), default=`active`), `started_at` (auto_now_add), `ended_at` (DateTimeField, null=True, blank=True), `kp_pitch_snap`/`ki_pitch_snap`/`kd_pitch_snap`/`kp_roll_snap`/`ki_roll_snap`/`kd_roll_snap` (FloatField); `Meta.db_table='cmg_suppression_sessions'`; indexes: `(device, -started_at)` name `cmg_supp_device_ts_idx`, `(patient, -started_at)` name `cmg_supp_patient_ts_idx`, `(status, -started_at)` name `cmg_supp_status_ts_idx`
- [X] T005 Add `SuppressionMetric` model to `backend/cmg/models.py` after `SuppressionSession`; fields: `session` (FK → `SuppressionSession`, CASCADE, db_index=False), `device` (FK → `devices.Device`, PROTECT, db_index=False), `device_timestamp` (DateTimeField), `raw_amplitude_deg` (FloatField), `residual_amplitude_deg` (FloatField), `created_at` (auto_now_add); `Meta.db_table='cmg_suppression_metrics'`, `ordering=['-device_timestamp']`; indexes: `(session, device_timestamp)` name `cmg_metric_session_ts_idx`, `(device, device_timestamp)` name `cmg_metric_device_ts_idx`, `(created_at,)` name `cmg_metric_created_idx`
- [X] T006 Run `python manage.py makemigrations cmg --name add_pid_models` then `python manage.py migrate cmg`; verify migration `0003_add_pid_models.py` is created and applied without errors; confirm tables `cmg_pid_config`, `cmg_suppression_sessions`, `cmg_suppression_metrics` exist

**Checkpoint**: Foundation ready — all 3 tables exist, user story implementation can now begin.

---

## Phase 3: User Story 1 — PID Gain Configuration (Priority: P1) 🎯 MVP

**Goal**: Doctor can view and update Kp/Ki/Kd for pitch and roll axes. Gains are persisted, validated, and pushed to the device via retained MQTT. Form pre-fills with current or default values.

**Independent Test**: `GET /api/cmg/pid/config/{device_pk}/` returns defaults; `PUT` with valid gains returns 201 and triggers retained MQTT; `PUT` with Kp=0.99 returns 400 with field error.

### Implementation for User Story 1

- [X] T007 [P] [US1] Add `PIDConfigSerializer` to `backend/cmg/serializers.py`; `ModelSerializer` for `PIDConfig`; `fields=['device_id', 'kp_pitch', 'ki_pitch', 'kd_pitch', 'kp_roll', 'ki_roll', 'kd_roll', 'config_version', 'updated_at', 'updated_by_id']`; `read_only_fields=['device_id', 'config_version', 'updated_at', 'updated_by_id']`; `validate()` method calls `from .validators import validate_pid_gains` passing `data`
- [X] T008 [P] [US1] Add `getPIDConfig(deviceId)` and `setPIDConfig(deviceId, data)` to `frontend/src/services/cmgService.js`; `getPIDConfig` → `api.get('/cmg/pid/config/${deviceId}/')`, `setPIDConfig` → `api.put('/cmg/pid/config/${deviceId}/', data)`; both `.then(r => r.data)`; update file header comment to include Feature 029
- [X] T009 [P] [US1] Add `publish_pid_config(self, serial_number, pid_config) -> bool` method to `backend/realtime/mqtt_client.py`; topic `devices/{serial}/pid_config`; QoS 1, `retain=True`; payload JSON includes `kp_pitch`, `ki_pitch`, `kd_pitch`, `kp_roll`, `ki_roll`, `kd_roll`, `config_version`, `updated_at`; uses `_publish_lock`; follows same pattern as existing `publish_servo_config()`
- [X] T010 [US1] Implement `PIDConfigView(APIView)` in `backend/cmg/views.py`; import `PIDConfig` and `PIDConfigSerializer`; add `_PID_DEFAULTS` constant dict with 6 gain fields using `decouple.config` for defaults (fallback to 0.08/0.002/0.012/0.06/0.001/0.008); `GET`: resolve device with `_get_device()` helper; try to return `device.pid_config` via serializer; on `PIDConfig.DoesNotExist` return synthetic defaults dict with `device_id`, 6 gain fields from `_PID_DEFAULTS`, `config_version=0`, `updated_at=None`, `updated_by_id=None`; `PUT`: doctor-only (403 otherwise); validate `PIDConfigSerializer`; `update_or_create` incrementing `config_version`; publish via `mqtt_client_instance.publish_pid_config()`; return 201/200
- [X] T011 [US1] Add `pid/config/<int:device_pk>/` URL with `PIDConfigView` to `backend/cmg/urls.py`; add `PIDConfigView` to imports; name the URL `'cmg-pid-config'`; place after the Feature 028 servo URL block under `# Feature 029: PID Controller Tuning` comment
- [X] T012 [US1] Create `frontend/src/components/CMG/PIDGainPanel.jsx`; doctor-only (return null if `user?.role !== 'doctor'`); `useEffect` on `deviceId` to call `getPIDConfig(deviceId)` and pre-fill 6 input fields; form has 6 `<input type="number" step="0.001">` fields organized as pitch row (Kp/Ki/Kd) and roll row; inline `validate()` checks each value is ≥ 0 and within per-axis max (read from a `BOUNDS` constant in the component matching the env var values); on submit calls `setPIDConfig`; shows field-level DRF errors if API returns 400 object; shows success message on 201/200; Tailwind CSS matching existing CMG panel style

**Checkpoint**: US1 fully functional — doctors can configure and deliver PID gains to device.

---

## Phase 4: User Story 2 — Suppression Mode Activation (Priority: P2)

**Goal**: Doctor can enable/disable automatic tremor suppression. Platform shows active/inactive/interrupted status. Enabling creates a `SuppressionSession` with gain snapshot and publishes retained `pid_mode=enabled`. Disabling completes the session and publishes `pid_mode=disabled`. Device going offline marks session as interrupted.

**Independent Test**: `POST /api/cmg/pid/sessions/` creates active session and retained MQTT; `GET /api/cmg/pid/mode/{pk}/` shows `is_active: true`; `DELETE /api/cmg/pid/sessions/1/` completes it; `GET mode` shows `is_active: false`.

### Implementation for User Story 2

- [X] T013 [P] [US2] Add `SuppressionSessionSerializer` to `backend/cmg/serializers.py`; `ModelSerializer` for `SuppressionSession`; `fields=['id', 'session_uuid', 'device_id', 'patient_id', 'started_by_id', 'status', 'started_at', 'ended_at', 'kp_pitch_snap', 'ki_pitch_snap', 'kd_pitch_snap', 'kp_roll_snap', 'ki_roll_snap', 'kd_roll_snap']`; all fields read-only
- [X] T014 [P] [US2] Add `startSuppression(deviceId)`, `stopSuppression(sessionPk)`, and `getSuppressionMode(deviceId)` to `frontend/src/services/cmgService.js`; `startSuppression` → `api.post('/cmg/pid/sessions/', { device_id: deviceId })`; `stopSuppression` → `api.delete('/cmg/pid/sessions/${sessionPk}/')`; `getSuppressionMode` → `api.get('/cmg/pid/mode/${deviceId}/')`; all `.then(r => r.data)`
- [X] T015 [P] [US2] Add `publish_pid_mode(self, serial_number, mode) -> bool` method to `backend/realtime/mqtt_client.py`; topic `devices/{serial}/pid_mode`; QoS 1, `retain=True`; payload JSON `{ mode: 'enabled'|'disabled', command_id: str(uuid4()), issued_at: timezone.now().isoformat() }`; uses `_publish_lock`; follows same pattern as `publish_servo_config()`
- [X] T016 [US2] Implement `SuppressionSessionView(APIView)` and `SuppressionModeView(APIView)` in `backend/cmg/views.py`; import `SuppressionSession`, `SuppressionSessionSerializer`; `SuppressionSessionView.post()`: doctor-only; resolve device with `_get_device()`; check device has PIDConfig (400 if not); check no existing active session for device (409 if exists); load PIDConfig values for snapshot; create `SuppressionSession` with gain snapshot fields; publish `mqtt_client_instance.publish_pid_mode(serial, 'enabled')`; return 201; `SuppressionSessionView.delete(session_pk)`: doctor-only; get session; mark `status='completed'`, set `ended_at=timezone.now()`; publish `pid_mode='disabled'`; return 200; `SuppressionModeView.get(device_pk)`: doctor/patient; query `SuppressionSession.objects.filter(device=device, status='active').first()`; return `{device_id, is_active, session_id, session_uuid, started_at}`; `SuppressionSessionView.get()`: list sessions by `device_id` query param with `limit` (default 20, max 100); doctor/patient access; return `{count, results}` with `SuppressionSessionSerializer`
- [X] T017 [US2] Add URL patterns to `backend/cmg/urls.py` under Feature 029 comment: `pid/sessions/` → `SuppressionSessionView` (name `'cmg-pid-sessions'`), `pid/sessions/<int:session_pk>/` → `SuppressionSessionView` for DELETE (name `'cmg-pid-session-detail'`), `pid/mode/<int:device_pk>/` → `SuppressionModeView` (name `'cmg-pid-mode'`); add both new views to imports
- [X] T018 [US2] Add `devices/+/pid_status` subscription to `on_connect` in `backend/realtime/mqtt_client.py` (QoS 0); add `elif message_type == 'pid_status': self._handle_pid_status(payload, serial_number)` dispatch branch in `on_message`; implement `_handle_pid_status(self, payload, serial_number)` method: call `validate_device_pairing(serial_number)` to get `(device, patient)`; if `payload.get('mode') == 'fault'` or `'interrupted'`, find active session for device and mark it `status='interrupted'`, set `ended_at=timezone.now()`, publish `pid_mode='disabled'`; broadcast to WebSocket via `async_to_sync(channel_layer.group_send)` with `type='pid_status'` and message payload; add `self._pid_sample_counters: dict = {}` to `__init__` for use by T025
- [X] T019 [US2] Add `async def pid_status(self, event)` handler to `TremorDataConsumer` in `backend/realtime/consumers.py`; method body: `try: message = event['message']; await self.send(text_data=json.dumps(message)); except Exception as e: logger.error(...)`; follows exact pattern of existing `servo_state()` handler
- [X] T020 [US2] Create `frontend/src/components/CMG/SuppressionModeControl.jsx`; doctor-only (return null if not doctor); `useEffect` on `deviceId` to call `getSuppressionMode(deviceId)` and set `{isActive, sessionId}`; merge WebSocket `latestMessage` when `type === 'pid_status'` to update live status; renders status badge (active=green, inactive=gray, interrupted=amber); "Enable Suppression" button calls `startSuppression(deviceId)` and refreshes mode; "Disable Suppression" button calls `stopSuppression(sessionId)` and refreshes mode; separate loading state for each button; error display; also receives `latestMessage` prop like `GimbalStatusDisplay`

**Checkpoint**: US2 fully functional — doctors can enable/disable suppression; sessions logged; device receives MQTT mode command.

---

## Phase 5: User Story 3 — Suppression Effectiveness Monitoring (Priority: P3)

**Goal**: Doctor views per-session aggregate (avg raw amplitude, avg residual amplitude, % reduction with 60% target indicator) and live time-series chart. Device metrics are stored at 1 Hz (downsampled from ~10 Hz). WebSocket pushes live readings during active sessions.

**Independent Test**: With a completed session that has ≥ 60 metric rows, `GET /api/cmg/pid/sessions/?device_id=N` returns `reduction_pct`; `GET /api/cmg/pid/sessions/1/metrics/` returns time-series data with aggregate; WebSocket forwards `suppression_metric` messages.

### Implementation for User Story 3

- [X] T021 [P] [US3] Add `SuppressionMetricSerializer` and `SuppressionSessionSummarySerializer` to `backend/cmg/serializers.py`; `SuppressionMetricSerializer`: `ModelSerializer` for `SuppressionMetric`, `fields=['device_timestamp', 'raw_amplitude_deg', 'residual_amplitude_deg']`; `SuppressionSessionSummarySerializer`: plain `Serializer` extending `SuppressionSessionSerializer` fields plus `avg_raw_amplitude_deg` (FloatField, allow_null=True), `avg_residual_amplitude_deg` (FloatField, allow_null=True), `reduction_pct` (FloatField, allow_null=True)
- [X] T022 [P] [US3] Add `listSessions(deviceId, params = {})` and `getSessionMetrics(sessionPk, params = {})` to `frontend/src/services/cmgService.js`; `listSessions` → `api.get('/cmg/pid/sessions/', { params: { device_id: deviceId, ...params } })`; `getSessionMetrics` → `api.get('/cmg/pid/sessions/${sessionPk}/metrics/', { params })`; both `.then(r => r.data)`
- [X] T023 [US3] Implement `SuppressionMetricView(APIView)` in `backend/cmg/views.py` and extend `SuppressionSessionView.get()` with aggregate computation; import `SuppressionMetric`, `SuppressionMetricSerializer`, `SuppressionSessionSummarySerializer`, `Avg` from `django.db.models`; `SuppressionMetricView.get(session_pk)`: doctor/patient access; resolve session; support `since` ISO param and `limit` (default 300, max 3600); compute aggregate with `session.suppression_metrics.aggregate(avg_raw=Avg('raw_amplitude_deg'), avg_residual=Avg('residual_amplitude_deg'))`; compute `reduction_pct = round((avg_raw - avg_residual) / avg_raw * 100, 1) if avg_raw else None`; return `{session_id, session_status, aggregate: {avg_raw, avg_residual, reduction_pct}, metrics: [...]}` using `SuppressionMetricSerializer(many=True)`; extend `SuppressionSessionView.get()` list to annotate each session with aggregate fields using the same `Avg()` pattern
- [X] T024 [US3] Add `pid/sessions/<int:session_pk>/metrics/` URL to `backend/cmg/urls.py`; import `SuppressionMetricView`; name `'cmg-pid-session-metrics'`
- [X] T025 [US3] Extend `_handle_pid_status()` in `backend/realtime/mqtt_client.py` to store `SuppressionMetric` rows at 1 Hz and broadcast `suppression_metric` WebSocket events; add metric storage block: generate `counter_key = f"{serial_number}:{payload.get('session_id', '')}"`, increment `self._pid_sample_counters[counter_key]`, only call `SuppressionMetric.objects.create(session_id=..., device=device, device_timestamp=..., raw_amplitude_deg=payload['raw_amplitude_deg'], residual_amplitude_deg=payload['residual_amplitude_deg'])` every 10th message; always broadcast `async_to_sync(channel_layer.group_send)(group_name, {'type': 'suppression_metric', 'message': {'type': 'suppression_metric', 'session_id': payload.get('session_id'), 'raw_amplitude_deg': payload['raw_amplitude_deg'], 'residual_amplitude_deg': payload['residual_amplitude_deg'], 'timestamp': payload['timestamp']}})` regardless of sampling; wrap both blocks in try/except to prevent one failure from blocking the other
- [X] T026 [US3] Add `async def suppression_metric(self, event)` handler to `TremorDataConsumer` in `backend/realtime/consumers.py`; identical pattern to `pid_status()` — `await self.send(text_data=json.dumps(event['message']))`; also follows existing `cmg_telemetry` pattern
- [X] T027 [US3] Create `frontend/src/components/CMG/SuppressionEffectivenessChart.jsx`; props: `deviceId`, `latestMessage`; `useState` for `sessions` list and `liveMetrics` array and `activeSessionId`; on mount: call `listSessions(deviceId)` and populate sessions; on `latestMessage` with `type === 'suppression_metric'`: append to `liveMetrics` (cap at last 300 points); display aggregate summary for selected session: avg raw amplitude, avg residual amplitude, `reduction_pct` colored green (≥ 60%) or amber (< 60%); Recharts `LineChart` with two `<Line>` series (raw amplitude = dashed gray, residual amplitude = solid blue) and a horizontal `<ReferenceLine y={targetResidual}` to show 60% target; show "Meets target" / "Below target" indicator badge; use `getSessionMetrics(sessionId)` to load historical data when a past session is selected; `since` param polling not needed — use WebSocket for live data; doctor and patient roles both see this component; add `SuppressionEffectivenessChart` component header comment citing Feature 029

**Checkpoint**: All three user stories functional. Live metrics flow device → MQTT → DB + WebSocket → chart.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 Run `python manage.py check` from `backend/` and confirm output is `System check identified no issues (0 silenced)`
- [X] T029 Validate all 7 API endpoints from `specs/029-pid-tuning/quickstart.md` via Django shell or HTTP client: `GET /api/cmg/pid/config/{device_pk}/` returns defaults; `PUT` with valid gains returns 201; `PUT` with `kp_pitch=0.99` returns 400; `POST /api/cmg/pid/sessions/` without PIDConfig returns 400; `POST` with config returns 201; `GET /api/cmg/pid/mode/{device_pk}/` returns active session; `DELETE /api/cmg/pid/sessions/{pk}/` returns 200 completed; confirm MQTT methods (`publish_pid_config`, `publish_pid_mode`) exist on `MQTTClient` class; confirm `suppression_metric` and `pid_status` handlers exist in `TremorDataConsumer`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational migration (T006) — can start immediately after
- **User Story 2 (Phase 4)**: Depends on US1 completion (US2 session start requires PIDConfig to exist)
- **User Story 3 (Phase 5)**: Depends on US2 completion (`_handle_pid_status` from T018 must exist before T025 extends it)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Requires only Foundational (Phase 2) — fully independent
- **US2 (P2)**: Logically requires US1 (FR-010: must have PIDConfig before enabling suppression); `SuppressionSession` model was created in Foundational so schema is ready
- **US3 (P3)**: Requires US2 (`_handle_pid_status` in T018 is the subscription that T025 extends); `SuppressionMetric` model was created in Foundational

### Within Each User Story

- Backend serializer, frontend service function, and MQTT method can be written in parallel (different files)
- View implementation depends on serializer
- URL routing depends on view
- Frontend component depends on frontend service function

### Parallel Opportunities

- T003, T004, T005 must be sequential (same file)
- T007, T008, T009 can be parallel (serializers.py, cmgService.js, mqtt_client.py)
- T013, T014, T015 can be parallel (serializers.py, cmgService.js, mqtt_client.py)
- T021, T022 can be parallel (serializers.py, cmgService.js)
- T025, T026 can be parallel (mqtt_client.py, consumers.py)

---

## Parallel Execution Examples

### User Story 1 (Phase 3)

```text
Parallel batch 1 (different files):
  Task T007: PIDConfigSerializer in backend/cmg/serializers.py
  Task T008: getPIDConfig/setPIDConfig in frontend/src/services/cmgService.js
  Task T009: publish_pid_config() in backend/realtime/mqtt_client.py

Sequential after batch 1:
  Task T010: PIDConfigView in backend/cmg/views.py  (needs T007)
  Task T011: URL pattern in backend/cmg/urls.py       (needs T010)
  Task T012: PIDGainPanel.jsx                         (needs T008)
```

### User Story 2 (Phase 4)

```text
Parallel batch 1:
  Task T013: SuppressionSessionSerializer in backend/cmg/serializers.py
  Task T014: session service functions in frontend/src/services/cmgService.js
  Task T015: publish_pid_mode() in backend/realtime/mqtt_client.py

Sequential/parallel after batch 1:
  Task T016: views in backend/cmg/views.py            (needs T013)
  Task T017: URL patterns in backend/cmg/urls.py       (needs T016)
  Task T018: pid_status subscription in mqtt_client.py (different file from T016/T017)
  Task T019: consumers.py handler                      (different file, parallel with T016-T018)
  Task T020: SuppressionModeControl.jsx                (needs T014)
```

### User Story 3 (Phase 5)

```text
Parallel batch 1:
  Task T021: SuppressionMetricSerializer in backend/cmg/serializers.py
  Task T022: listSessions/getSessionMetrics in frontend/src/services/cmgService.js

Sequential after batch 1:
  Task T023: views in backend/cmg/views.py             (needs T021)
  Task T024: URL pattern in backend/cmg/urls.py         (needs T023)

Parallel batch 2:
  Task T025: extend _handle_pid_status in mqtt_client.py
  Task T026: suppression_metric handler in consumers.py

  Task T027: SuppressionEffectivenessChart.jsx         (needs T022)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (env vars + validator)
2. Complete Phase 2: Foundational (all 3 models + migration)
3. Complete Phase 3: User Story 1 (gain config end-to-end)
4. **STOP and VALIDATE**: `GET /api/cmg/pid/config/42/` returns defaults; `PUT` saves and triggers retained MQTT; `PIDGainPanel` renders and submits correctly
5. Demo: doctor configures gains and device receives them

### Incremental Delivery

1. Setup + Foundational → database ready
2. User Story 1 → gain config working (MVP)
3. User Story 2 → suppression activate/deactivate working
4. User Story 3 → live chart and effectiveness monitoring
5. Each story adds value independently

---

## Notes

- All 3 models are in Foundational because US2 needs the SuppressionSession model (not just US2 API) and US3 needs SuppressionMetric; adding all models upfront in a single migration avoids multiple migration files
- `mqtt_client_instance` is a deferred import in views.py (existing pattern); all publish calls follow `from realtime.mqtt_client import mqtt_client_instance`
- `_pid_sample_counters` is keyed by `f"{serial_number}:{session_id}"` — keys can be cleaned up when a session ends in `_handle_pid_status`
- The `SuppressionEffectivenessChart` 60% target line: `targetResidual = avg_raw * 0.40` (residual must be ≤40% of raw to achieve ≥60% reduction); draw as dashed ReferenceLine on the amplitude axis
- Session aggregate in the list endpoint uses Django ORM annotation: `SuppressionSession.objects.annotate(avg_raw=Avg('suppression_metrics__raw_amplitude_deg'), avg_residual=Avg('suppression_metrics__residual_amplitude_deg'))`
