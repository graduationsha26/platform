# Tasks: Live Tremor Monitor Page

**Input**: Design documents from `/specs/034-live-tremor-monitor/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/websocket-protocol.md ✅ quickstart.md ✅

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup

**Purpose**: Environment configuration for the new WebSocket env variable

- [X] T001 Add `VITE_WS_BASE_URL=ws://localhost:8000` to `frontend/.env.example` (used by `tremorWebSocketService.js` to build the WebSocket URL)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Three parallel backend additions and one frontend service class — all must complete before any US1 work can receive live `biometric_reading` messages

**⚠️ CRITICAL**: US1 amplitude chart depends on `biometric_reading` WebSocket messages that do not yet exist; T002 + T003 together enable them. T004 is the shared frontend WS client used by all user stories.

- [X] T002 [P] Add `async def biometric_reading(self, event)` handler to `TremorDataConsumer` in `backend/realtime/consumers.py` — identical in structure to the existing `tremor_data()` handler: extract `event['message']` and call `await self.send(text_data=json.dumps(message))`
- [X] T003 [P] Add `_broadcast_reading_to_websocket(self, reading, device, patient)` helper method to `MQTTClient` in `backend/realtime/mqtt_client.py` and call it at the end of `_handle_reading_message` (after `self.tremor_service.process(reading)`); the method sends `{"type": "biometric_reading", "patient_id": patient.id, "device_serial": device.serial_number, "timestamp": reading.timestamp.isoformat(), "aX": float(reading.aX), "aY": float(reading.aY), "aZ": float(reading.aZ), "gX": float(reading.gX), "gY": float(reading.gY), "gZ": float(reading.gZ)}` to `patient_{patient.id}_tremor_data` channel group using `async_to_sync(self.channel_layer.group_send)`
- [X] T004 [P] Create `frontend/src/services/tremorWebSocketService.js` — class `TremorWebSocketService` with: `constructor(patientId, { onMessage, onConnected, onDisconnected, onError })` builds URL as `` `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/ws/tremor-data/${patientId}/?token=${getToken()}` `` (import `getToken` from `../utils/tokenStorage`); `connect()` opens the WebSocket, sets up `onopen`/`onmessage`/`onclose`/`onerror` handlers, starts 30-second ping interval, implements exponential-backoff auto-reconnect on close (delays: 1s→2s→4s→8s→16s→30s, max 10 attempts, stopped if `_destroyed`); `destroy()` sets `_destroyed = true`, clears timers, closes the socket; parse JSON in `onmessage` and route to `handlers.onMessage(parsedMsg)`

**Checkpoint**: Backend will now broadcast `biometric_reading` messages and frontend has a reconnecting WS client class.

---

## Phase 3: User Story 1 — Live Connection & Amplitude Chart (Priority: P1) 🎯 MVP

**Goal**: Doctor opens `/doctor/patients/:id/monitor`, WebSocket connects, rolling 60-second amplitude line chart populates and scrolls live.

**Independent Test**: Publish MQTT readings to `tremo/sensors/{device_id}` and verify the amplitude chart updates; stop the server and verify "Disconnected" status; restart and verify auto-reconnect.

