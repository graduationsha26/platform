# Tasks: ESP32 WiFi + MQTT Client (Feature 030)

**Input**: Design documents from `/specs/030-esp32-mqtt/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story. US1 (streaming) is the MVP. US2 (reconnection) extends mqtt_publisher.cpp. US3 (QoS 1) is verified via the library + publish call established in US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- Paths: `firmware/` (ESP32 C++/Arduino), `backend/` (Django Python)

---

## Phase 1: Setup (Library Swap + Config)

**Purpose**: Swap MQTT library for QoS 1 support and add new firmware configuration constants. Both tasks touch different files and can run in parallel.

- [X] T001 [P] Update `firmware/platformio.ini` — replace `knolleary/PubSubClient @ ^2.8.0` with `256dpi/arduino-mqtt @ ^2.5.0` in `lib_deps`; add `-DMQTT_MAX_PACKET_SIZE=512` to `build_flags` section
- [X] T002 [P] Update `firmware/include/config.h.example` — add `BATTERY_ADC_PIN 34` (GPIO34, ADC1), `MQTT_PUBLISH_RATE_HZ 33`, `BATTERY_DIVIDER_RATIO` (47.0 / 147.0), `BATTERY_V_MIN 3.0f`, `BATTERY_V_MAX 4.2f` constants with inline comments; update file header comment to reference Feature 030

---

## Phase 2: Foundational (Backend Alignment)

**Purpose**: Update backend to accept the new MQTT topic and payload field names. Both tasks touch different files and can run in parallel. Backend must be aligned before end-to-end integration can be verified.

**⚠️ CRITICAL**: End-to-end validation cannot succeed until both T003 and T004 are complete.

- [X] T003 [P] Update `backend/realtime/validators.py` — in `validate_biometric_reading_message()`: rename required field `serial_number` → `device_id` (update `required_fields` list and the serial_number validation block to validate `device_id` instead); add optional `battery_level` field validation (must be numeric, log WARNING if outside 0–100, do not reject); update `validate_device_pairing()` call to pass `payload['device_id']`; update function docstring
- [X] T004 [P] Update `backend/realtime/mqtt_client.py` — change MQTT subscription from `devices/+/reading` to `tremo/sensors/+`; update the `on_connect` subscribe call and the `on_message` topic-pattern matching/dispatch to route `tremo/sensors/+` messages to the biometric reading handler; update the `_extract_serial()` helper (or equivalent) to parse `device_id` from the new topic path `tremo/sensors/{device_id}` (position index 2 when split on `/`); extract `device_id` from payload (was `serial_number`) when calling `validate_biometric_reading_message` and `validate_device_pairing`; extract `battery_level` from payload and log it at DEBUG level

**Checkpoint**: Backend now accepts `tremo/sensors/+` messages with `device_id` field. MQTT client ready for new firmware.

---

## Phase 3: User Story 1 — Continuous Sensor Data Streaming (Priority: P1) 🎯 MVP

**Goal**: Glove connects to WiFi + MQTT broker and continuously publishes 9-axis IMU data + battery level as JSON to `tremo/sensors/{device_id}` at 30–50 Hz.

**Independent Test**: Flash firmware, run `mosquitto_sub -t "tremo/sensors/+" -v`, verify well-formed JSON messages arrive at ~33 Hz with all 9 fields including `battery_level`.

- [X] T005 [P] [US1] Create `firmware/include/battery_reader.h` — define `BatteryReading` struct (fields: `adc_mv` uint32_t, `voltage_v` float, `percentage` float); declare `battery_init()` (void) and `read_battery()` (returns float 0.0–100.0) functions; add `#pragma once` guard; add header comment referencing Feature 030
- [X] T006 [P] [US1] Update `firmware/include/mqtt_publisher.h` — add `float battery_level` field to `FusedReading` struct (after `pitch`); update struct comment to note `battery_level` is populated before `publish_reading()` call; update `publish_reading()` doc comment to reflect new payload format (`device_id`, `battery_level`) and new topic (`tremo/sensors/{DEVICE_SERIAL}`); remove PubSubClient references and update library reference to `256dpi/arduino-mqtt`
- [X] T007 [US1] Create `firmware/src/battery_reader.cpp` — implement `battery_init()`: call `analogSetAttenuation(ADC_11db)` on `BATTERY_ADC_PIN`; implement `read_battery()`: average 16 `analogReadMilliVolts(BATTERY_ADC_PIN)` readings, compute `voltage_v = (avg_mv / 1000.0f) / BATTERY_DIVIDER_RATIO`, compute `percentage = (voltage_v - BATTERY_V_MIN) / (BATTERY_V_MAX - BATTERY_V_MIN) * 100.0f`, return `constrain(percentage, 0.0f, 100.0f)`; include `battery_reader.h` and `config.h` (depends on T005, T002)
- [X] T008 [US1] Rewrite `firmware/src/mqtt_publisher.cpp` — switch from `PubSubClient` to `MQTT.h` (`256dpi/arduino-mqtt`) API: replace `WiFiClient` + `PubSubClient` declarations with `WiFiClient` + `MQTTClient mqttClient(512)` (512-byte buffer); replace `mqttClient.setServer()` with `mqttClient.begin(MQTT_BROKER_HOST, MQTT_BROKER_PORT, wifiClient)`; build topic string as `tremo/sensors/{DEVICE_SERIAL}`; update `publish_reading()` JSON payload: rename `serial_number` field → `device_id`, add `doc["battery_level"] = reading->battery_level`; change publish call to `mqttClient.publish(mqtt_topic, payload, false, 1)` (QoS 1); implement `wifi_connect()` and `broker_connect()` using the new library's `mqttClient.connect(DEVICE_SERIAL)` / `mqttClient.connect(DEVICE_SERIAL, MQTT_USERNAME, MQTT_PASSWORD)` API; keep `mqtt_connect()` and `mqtt_loop()` public API signatures unchanged so main.cpp needs no changes beyond T009; keep NTP/ISO8601 timestamp logic unchanged (depends on T006, T001)
- [X] T009 [US1] Update `firmware/src/main.cpp` — add `#include "battery_reader.h"`; add `battery_init()` call in `setup()` after IMU calibration and before `mqtt_connect()`; add a `static uint32_t last_publish_ms = 0` variable and a publish-rate guard in `loop()`: replace the direct `publish_reading(&g_fused)` call with a block that checks `(millis() - last_publish_ms) >= (1000UL / MQTT_PUBLISH_RATE_HZ)`, sets `last_publish_ms = millis()`, then reads `g_fused.battery_level = read_battery()` and calls `publish_reading(&g_fused)`; keep `mqtt_loop()` call outside the rate guard so it runs every 100Hz tick for keepalive (depends on T007, T008)

