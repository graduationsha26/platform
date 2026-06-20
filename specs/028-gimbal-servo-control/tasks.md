# Tasks: CMG Gimbal Servo Control

**Input**: Design documents from `/specs/028-gimbal-servo-control/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Not requested — no test tasks included per project convention.

**Organization**: Tasks are grouped by user story. US1 (Gimbal Position Control) is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependencies within the phase)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment configuration needed before any model or code can be written.

- [X] T001 Add `GIMBAL_RATE_LIMIT_MIN_DEG_PER_SEC=5.0` and `GIMBAL_RATE_LIMIT_MAX_DEG_PER_SEC=180.0` to `backend/.env` and `backend/.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The three new database models, validation helpers, and migration that ALL user stories depend on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: The migration (T004) depends on the models (T002). T002 and T003 can run in parallel.

- [X] T002 [P] Add `GimbalCalibration`, `ServoCommand`, and `GimbalState` model classes to `backend/cmg/models.py` — `GimbalCalibration`: OneToOneField(Device, CASCADE, related_name='gimbal_calibration'), fields pitch_center_deg/roll_center_deg (default=0.0), pitch_min_deg (default=-30.0), pitch_max_deg (default=30.0), roll_min_deg (default=-20.0), roll_max_deg (default=20.0), rate_limit_deg_per_sec (default=45.0), updated_at (auto_now), updated_by (nullable FK to CustomUser SET_NULL); clean() validates min<max both axes and rate_limit within .env bounds; save() calls full_clean(). `ServoCommand`: FK(Device, CASCADE), FK(Patient, CASCADE), FK(CustomUser, PROTECT, issued_by), command_id (UUIDField unique default=uuid4), target_pitch_deg/target_roll_deg (nullable FloatField), is_home_command (BooleanField default=False), rate_limit_snap/pitch_min_snap/pitch_max_snap/roll_min_snap/roll_max_snap (FloatField), status (CharField choices: pending/published/failed); indexes on (device,-issued_at) and (patient,-issued_at). `GimbalState`: OneToOneField(Device, CASCADE, related_name='gimbal_state'), pitch_deg/roll_deg (FloatField), pitch_status/roll_status (CharField choices: idle/moving/fault), device_timestamp (DateTimeField), received_at (DateTimeField auto_now)
- [X] T00\ [P] Create `backend/cmg/validators.py` with two helper functions: `validate_angle_in_range(value, min_deg, max_deg, axis_name)` raises `ValidationError` if `value < min_deg` or `value > max_deg`; `validate_calibration_bounds(data)` raises field-keyed `ValidationError` dict if `pitch_min_deg >= pitch_max_deg` or `roll_min_deg >= roll_max_deg` or `rate_limit_deg_per_sec` outside GIMBAL_RATE_LIMIT_{MIN,MAX}_DEG_PER_SEC read from `decouple.config`
- [X] T00\ Generate migration for the three new models by running `python manage.py makemigrations cmg` from `backend/` — verify the output file is `backend/cmg/migrations/0002_add_gimbal_models.py` creating tables `cmg_gimbal_calibration`, `cmg_servo_commands`, `cmg_gimbal_state`; then run `python manage.py migrate` to apply it

**Checkpoint**: Foundation ready — migration applied, models importable, validators testable.

---

## Phase 3: User Story 1 — Gimbal Position Control (Priority: P1) 🎯 MVP

**Goal**: Doctor can issue pitch/roll position commands and home commands via the dashboard; platform validates against calibration, publishes via MQTT, and logs the `ServoCommand` audit record.

**Independent Test**: `POST /api/cmg/servo/commands/` with `{"device_id": 5, "command": "set_position", "pitch_deg": 20.0, "roll_deg": -5.0}` returns HTTP 200 and the payload appears on `devices/{serial}/servo_command`; `POST` with `pitch_deg: 100.0` returns HTTP 400 out-of-range error; `POST /api/cmg/servo/commands/` with `{"command": "home"}` publishes home payload. `GimbalControlPanel` renders pitch/roll inputs and Home button for doctor role; returns null for patient role.