- [X] T005 [US1] Create `frontend/src/hooks/useTremorMonitor.js` — custom hook `useTremorMonitor(patientId)` that: (a) holds a `TremorWebSocketService` instance in a `useRef`; (b) manages `connectionStatus` state (`'connecting'|'connected'|'disconnected'`); (c) maintains an amplitude `bufferRef` (useRef array) that receives `{ts: Date.parse(msg.timestamp), amplitude: Math.sqrt(aX²+aY²+aZ²)}` from each `biometric_reading` message at full 100Hz without calling setState; (d) runs a `setInterval` at 100ms (10Hz) that prunes the buffer to the last 60 000ms, copies it to `chartData` state; (e) stores `lastDataAtRef` (Date.now()) on each `biometric_reading`; (f) cleans up WS on unmount; returns `{ connectionStatus, chartData, lastDataAt }`
- [X] T006 [P] [US1] Create `frontend/src/components/tremor/ConnectionStatus.jsx` — receives `status` prop (`'connecting'|'connected'|'disconnected'`); renders a small badge: connecting=yellow pulse dot + "Connecting...", connected=green dot + "Connected", disconnected=red dot + "Disconnected" using Tailwind classes
- [X] T007 [P] [US1] Create `frontend/src/components/tremor/AmplitudeChart.jsx` — receives `data` prop (array of `{ts, amplitude}`) and `isStale` bool; renders a Recharts `<ResponsiveContainer height={260}><LineChart data={data}>` with `<XAxis dataKey="ts" type="number" scale="time" domain={['dataMin','dataMax']} tickCount={7} tickFormatter={(ms)=>`${Math.round((ms-Date.now())/1000)}s`} />`, `<YAxis domain={[0,'auto']} animationDuration={0} />`, `<Line type="linear" dataKey="amplitude" stroke="#6366f1" dot={false} isAnimationActive={false} animationDuration={0} strokeWidth={1.5} />`; when `isStale` is true, render a grey overlay with "(stale)" label; show "Waiting for data..." placeholder when `data` is empty
- [X] T008 [US1] Create `frontend/src/pages/LiveTremorPage.jsx` — uses `useParams` to get `id`; calls `useTremorMonitor(id)`; renders inside `AppLayout`: a header with "Live Monitor — {patient name}" and a back link to `/doctor/patients/${id}`; renders `<ConnectionStatus status={connectionStatus} />`; renders `<AmplitudeChart data={chartData} isStale={connectionStatus==='disconnected'} />`; leaves placeholder `div`s for spectrum chart, severity indicator, and raw values panel (to be added in later phases)
- [X] T009 [US1] Add lazy-loaded route `/doctor/patients/:id/monitor` to `frontend/src/routes/AppRoutes.jsx` — add `const LiveTremorPage = lazy(() => import('../pages/LiveTremorPage'))` and a `<Route path="/doctor/patients/:id/monitor" element={<ProtectedRoute><LiveTremorPage /></ProtectedRoute>} />` inside the existing `<Routes>`, placed after the `/doctor/patients/:id/edit` route

**Checkpoint**: Navigating to `/doctor/patients/1/monitor` should show the connection status badge and the live amplitude chart. Auto-reconnect on disconnect.

---

## Phase 4: User Story 2 — FFT Frequency Spectrum Chart (Priority: P2)

**Goal**: A bar chart showing frequency spectrum (Hz on X-axis, amplitude on Y-axis) updates ~1 Hz from `tremor_metrics_update` messages enhanced with full band arrays.

**Independent Test**: The bar chart should populate ~2.56 seconds after readings start flowing (first FFT window takes 256 samples). Bars should be taller at 4–6 Hz for Parkinsonian tremor.

- [X] T010 [US2] Extend `_run_fft_and_store` in `backend/realtime/filter_service.py` to add `dominant_band_freqs` and `dominant_band_amplitudes` to the WebSocket broadcast message: after computing `band_amp` for the dominant axis, append `"dominant_band_freqs": band_freqs.tolist()` and `"dominant_band_amplitudes": band_amp.tolist()` to the `message` dict before calling `channel_layer.group_send`
- [X] T011 [P] [US2] Extend `frontend/src/hooks/useTremorMonitor.js` to add `spectrumData` state: in the `onMessage` callback, handle `msg.type === 'tremor_metrics_update'` by calling `setSpectrumData(msg.dominant_band_freqs?.map((freq, i) => ({ freq: freq.toFixed(2), amplitude: msg.dominant_band_amplitudes?.[i] ?? 0 })) ?? [])`; return `spectrumData` from the hook
- [X] T012 [P] [US2] Create `frontend/src/components/tremor/SpectrumChart.jsx` — receives `data` prop (array of `{freq, amplitude}`) and `isStale` bool; renders `<ResponsiveContainer height={200}><BarChart data={data}><XAxis dataKey="freq" label={{ value: 'Hz', position: 'insideBottom', offset: -2 }} /><YAxis /><Bar dataKey="amplitude" fill="#a78bfa" isAnimationActive={false} /></BarChart></ResponsiveContainer>`; shows "Waiting for FFT..." when data is empty; applies grey overlay with "(stale)" when `isStale` is true; labels chart title as "Tremor Frequency Spectrum (dominant axis)"
- [X] T013 [US2] Replace the spectrum placeholder in `frontend/src/pages/LiveTremorPage.jsx` with `<SpectrumChart data={spectrumData} isStale={connectionStatus==='disconnected'} />` (import `SpectrumChart` and destructure `spectrumData` from `useTremorMonitor`)

