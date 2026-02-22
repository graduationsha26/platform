# Tasks: CMG Brushless Motor & ESC Initialization

**Input**: Design documents from `/specs/027-cmg-esc-init/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: No test tasks — not requested in spec.

**Organization**: Tasks grouped by user story. Each phase is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `cmg` Django app skeleton before any model or logic is written.

- [X] T001 Create `backend/cmg/` directory with `__init__.py` and `apps.py` (AppConfig name `'cmg'`, label `'cmg'`)
- [X] T002 Register `'cmg'` in `INSTALLED_APPS` in `backend/tremoai_backend/settings.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and MQTT client upgrade that ALL user stories depend on. Must complete before any story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `MotorTelemetry` and `MotorFaultEvent` models in `backend/cmg/models.py` — see data-model.md for full field list, choices, and index definitions; include `__str__` methods and Meta classes with `db_table`, `ordering`, and `indexes`
- [X] T004 Run `python manage.py makemigrations cmg --name add_motor_models` and `python manage.py migrate` to apply CMG models to the database
- [X] T005 Upgrade `MQTTClient` in `backend/realtime/mqtt_client.py`: change `mqtt.Client()` to `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)`, update `on_connect`/`on_disconnect` signatures to VERSION2 (`reason_code` instead of `rc`), add `self.is_connected = False` (set True in `on_connect`, False in `on_disconnect`), add `self._publish_lock = threading.Lock()` to `__init__`

**Checkpoint**: `python manage.py check` passes, migration applied, `MotorTelemetry` and `MotorFaultEvent` tables exist in DB.

---

## Phase 3: User Story 1 - Safe CMG Rotor Startup (Priority: P1) 🎯 MVP

**Goal**: Platform backend receives CMG motor telemetry via MQTT, stores each reading as a `MotorTelemetry` row, and exposes telemetry history + latest state via REST API. Doctors can query startup progress (idle → starting → running status transitions).

**Independent Test**: Publish a `devices/GLOVE00001/cmg_telemetry` MQTT message → verify `MotorTelemetry` row created in DB → call `GET /api/cmg/telemetry/latest/?device_id=1` → receive correct JSON (Quickstart Scenarios 1 + 3).

- [X] T006 [US1] Add `devices/+/cmg_telemetry` subscription in `on_connect` in `backend/realtime/mqtt_client.py` (follow existing `devices/+/data` subscription pattern)
- [X] T007 [US1] Add `'cmg_telemetry'` dispatch branch to `on_message` in `backend/realtime/mqtt_client.py` and implement `_handle_cmg_telemetry(self, payload, serial_number)` private method: validate device pairing via `validate_device_pairing`, parse `timestamp`/`rpm`/`current_a`/`status`/`fault_type` from payload, create `MotorTelemetry` row, broadcast `cmg_telemetry` message to channel group `patient_{patient_id}_tremor_data` via `async_to_sync(channel_layer.group_send)` (non-fatal, wrapped in try/except)
- [X] T008 [P] [US1] Create `backend/cmg/serializers.py` with `MotorTelemetrySerializer` (ModelSerializer on `MotorTelemetry`; read-only fields: `id`, `device_id`, `patient_id`, `timestamp`, `rpm`, `current_a`, `status`, `fault_type`)
- [X] T009 [US1] Create `backend/cmg/views.py` with `MotorTelemetryViewSet(viewsets.ReadOnlyModelViewSet)`: `permission_classes = [IsAuthenticated, IsOwnerOrDoctor]`; `get_queryset()` filters by doctor access (same pattern as `BiometricReadingViewSet`); `list()` requires at least one of `device_id` or `patient_id` query param, returns 400 otherwise, supports `limit` (default 60, max 300) and `since` params; `@action(detail=False, methods=['get'], url_path='latest')` returns single most recent row for `device_id`, 404 if none
- [X] T010 [US1] Create `backend/cmg/urls.py` with `DefaultRouter` registering `MotorTelemetryViewSet` at `r'telemetry'` (basename `'cmg-telemetry'`)
- [X] T011 [US1] Add `path('api/cmg/', include('cmg.urls'))` to `backend/tremoai_backend/urls.py`

**Checkpoint**: `GET /api/cmg/telemetry/latest/?device_id=1` returns 200 with correct telemetry after MQTT publish (Quickstart Scenario 3).

---