**Checkpoint**: US1 complete. Flash firmware, observe serial monitor showing `[MQTT] Publishing to topic: tremo/sensors/GLOVE001A`, verify `mosquitto_sub -t "tremo/sensors/+" -v` shows ~33 messages/second with `battery_level` field present.

---

## Phase 4: User Story 2 — Automatic Reconnection on Network Loss (Priority: P2)

**Goal**: When WiFi or MQTT connection drops, the glove reconnects automatically within 10 seconds without rebooting or blocking the sensor loop.

**Independent Test**: With firmware running and streaming, restart Mosquitto broker. Within 10 seconds, `mosquitto_sub` should resume receiving messages with no manual intervention.

- [X] T010 [US2] Extend `firmware/src/mqtt_publisher.cpp` — replace the simple `if (!mqttClient.connected()) { broker_connect(); }` in `mqtt_loop()` with a 4-state non-blocking FSM: states are `CONN_WIFI_DOWN`, `CONN_WIFI_CONNECTING`, `CONN_MQTT_DOWN`, `CONN_READY`; add `static uint32_t lastWifiAttemptMs`, `lastMqttAttemptMs` and `const uint32_t WIFI_RETRY_MS = 10000`, `MQTT_RETRY_MS = 5000`; in `CONN_WIFI_DOWN`: if retry interval elapsed, call `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)` and transition to `CONN_WIFI_CONNECTING`; in `CONN_WIFI_CONNECTING`: if `WiFi.status() == WL_CONNECTED`, call `configTime(0, 0, "pool.ntp.org")` and transition to `CONN_MQTT_DOWN`; else if timeout elapsed, call `WiFi.disconnect()` and return to `CONN_WIFI_DOWN`; in `CONN_MQTT_DOWN`: if retry interval elapsed and WiFi still connected, attempt `mqttClient.connect(...)` and transition to `CONN_READY` on success; in `CONN_READY`: check WiFi and MQTT still connected on every call, downgrade state if either drops; call `mqttClient.loop()` only in `CONN_READY`; update `mqtt_loop()` docstring to describe FSM states and retry intervals (depends on T008)

**Checkpoint**: US2 complete. Kill and restart Mosquitto while firmware is running. Serial monitor shows reconnect attempt then `[MQTT] Broker connected.` within 10 seconds. Streaming resumes.

---

## Phase 5: User Story 3 — Reliable Message Delivery with QoS 1 (Priority: P3)

**Goal**: All published messages use QoS 1 (at-least-once delivery) — the broker sends PUBACK for each message, and the firmware library retransmits any unacknowledged messages.

**Independent Test**: Run `mosquitto -v` and observe `Sending PUBACK` entries corresponding to every `PUBLISH` from the glove. No QoS 0 publishes should appear.