**Checkpoint**: FFT bar chart populates and shows frequency content of the dominant tremor axis ~1 second after readings begin flowing.

---

## Phase 5: User Story 3 — Severity Indicator (Priority: P3)

**Goal**: Color-coded severity badge (green/amber/red) updates in real time from `tremor_data.prediction.severity`.

**Independent Test**: Publish a `devices/{serial}/data` MQTT session message and verify the badge changes color and label immediately.

- [X] T014 [US3] Extend `frontend/src/hooks/useTremorMonitor.js` to add `severity` state: handle `msg.type === 'tremor_data'` by calling `setSeverity({ level: msg.prediction?.severity ?? null, confidence: msg.prediction?.confidence ?? null })`; initialize as `{ level: null, confidence: null }`; return `severity` from the hook
- [X] T015 [P] [US3] Create `frontend/src/components/tremor/SeverityIndicator.jsx` — receives `severity` prop `{ level, confidence }` and `isStale` bool; renders a prominent badge with label and dot color: mild → `bg-green-100 border-green-300 text-green-800` label "Mild", moderate → `bg-amber-100 border-amber-300 text-amber-800` label "Moderate", severe → `bg-red-100 border-red-300 text-red-800` label "Severe", null → `bg-neutral-100 border-neutral-300 text-neutral-600` label "No Data"; when `isStale && level !== null`, append "(stale)" in small grey text; show confidence as "Confidence: 87%" beneath label when non-null
- [X] T016 [US3] Replace the severity placeholder in `frontend/src/pages/LiveTremorPage.jsx` with `<SeverityIndicator severity={severity} isStale={connectionStatus==='disconnected'} />` (import `SeverityIndicator` and destructure `severity` from `useTremorMonitor`)

**Checkpoint**: Severity badge changes color/label within 500ms of a session-level MQTT message arriving.

---

## Phase 6: User Story 4 — 6-Axis Raw Sensor Values Panel (Priority: P4)

**Goal**: A live panel showing Acc X/Y/Z and Gyro X/Y/Z values from `biometric_reading` messages; `hasActiveStream` detection enables "No active data stream" overlay.

**Independent Test**: Publish a `tremo/sensors/{device_id}` reading and verify all six values update immediately.

- [X] T017 [US4] Extend `frontend/src/hooks/useTremorMonitor.js` to add `rawValues` state and `hasActiveStream` detection: (a) on each `biometric_reading` message call `setRawValues({ aX: msg.aX, aY: msg.aY, aZ: msg.aZ, gX: msg.gX, gY: msg.gY, gZ: msg.gZ, timestamp: msg.timestamp })` AND update `lastDataAtRef.current = Date.now()`; (b) add a `setInterval` at 1 000ms that sets `setHasActiveStream(Date.now() - lastDataAtRef.current < 5000)`; (c) initialize `rawValues` as `null` and `hasActiveStream` as `false`; (d) return `rawValues` and `hasActiveStream` from the hook
- [X] T018 [P] [US4] Create `frontend/src/components/tremor/RawValuesPanel.jsx` — receives `rawValues` prop `{aX, aY, aZ, gX, gY, gZ, timestamp}|null` and `isStale` bool; renders a 2×3 grid (Accelerometer section + Gyroscope section) with labels "Acc X", "Acc Y", "Acc Z", "Gyro X", "Gyro Y", "Gyro Z"; formats floats to 3 decimal places with units (m/s² for acc, °/s for gyro); shows `—` dashes when `rawValues` is null; when `isStale && rawValues !== null`, applies a "(stale)" label to the panel header
- [X] T019 [US4] Replace the raw values placeholder in `frontend/src/pages/LiveTremorPage.jsx` with `<RawValuesPanel rawValues={rawValues} isStale={connectionStatus==='disconnected'} />` (import `RawValuesPanel` and destructure `rawValues` from `useTremorMonitor`)

**Checkpoint**: All six axis values update in the panel when `tremo/sensors/` MQTT messages arrive.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Navigation entry point, "No active stream" UX, and integration validation