## Phase 4: User Story 2 - Real-Time CMG Status Telemetry (Priority: P2)

**Goal**: Live motor state (RPM, current, status) streams to connected doctor browsers via WebSocket at ~1 Hz. Frontend `CMGStatusPanel` component displays real-time RPM and status badge.

**Independent Test**: Connect to `ws/tremor-data/{patient_id}/`, publish a `cmg_telemetry` MQTT message, verify a `{"type": "cmg_telemetry", ...}` WebSocket message arrives within 2 seconds (Quickstart Scenario 6). Separately: CMGStatusPanel renders with mock data.

- [X] T012 [P] [US2] Add `async def cmg_telemetry(self, event)` handler method to `TremorDataConsumer` in `backend/realtime/consumers.py` — extract `event['message']`, send via `self.send(text_data=json.dumps(message))`, include try/except with error logging (identical pattern to existing `tremor_metrics_update` method)
- [X] T013 [P] [US2] Create `frontend/src/components/CMG/CMGStatusPanel.jsx` — receives `cmg_telemetry` WebSocket messages from parent's WebSocket hook; displays: RPM value (large number), current draw in amperes, status badge (`idle`/`starting`/`running`/`fault` with color coding — grey/yellow/green/red); calls `cmgService.getLatestTelemetry(deviceId)` on mount for initial state; uses Tailwind CSS for layout
- [X] T014 [P] [US2] Create `frontend/src/services/cmgService.js` with `getLatestTelemetry(deviceId)` calling `GET /api/cmg/telemetry/latest/?device_id={deviceId}` and `getTelemetryHistory(deviceId, limit)` calling `GET /api/cmg/telemetry/?device_id={deviceId}&limit={limit}`; use existing axios/fetch pattern from other service files in `frontend/src/services/`

**Checkpoint**: WebSocket receives `cmg_telemetry` messages after MQTT publish; CMGStatusPanel updates live (Quickstart Scenario 6).

---

## Phase 5: User Story 3 - Automatic Safety Fault Response (Priority: P3)

**Goal**: Platform receives fault events via MQTT, stores them as `MotorFaultEvent` records, pushes immediate WebSocket fault alerts to doctors, provides REST API for fault listing and acknowledgment, and allows doctors to send motor commands (start/stop/emergency_stop) back to the glove via MQTT.

**Independent Test**: Publish a `cmg_fault` MQTT message → verify `MotorFaultEvent` row with `acknowledged=False` created → `GET /api/cmg/faults/?device_id=1&acknowledged=false` returns the fault → `POST /api/cmg/faults/1/acknowledge/` marks it acknowledged → WebSocket receives `cmg_fault` message → `POST /api/cmg/commands/` with `{"device_id":1,"command":"start"}` returns 200 (Quickstart Scenarios 2, 4, 5, 7).