- [X] T00\ [P] [US1] Add `ServoCommandSerializer` to `backend/cmg/serializers.py` — `ModelSerializer` for `ServoCommand` with fields: `id`, `command_id`, `device_id`, `patient_id`, `issued_by_id`, `issued_at`, `target_pitch_deg`, `target_roll_deg`, `is_home_command`, `rate_limit_snap`, `pitch_min_snap`, `pitch_max_snap`, `roll_min_snap`, `roll_max_snap`, `status`; all fields read-only (record created exclusively by the view)
- [X] T00\ [P] [US1] Add `publish_servo_command(serial_number: str, command_data: dict) -> bool` method to `MQTTClient` in `backend/realtime/mqtt_client.py` — publishes to topic `devices/{serial_number}/servo_command` at QoS 1, retain=False; payload includes `command`, `command_id` (UUID str), `issued_at` (ISO UTC), `rate_limit_deg_per_sec`, `pitch_min_deg`, `pitch_max_deg`, `roll_min_deg`, `roll_max_deg`; for `set_position` also includes `pitch_deg` (if not None) and `roll_deg` (if not None); for `home` command no angle fields; uses `self._publish_lock` thread-safety pattern identical to `publish_cmg_command`; returns False if not connected
- [X] T00\ [P] [US1] Add `sendServoCommand(deviceId, command, angles = {})` function to `frontend/src/services/cmgService.js` — calls `api.post('/cmg/servo/commands/', { device_id: deviceId, command, ...angles })` and returns `response.data`; export alongside existing CMG service functions
- [X] T00\ [US1] Implement `ServoCommandView(APIView)` in `backend/cmg/views.py` — `POST` handler: (1) reject non-doctor with 403 `{"error": "Only doctors can send servo commands."}`; (2) validate `device_id` and `command` present; (3) get `Device` or 400; (4) check `device.patient` not null or 400 `{"error": "Device is not paired."}`; (5) check `Patient.objects.filter(doctor=request.user, id=device.patient_id).exists()` or 403; (6) load `GimbalCalibration` via `getattr(device, 'gimbal_calibration', None)` and fall back to synthesised defaults (centers=0, min=-30/max=30 pitch, min=-20/max=20 roll, rate=45); (7) for `set_position`: call `validate_angle_in_range` for each provided angle against calibration; (8) for `set_position` with neither angle provided return 400; (9) create `ServoCommand` with `status='pending'` and calibration snapshots; (10) call `mqtt_client.publish_servo_command(serial, payload_dict)`; (11) set `cmd.status='published'` or `'failed'`; `cmd.save(update_fields=['status'])`; (12) return 200 with `{"success": True, "command_id": ..., "device_id": ..., "command": ..., "target_pitch_deg": ..., "target_roll_deg": ..., "message": "Command published to device"}` or 503 if MQTT not connected
- [X] T00\ [US1] Add `path('servo/commands/', ServoCommandView.as_view(), name='cmg-servo-commands')` to `urlpatterns` in `backend/cmg/urls.py`; import `ServoCommandView` at top of file
- [X] T0\ [US1] Create `frontend/src/components/CMG/GimbalControlPanel.jsx` — doctor-only component (returns null if `user?.role !== 'doctor'`); two controlled `<input type="number">` fields for `pitchDeg` and `rollDeg`; each input displays `step="0.5"`; "Set Position" button calls `sendServoCommand(deviceId, 'set_position', { pitch_deg: parseFloat(pitchDeg), roll_deg: parseFloat(rollDeg) })` with per-button loading state; "Home" button calls `sendServoCommand(deviceId, 'home')` with its own loading state; `lastError` state shows error message on failure using `err?.response?.data?.error ?? 'Command failed.'`; styled with Tailwind CSS matching CMGControlPanel pattern

**Checkpoint**: US1 fully functional — position commands reach MQTT broker, out-of-range angles rejected, audit records created, `GimbalControlPanel` renders for doctors.

---

## Phase 4: User Story 2 — Servo Calibration (Priority: P2)

**Goal**: Doctor can read and update the center positions and travel range for both servo axes; calibration persists across device power cycles and is pushed to the device as a retained MQTT `servo_config` message.

**Independent Test**: `PUT /api/cmg/servo/calibration/{device_pk}/` with valid JSON returns 201/200 and a subsequent `GET` returns the same values; retained message appears on `devices/{serial}/servo_config`; `PUT` with `pitch_min_deg >= pitch_max_deg` returns 400 with field-keyed error; `GET` before any calibration set returns defaults. `GimbalCalibrationPanel` pre-fills form and shows success after save.