- [X] T020 [P] Add a "Live Monitor" `<Link>` button to `frontend/src/pages/PatientDetailPage.jsx` — import `Link` from `react-router-dom`; add a button next to the existing "Edit" button that navigates to `` `/doctor/patients/${id}/monitor` ``; style: `bg-primary-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-primary-700`; label "Live Monitor"
- [X] T021 Add "No active data stream" overlay to `frontend/src/pages/LiveTremorPage.jsx` — when `connectionStatus === 'connected' && !hasActiveStream`, render an info banner (not a full-page block) above the charts: amber background, icon, text "No active data stream — check that the patient's device is powered on and connected."; destructure `hasActiveStream` from `useTremorMonitor`
- [X] T022 [P] Validate all five quickstart scenarios in `specs/034-live-tremor-monitor/quickstart.md` via code review — verify the implemented code handles: happy path, connection drop/reconnect, no active stream state, unauthorized access (4403 close code), and severity cycling

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories (US1 needs biometric_reading broadcast)
- **User Stories (Phase 3–6)**: All depend on Phase 2; execute in priority order P1 → P2 → P3 → P4
- **Polish (Phase 7)**: Depends on all four user stories (T020 needs T009 route; T021 needs T017 hook; T022 needs all)

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 complete — no dependency on US2/US3/US4
- **US2 (P2)**: Requires Phase 2 + US1 page structure (T008) — US2 tasks extend the hook and page
- **US3 (P3)**: Requires Phase 2 + US1 page structure (T008) — extends hook and page independently of US2
- **US4 (P4)**: Requires Phase 2 (biometric_reading broadcast) + US1 page structure (T008)

### Within Each User Story

- Hook extension tasks (T005, T011, T014, T017) are always sequential — they modify the same file
- Component tasks ([P]) can run parallel to hook tasks — they read only the data contract (not the hook source)
- Page integration tasks are always last in each story — they depend on hook + component

---

## Parallel Opportunities

### Phase 2 (All Three Parallel)
```
T002 [consumers.py]  ──┐
T003 [mqtt_client.py]──┤─→ Phase 3 can start
T004 [tremorWebSocketService.js] ──┘
```

### Phase 3 (US1)
```
T005 [useTremorMonitor.js] ──→ T006, T007 can now run in parallel
                                    T006 [ConnectionStatus.jsx]  ──┐
                                    T007 [AmplitudeChart.jsx]    ──┴→ T008 [LiveTremorPage.jsx] → T009
```

### Phase 4 (US2)
```
T010 [filter_service.py] ──┐
T011 [useTremorMonitor.js]─┤→ all complete → T013 [LiveTremorPage.jsx]
T012 [SpectrumChart.jsx]  ─┘
```

### Phase 5 (US3)
```
T014 [useTremorMonitor.js] ──┐
T015 [SeverityIndicator.jsx]─┴→ T016 [LiveTremorPage.jsx]
```

### Phase 6 (US4)
```
T017 [useTremorMonitor.js] ──┐
T018 [RawValuesPanel.jsx]  ──┴→ T019 [LiveTremorPage.jsx]
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003, T004)
3. Complete Phase 3: User Story 1 (T005–T009)
4. **STOP and VALIDATE**: Open `/doctor/patients/:id/monitor`, verify connection status badge and live amplitude chart scroll

### Incremental Delivery

1. Setup + Foundational → backend broadcasts live, WS service ready
2. US1 (T005–T009) → Amplitude chart live → **MVP demo-ready**
3. US2 (T010–T013) → FFT spectrum chart added
4. US3 (T014–T016) → Severity indicator added
5. US4 (T017–T019) → Raw values panel added
6. Polish (T020–T022) → Navigation entry + no-stream overlay + validation

Each story adds a visible panel without breaking the previous ones.

---

## Notes

- `useTremorMonitor.js` is extended in-place across US1–US4; each extension adds new state + message handler while preserving the existing ones
- `LiveTremorPage.jsx` is similarly extended across phases — start with placeholders and replace them
- The amplitude buffer uses `useRef` (not `useState`) to avoid 100 re-renders/sec at the sensor's 100Hz rate
- Recharts `isAnimationActive={false}` + `animationDuration={0}` are both required (workaround for Recharts bug #945)
- The `biometric_reading` broadcast (T002+T003) is the only backend change that must precede all frontend work; the filter_service enhancement (T010) only affects US2