- [X] T015 [US3] Add `devices/+/cmg_fault` subscription to `on_connect` and add `'cmg_fault'` dispatch branch to `on_message` + implement `_handle_cmg_fault(self, payload, serial_number)` in `backend/realtime/mqtt_client.py`: validate device pairing, parse `timestamp`/`fault_type`/`rpm_at_fault`/`current_at_fault`, create `MotorFaultEvent` row, broadcast `cmg_fault` message (including DB `id` of created record) to channel group via `async_to_sync` (non-fatal try/except)
- [X] T016 [US3] Implement `publish_cmg_command(self, serial_number: str, command: str) -> bool` on `MQTTClient` in `backend/realtime/mqtt_client.py`: check `self.is_connected` first (return False + log if not); build payload `{"command": command, "command_id": str(uuid.uuid4()), "issued_at": timezone.now().isoformat()}`; use `with self._publish_lock: result = self.client.publish(f"devices/{serial_number}/cmg_command", json.dumps(payload), qos=1)`; check `result.rc != mqtt.MQTT_ERR_SUCCESS` and return False on failure; return True on success
- [X] T017 [P] [US3] Add `MotorFaultEventSerializer` to `backend/cmg/serializers.py` — ModelSerializer on `MotorFaultEvent`; read-only fields: `id`, `device_id`, `patient_id`, `occurred_at`, `fault_type`, `rpm_at_fault`, `current_at_fault`, `acknowledged`, `acknowledged_at`, `acknowledged_by`
- [X] T018 [P] [US3] Add `async def cmg_fault(self, event)` handler method to `TremorDataConsumer` in `backend/realtime/consumers.py` — identical pattern to `cmg_telemetry` handler added in T012
- [X] T019 [US3] Add `MotorFaultViewSet(viewsets.ReadOnlyModelViewSet)` to `backend/cmg/views.py`: `permission_classes = [IsAuthenticated, IsOwnerOrDoctor]`; `get_queryset()` filters by doctor access; `list()` requires at least one of `device_id` or `patient_id`, supports `acknowledged` boolean filter; `@action(detail=True, methods=['post'], url_path='acknowledge')` sets `fault.acknowledged=True`, `fault.acknowledged_at=timezone.now()`, `fault.acknowledged_by=request.user`, saves and returns updated serializer (idempotent — no-op if already acknowledged)
- [X] T020 [US3] Add `CMGCommandView(APIView)` to `backend/cmg/views.py`: `permission_classes = [IsAuthenticated]`; POST validates `device_id` and `command` (must be one of `start`/`stop`/`emergency_stop`); resolves `Device` and checks doctor has access to `device.patient`; calls `mqtt_client_instance.publish_cmg_command(device.serial_number, command)`; returns 200 `{"status":"published","command":command,"device_serial":serial,"published_at":...}` or 503 `{"error":"MQTT broker not connected. Command not sent."}` if publish returns False
- [X] T021 [US3] Update `backend/cmg/urls.py` to register `MotorFaultViewSet` at `r'faults'` (basename `'cmg-faults'`) and add `path('commands/', CMGCommandView.as_view(), name='cmg-commands')`
- [X] T022 [P] [US3] Create `frontend/src/components/CMG/CMGFaultAlert.jsx` — receives list of unacknowledged faults as props (loaded via `cmgService.getFaults(deviceId, {acknowledged: false})`); renders a dismissible alert card per fault showing `fault_type`, `occurred_at`, `rpm_at_fault`, `current_at_fault`; each card has an "Acknowledge" button that calls `cmgService.acknowledgeFault(faultId)` and removes the card on success; uses Tailwind CSS (red color scheme for fault severity)
- [X] T023 [P] [US3] Create `frontend/src/components/CMG/CMGControlPanel.jsx` — rendered only when `user.role === 'doctor'`; shows three buttons: "Start", "Stop", "Emergency Stop"; each button calls `cmgService.sendCommand(deviceId, command)` on click; "Emergency Stop" is styled in red and requires no confirmation; "Start" is disabled when `status === 'running'` and "Stop"/"E-Stop" are disabled when `status === 'idle'`; handles loading state per button
- [X] T024 [US3] Add `getFaults(deviceId, filters)`, `acknowledgeFault(faultId)`, and `sendCommand(deviceId, command)` to `frontend/src/services/cmgService.js` — `getFaults` calls `GET /api/cmg/faults/?device_id={id}&acknowledged={filters.acknowledged}`; `acknowledgeFault` calls `POST /api/cmg/faults/{id}/acknowledge/`; `sendCommand` calls `POST /api/cmg/commands/` with `{device_id, command}` body

**Checkpoint**: Full fault lifecycle works — MQTT fault → DB → WebSocket push → REST list → acknowledge (Quickstart Scenarios 2, 4, 5, 7, 8, 9). Motor commands publish to MQTT (Scenario 5).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Maintenance tooling and final validation.

- [X] T025 Create `backend/cmg/management/__init__.py`, `backend/cmg/management/commands/__init__.py`, and `backend/cmg/management/commands/purge_cmg_telemetry.py` management command — accepts `--days` (default 30) and `--batch-size` (default 10000) args; batch-deletes `MotorTelemetry` rows older than cutoff using the pattern from research.md Decision 2 to avoid lock contention; prints running total; no-op if no rows to delete
- [X] T026 Run `python manage.py check` and verify 0 system check issues
- [X] T027 Run Quickstart Scenarios 1-5 from `quickstart.md` via Django shell and curl to confirm end-to-end pipeline

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001–T002) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T003–T005)
- **US2 (Phase 4)**: Depends on US1 completion (T011 must be done so the Django app is registered and serving)
- **US3 (Phase 5)**: Depends on Foundational (T003–T005); builds on US1 files (modifies `cmg/views.py`, `cmg/urls.py`, `cmg/serializers.py`, `mqtt_client.py`)
- **Polish (Phase 6)**: Depends on all stories complete

### User Story Dependencies