- [X] T0\ [P] [US2] Add `GimbalCalibrationSerializer` to `backend/cmg/serializers.py` — `ModelSerializer` for `GimbalCalibration` with fields: `device_id` (read-only), `pitch_center_deg`, `roll_center_deg`, `pitch_min_deg`, `pitch_max_deg`, `roll_min_deg`, `roll_max_deg`, `rate_limit_deg_per_sec`, `updated_at` (read-only), `updated_by_id` (read-only); `validate()` method calls `validate_calibration_bounds(attrs)` from `backend/cmg/validators.py` to enforce min<max and rate_limit bounds
- [X] T0\ [P] [US2] Add `publish_servo_config(serial_number: str, calibration) -> bool` method to `MQTTClient` in `backend/realtime/mqtt_client.py` — publishes to `devices/{serial_number}/servo_config` at QoS 1, retain=**True**; payload: `pitch_offset_deg` (= `calibration.pitch_center_deg`), `roll_offset_deg` (= `calibration.roll_center_deg`), `pitch_min_deg`, `pitch_max_deg`, `roll_min_deg`, `roll_max_deg`, `rate_limit_deg_per_sec`, `config_version` (= `str(calibration.id)`), `updated_at` (ISO UTC now); uses `self._publish_lock`; returns False if not connected
- [X] T0\ [P] [US2] Add `getGimbalCalibration(deviceId)` and `setGimbalCalibration(deviceId, data)` functions to `frontend/src/services/cmgService.js` — `getGimbalCalibration` calls `api.get(\`/cmg/servo/calibration/\${deviceId}/\`)` and returns `response.data`; `setGimbalCalibration` calls `api.put(\`/cmg/servo/calibration/\${deviceId}/\`, data)` and returns `response.data`
- [X] T0\ [US2] Implement `GimbalCalibrationView(APIView)` in `backend/cmg/views.py` — `GET` handler: get `Device` by `device_pk` (404 if not found); check role access (doctor sees own patients, patient sees own device); try `device.gimbal_calibration`, on `DoesNotExist` return synthesised default dict with `{"device_id": device.id, "pitch_center_deg": 0.0, "roll_center_deg": 0.0, "pitch_min_deg": -30.0, "pitch_max_deg": 30.0, "roll_min_deg": -20.0, "roll_max_deg": 20.0, "rate_limit_deg_per_sec": 45.0, "updated_at": null, "updated_by_id": null}`; `PUT` handler: doctor-only (403 otherwise); validate device access; deserialise with `GimbalCalibrationSerializer(data=request.data)`, `.is_valid(raise_exception=True)`; call `GimbalCalibration.objects.update_or_create(device=device, defaults={**serializer.validated_data, "updated_by": request.user})`; after save, call `mqtt_client.publish_servo_config(device.serial_number, cal_obj)` (non-fatal if broker offline); return 201 if created, 200 if updated, with `GimbalCalibrationSerializer(cal_obj).data`
- [X] T0\ [US2] Add `path('servo/calibration/<int:device_pk>/', GimbalCalibrationView.as_view(), name='cmg-servo-calibration')` to `urlpatterns` in `backend/cmg/urls.py`; import `GimbalCalibrationView` at top of file
- [X] T0\ [US2] Create `frontend/src/components/CMG/GimbalCalibrationPanel.jsx` — doctor-only component (returns null if `user?.role !== 'doctor'`); `useEffect` on mount fetches `getGimbalCalibration(deviceId)` and pre-fills all 7 controlled input fields (pitch_center_deg, roll_center_deg, pitch_min_deg, pitch_max_deg, roll_min_deg, roll_max_deg, rate_limit_deg_per_sec); client-side validation before submit: `pitch_min_deg < pitch_max_deg` and `roll_min_deg < roll_max_deg` with inline error messages; submit calls `setGimbalCalibration(deviceId, formData)` with `loading` state; shows success message `"Calibration saved"` on 200/201; shows API error string on failure; styled with Tailwind CSS (two-column grid for axis pairs)

**Checkpoint**: US2 fully functional — calibration persists in DB, pushed to device via retained MQTT, defaults shown before calibration, validation rejects invalid ranges.

---

## Phase 5: User Story 3 — Real-time Gimbal Monitoring (Priority: P3)

**Goal**: Doctor sees live pitch/roll angles and per-axis status (idle/moving/fault) updating in real time from the WebSocket stream; latest state is also queryable via REST; platform stores most-recent state per device from MQTT.