- [X] T011 [US3] Update `firmware/README.md` — change MQTT topic in all examples from `devices/+/reading` to `tremo/sensors/+`; update example payload to show `device_id` field (not `serial_number`) and add `battery_level` field; add new "QoS 1 Delivery Verification" section documenting how to confirm QoS 1 is active using `mosquitto -v` verbose log (show expected PUBLISH + PUBACK log entries); update `mosquitto_sub` example command; update Verify Operation section for new 33 Hz rate; update troubleshooting table with new rows for `battery_level: 0` and `QoS shows 0 in broker log` scenarios

**Checkpoint**: US3 complete. QoS 1 was implemented in T001 (library) + T008 (publish call). Verification: `mosquitto -v` log shows `Sending PUBACK to GLOVE001A` after each PUBLISH.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate build health and end-to-end integration for all user stories.

- [ ] T012 [P] Validate firmware build — run `pio run` (compile only, no upload) from the `firmware/` directory and confirm zero compilation errors with `256dpi/arduino-mqtt` and all modified source files; fix any compilation errors before proceeding
- [X] T013 [P] Validate backend system check — run `python manage.py check` from `backend/` and confirm `System check identified no issues (0 silenced)` after `validators.py` and `mqtt_client.py` changes
- [ ] T014 Run quickstart end-to-end integration — follow `specs/030-esp32-mqtt/quickstart.md` Scenario 1: start Mosquitto, start Django backend, flash firmware, verify `mosquitto_sub -t "tremo/sensors/+" -v` receives ~33 messages/second; verify backend `BiometricReading.objects.count()` increases at ~33/s; confirm payload contains `device_id` and `battery_level` fields

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 can start immediately and run in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 completion (T003, T004 need new config constants for reference) — T003 and T004 can run in parallel
- **US1 (Phase 3)**: Depends on Phase 1 + Phase 2 completion — T005/T006 parallel; T007 after T005; T008 after T006; T009 after T007 and T008
- **US2 (Phase 4)**: Depends on T008 (extends same file) — T010 must run after T008
- **US3 (Phase 5)**: Depends on T008 + T010 (QoS 1 already implemented; this adds verification documentation) — T011 after T010
- **Polish (Phase 6)**: T012 and T013 can run in parallel after Phase 5; T014 after T012 and T013

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 1 + Phase 2 — core streaming MVP
- **US2 (P2)**: Depends on T008 from US1 (same file, extends mqtt_loop FSM)
- **US3 (P3)**: Depends on T008 and T010 (QoS 1 is in T008, this phase only adds verification docs)

### Within Phase 3 (US1)

```
T001, T002 (parallel)
    ↓
T003, T004 (parallel)
    ↓
T005, T006 (parallel)
    ↓
T007 (after T005)    T008 (after T006)
         \              /
              T009
```

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002 (different files)
- **Phase 2**: T003 ∥ T004 (different files)
- **Phase 3**: T005 ∥ T006 (different files); T007 ∥ T008 (different files, both after their respective headers)
- **Phase 6**: T012 ∥ T013 (firmware vs backend, independent)

---

## Parallel Example: Phase 3 (US1)

```bash
# Step 1 — headers in parallel:
Task: "Create firmware/include/battery_reader.h (T005)"
Task: "Update firmware/include/mqtt_publisher.h (T006)"

# Step 2 — implementations in parallel (after respective headers):
Task: "Create firmware/src/battery_reader.cpp (T007)"   # after T005
Task: "Rewrite firmware/src/mqtt_publisher.cpp (T008)"  # after T006

# Step 3 — main.cpp (after both T007 and T008):
Task: "Update firmware/src/main.cpp (T009)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational — backend alignment (T003, T004)
3. Complete Phase 3: User Story 1 — core streaming (T005–T009)
4. **STOP and VALIDATE**: Flash firmware, confirm messages arrive at `tremo/sensors/+` at ~33 Hz with full payload
5. Demo: Platform receives glove data via new topic + payload format

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001–T004)
2. US1 complete → MVP streaming (T005–T009) — **demo-ready**
3. US2 complete → Reliable sessions (T010) — reconnect tested
4. US3 complete → QoS 1 documented and verified (T011)
5. Polish → Full validation (T012–T014)

---

## Notes

- [P] = different files, no blocking dependencies — safe to parallelize
- `firmware/src/mqtt_publisher.cpp` is modified by T008 (US1) and extended by T010 (US2) — these MUST run sequentially
- US3 (QoS 1) is architecturally implemented in T001 (library choice) and T008 (publish call arg) — T011 adds documentation and verification procedure only
- `config.h` (gitignored) must be updated by the developer after T002 updates `config.h.example`
- ADC pin `BATTERY_ADC_PIN = 34` (GPIO34) is on ADC1 — do NOT change to an ADC2 pin (GPIO0/2/4/12-15/25-27 conflict with WiFi radio)
- `analogSetAttenuation(ADC_11db)` is required in `battery_init()` — default ADC range is 0–1.1V, insufficient for battery monitoring