- **US1 (P1)**: Can start immediately after Foundational. No dependency on US2 or US3.
- **US2 (P2)**: Can start after Foundational. Depends on US1 being complete (shares `cmg/urls.py` and the Django app registration from T011 for frontend to call REST on first mount).
- **US3 (P3)**: Can start after Foundational. Modifies same files as US1 (`mqtt_client.py`, `cmg/views.py`, `cmg/serializers.py`, `cmg/urls.py`) — must follow US1 task completion for those files.

### Within Each User Story

- Models before serializers (T003 → T008, T017)
- Serializers before viewsets (T008 → T009; T017 → T019)
- Viewsets before URLs (T009 → T010; T019+T020 → T021)
- MQTT handler before channel broadcast works (T007 → T012 for live data to arrive)
- Backend ready before frontend integration (T011 before T013/T014 REST calls work)

### Parallel Opportunities

- **Phase 3**: T008 [P] can run in parallel with T006→T007 (different files)
- **Phase 4**: T012 [P], T013 [P], T014 [P] — all touch different files; run all three in parallel
- **Phase 5**: T017 [P] + T018 [P] can run in parallel with T015→T016 (different files); T022 [P] + T023 [P] run in parallel with each other and with the backend tasks (T019–T021)

---

## Parallel Execution Examples

### Phase 3 (US1) Parallel Window

After T006+T007 complete:
```
T008 [P] — backend/cmg/serializers.py  (write MotorTelemetrySerializer)
```
Then sequentially: T009 (views.py) → T010 (urls.py) → T011 (main urls.py)

### Phase 4 (US2) Full Parallel

```
T012 [P] — backend/realtime/consumers.py  (add cmg_telemetry handler)
T013 [P] — frontend/src/components/CMG/CMGStatusPanel.jsx
T014 [P] — frontend/src/services/cmgService.js
```

### Phase 5 (US3) Parallel Windows

Window 1 — after T015+T016 (mqtt_client.py) complete:
```
T017 [P] — backend/cmg/serializers.py    (add MotorFaultEventSerializer)
T018 [P] — backend/realtime/consumers.py (add cmg_fault handler)
```

Window 2 — after T019+T020+T021 complete (backend fully wired):
```
T022 [P] — frontend/src/components/CMG/CMGFaultAlert.jsx
T023 [P] — frontend/src/components/CMG/CMGControlPanel.jsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005) ← CRITICAL GATE
3. Complete Phase 3: US1 (T006–T011)
4. **STOP and VALIDATE**: Quickstart Scenarios 1 + 3 (MQTT → DB → REST)
5. Demo: `GET /api/cmg/telemetry/latest/` shows motor startup progress

### Incremental Delivery

1. Setup + Foundational → DB models exist, MQTT client upgraded
2. US1 complete → MQTT telemetry ingested, REST API live
3. US2 complete → Live WebSocket dashboard with real-time RPM gauge
4. US3 complete → Fault alerts, acknowledgment workflow, motor start/stop buttons
5. Polish → Purge command, final validation

### Parallel Strategy

Once Foundational is complete:
- **Developer A**: US1 backend (T006–T011) then US3 backend (T015–T021)
- **Developer B**: US2 WebSocket (T012) then US3 WebSocket+frontend (T018, T022–T024)
- **Developer C**: Frontend US2 (T013–T014) then Frontend US3 (T022–T024)

---

## Notes

- [P] tasks operate on different files with no shared incomplete dependencies
- `mqtt_client.py` is modified by T005, T006, T007, T015, T016 — always sequential; do not parallelize any of these
- `cmg/views.py` is created by T009 and extended by T019, T020 — always sequential
- `cmg/urls.py` is created by T010 and extended by T021 — sequential
- `cmg/serializers.py` is created by T008 and extended by T017 — sequential
- `consumers.py` is extended by T012 and T018 — these touch different methods; they CAN be parallel [P] but only if working in separate branches/editors to avoid merge conflicts
- paho-mqtt `CallbackAPIVersion.VERSION2` upgrade (T005) must complete before any MQTT publish code (T016) is written — VERSION2 changes `on_connect` callback signature
- The `publish_cmg_command` method (T016) requires `self.is_connected` and `self._publish_lock` to exist (added in T005)
- Never call `self.client.publish()` from inside any MQTT callback method (`on_message`, `on_connect`, `on_disconnect`) — deadlock via `_callback_mutex`