**Independent Test**: Publish a `servo_state` MQTT message to `devices/{serial}/servo_state`; `GET /api/cmg/servo/state/{device_pk}/` returns matching values; connect a WebSocket client to `ws://localhost:8000/ws/tremor/` and observe `{"type": "servo_state", ...}` message within 1 second of the MQTT publish. `GimbalStatusDisplay` shows live pitch/roll values updating from `latestMessage` prop.

- [X] T0\ [P] [US3] Add `GimbalStateSerializer` to `backend/cmg/serializers.py` — `ModelSerializer` for `GimbalState` with fields: `device_id`, `pitch_deg`, `roll_deg`, `pitch_status`, `roll_status`, `device_timestamp`, `received_at`; all fields read-only
- [X] T0\ [P] [US3] Add `servo_state` MQTT subscription and handler to `backend/realtime/mqtt_client.py`: in `on_connect` add `client.subscribe("devices/+/servo_state", qos=0)` after existing CMG subscriptions; in `on_message` dispatch add `elif message_type == 'servo_state': self._handle_servo_state(payload, serial_number)`; implement `_handle_servo_state(self, payload, serial_number)`: (1) call `validate_device_pairing(serial_number)` → (device, patient), return early if None; (2) parse `payload['timestamp']` to datetime; (3) call `GimbalState.objects.update_or_create(device=device, defaults={'pitch_deg': payload['pitch_deg'], 'roll_deg': payload['roll_deg'], 'pitch_status': payload['pitch_status'], 'roll_status': payload['roll_status'], 'device_timestamp': timestamp})`; (4) call `async_to_sync(channel_layer.group_send)(f'patient_{patient.id}_tremor_data', {'type': 'servo_state', 'message': {'type': 'servo_state', 'device_serial': serial_number, 'patient_id': patient.id, 'pitch_deg': ..., 'roll_deg': ..., 'pitch_status': ..., 'roll_status': ..., 'device_timestamp': payload['timestamp']}})` — both steps non-fatal (wrapped in try/except with logger.error)
- [X] T0\ [P] [US3] Add `getGimbalState(deviceId)` function to `frontend/src/services/cmgService.js` — calls `api.get(\`/cmg/servo/state/\${deviceId}/\`)` and returns `response.data`
- [X] T0\ [US3] Implement `GimbalStateView(APIView)` in `backend/cmg/views.py` — `GET` only; get `Device` by `device_pk` (404 if not found); check role access (same pattern as `MotorTelemetryViewSet`: doctor sees own patients, patient sees own device); try `device.gimbal_state` and return `GimbalStateSerializer(device.gimbal_state).data`; on `RelatedObjectDoesNotExist` return 404 `{"error": "No gimbal state available for this device yet."}`
- [X] T0\ [US3] Add `async def servo_state(self, event)` handler to `TremorDataConsumer` in `backend/realtime/consumers.py` — body: `try: message = event['message']; await self.send(text_data=json.dumps(message)); logger.debug(...) except Exception as e: logger.error(f"Error forwarding servo_state: {e}", exc_info=True)` — pattern identical to existing `cmg_telemetry` and `cmg_fault` handlers
- [X] T0\ [US3] Add `path('servo/state/<int:device_pk>/', GimbalStateView.as_view(), name='cmg-servo-state')` to `urlpatterns` in `backend/cmg/urls.py`; import `GimbalStateView` at top of file
- [X] T0\ [US3] Create `frontend/src/components/CMG/GimbalStatusDisplay.jsx` — no role guard (visible to all roles); `useState` for `state` (initial null); `useEffect` on mount calls `getGimbalState(deviceId)`, sets `state` on success, leaves null on 404; second `useEffect` on `latestMessage` prop: when `latestMessage?.type === 'servo_state'` update `state` with the new values; render: if state is null show `<p>No gimbal data available</p>`; otherwise show pitch angle (large numeric display), roll angle, two status badges (pitch_status, roll_status) with colours: `idle`→gray, `moving`→blue, `fault`→red; display `received_at` as last-updated timestamp; styled with Tailwind CSS

**Checkpoint**: US3 fully functional — MQTT servo_state messages update DB, broadcast via WebSocket, REST endpoint returns latest state, `GimbalStatusDisplay` shows live values.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: System-level validation confirming all components integrate correctly.

- [X] T0\ Run `python manage.py check` from `backend/` and confirm 0 issues; if issues exist resolve them before continuing
- [X] T0\ Validate all 3 REST endpoints and both WebSocket handlers are wired correctly by running a Django shell check: `from django.urls import reverse; reverse('cmg-servo-commands'); reverse('cmg-servo-calibration', args=[1]); reverse('cmg-servo-state', args=[1])` — confirm no `NoReverseMatch`; `from realtime.consumers import TremorDataConsumer; assert hasattr(TremorDataConsumer, 'servo_state')` — confirm WS handler exists; `from realtime.mqtt_client import MQTTClient; assert hasattr(MQTTClient, 'publish_servo_command') and hasattr(MQTTClient, 'publish_servo_config') and hasattr(MQTTClient, '_handle_servo_state')` — confirm MQTT methods exist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (env vars must exist for validators to read); **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 completion (models + migration + validators)
- **US2 (Phase 4)**: Depends on Phase 2 completion; independent of US1
- **US3 (Phase 5)**: Depends on Phase 2 completion; independent of US1 and US2
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on US2 or US3
- **US2 (P2)**: Can start after Phase 2 — independent of US1
- **US3 (P3)**: Can start after Phase 2 — independent of US1 and US2

### Within Each User Story (sequencing)

1. [P] tasks first — serializer + MQTT method + frontend service (different files)
2. View implementation (after serializer and MQTT method)
3. URL routing (after view)
4. Frontend component (after frontend service)

### Parallel Opportunities

- **Phase 2**: T002 and T003 can run in parallel (different files); T004 must wait for T002
- **Phase 3**: T005, T006, T007 can all run in parallel; T008 follows; T009 follows T008; T010 follows T007
- **Phase 4**: T011, T012, T013 can all run in parallel; T014 follows T011+T012; T015 follows T014; T016 follows T013
- **Phase 5**: T017, T018, T019 can all run in parallel; T020 follows T017; T021 follows T018; T022 follows T020; T023 follows T019

---

## Parallel Example: User Story 1

```
# All three can launch together:
Task T005: Add ServoCommandSerializer to backend/cmg/serializers.py
Task T006: Add publish_servo_command() to backend/realtime/mqtt_client.py
Task T007: Add sendServoCommand() to frontend/src/services/cmgService.js

# Then sequentially:
Task T008: Implement ServoCommandView (uses T005 + T006)
Task T009: Add servo/commands/ URL (uses T008)
Task T010: Create GimbalControlPanel.jsx (uses T007)
```

## Parallel Example: User Story 2

```
# All three can launch together:
Task T011: Add GimbalCalibrationSerializer to backend/cmg/serializers.py
Task T012: Add publish_servo_config() to backend/realtime/mqtt_client.py
Task T013: Add getGimbalCalibration() + setGimbalCalibration() to cmgService.js

# Then sequentially:
Task T014: Implement GimbalCalibrationView (uses T011 + T012)
Task T015: Add servo/calibration/ URL (uses T014)
Task T016: Create GimbalCalibrationPanel.jsx (uses T013)
```

---

## Implementation Strategy

### MVP First (US1 Only — Gimbal Position Control)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T004) — **critical blocker**
3. Complete Phase 3: US1 (T005–T010)
4. **STOP and VALIDATE**: Test position commands via quickstart.md Scenario 1
5. Demo gimbal control to stakeholders

### Incremental Delivery

1. Setup + Foundational → models and migration ready
2. US1 → doctors can issue position commands via dashboard (MVP)
3. US2 → doctors can calibrate each glove's travel range
4. US3 → doctors see live position updates in real time
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With two developers:

1. Both complete Phase 1 + Phase 2 together
2. Once Foundational is done:
   - Dev A: US1 (position commands)
   - Dev B: US2 (calibration) — works in parallel
3. Both tackle US3 together or sequentially

---

## Notes

- No test tasks — tests not requested in this feature's spec
- `[P]` tasks touch different files and have no unresolved intra-phase dependencies
- Story labels ([US1], [US2], [US3]) map to spec.md user stories 1–3
- The CMG app (`backend/cmg/`) and CMG components dir (`frontend/src/components/CMG/`) already exist from Feature 027 — no directory creation needed
- `GimbalState` is a latest-state-only model (not time-series) — `update_or_create` on every MQTT message
- Rate limiting is enforced by device firmware; platform passes `rate_limit_deg_per_sec` in every command payload
- `servo_config` MQTT topic uses `retain=True` — device receives calibration immediately on reconnect
- All writes to `GimbalCalibration` from the view call `full_clean()` via the overridden `save()`
