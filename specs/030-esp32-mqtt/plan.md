# Implementation Plan: ESP32 WiFi + MQTT Client

**Branch**: `030-esp32-mqtt` | **Date**: 2026-02-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/030-esp32-mqtt/spec.md`

## Summary

Feature 030 updates the ESP32 glove firmware's WiFi + MQTT publish pipeline to the new canonical message format. It replaces the legacy `devices/{serial}/reading` topic (100 Hz, QoS 0, `serial_number` field) with `tremo/sensors/{device_id}` (33 Hz, QoS 1, `device_id` + `battery_level` fields). This requires:

1. **Firmware** (C++ / Arduino / PlatformIO): swap MQTT library for QoS 1 support, add battery ADC module, update topic/payload/rate in the publisher, improve WiFi reconnection.
2. **Backend** (Django): update MQTT subscription topic and validator to accept the new field names and battery_level.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (patient/doctor)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/) + firmware/
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data (topic: `tremo/sensors/+`)
**Firmware Platform**: ESP32 Arduino (PlatformIO) — C++ — `firmware/` directory
**Firmware MQTT Library**: `256dpi/arduino-mqtt @ ^2.5.0` (replaces PubSubClient for QoS 1 support)
**Firmware JSON Library**: `bblanchon/ArduinoJson @ ^6.21.5` (existing)
**Performance Goals**: MQTT publish 30–50 Hz; reconnect within 10 s; battery ±5 % accuracy
**Constraints**: Local development only; credentials in `config.h` (gitignored); no Docker/CI/CD
**Scale/Scope**: One device per test session; single Mosquitto broker on dev machine

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [X] **Monorepo Architecture**: Backend changes are in `backend/`. Firmware lives in `firmware/` — **justified exception** (hardware code cannot reside in `backend/` or `frontend/`; `firmware/` is an established precedent from Feature 025).
- [X] **Tech Stack Immutability**: No new framework added to backend/frontend. Firmware uses C++/Arduino — **justified exception** (ESP32 hardware requires embedded C++; no alternative exists).
- [X] **Database Strategy**: No new database models in this feature. Uses Supabase PostgreSQL via existing `BiometricReading` model.
- [X] **Authentication**: No user auth changes. JWT unchanged.
- [X] **Security-First**: WiFi/MQTT credentials in `firmware/include/config.h` (gitignored). Broker credentials remain in `.env` on the backend.
- [X] **Real-time Requirements**: Backend forwards MQTT data to WebSocket clients via existing Django Channels consumer (unchanged in this feature).
- [X] **MQTT Integration**: Feature IS the MQTT publish side. Backend subscription is updated to match new topic. Fully compliant.
- [X] **AI Model Serving**: Not affected.
- [X] **API Standards**: Backend validator updated; no new REST endpoints. Existing MQTT handler handles new topic.
- [X] **Development Scope**: Local development only. No Docker/CI/CD.

**Result**: ✅ PASS — Two justified violations documented in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/030-esp32-mqtt/
├── plan.md              # This file
├── research.md          # Phase 0: QoS 1 library, rate, battery ADC, topic decisions
├── data-model.md        # Phase 1: SensorMessage, BatteryReading, FusedReading
├── quickstart.md        # Phase 1: Integration scenarios, verification steps
├── contracts/
│   └── mqtt-sensor-message.yaml   # AsyncAPI 2.6 message contract
└── checklists/
    └── requirements.md
```

### Source Code Changes

```text
firmware/
├── platformio.ini          MODIFY — swap PubSubClient → arduino-mqtt; add MQTT_MAX_PACKET_SIZE build flag
├── include/
│   ├── config.h.example    MODIFY — add BATTERY_ADC_PIN, MQTT_PUBLISH_RATE_HZ constants
│   ├── battery_reader.h    CREATE — BatteryReading struct + read_battery() API
│   └── mqtt_publisher.h    MODIFY — update FusedReading (add battery_level), update topic/payload docs
└── src/
    ├── battery_reader.cpp  CREATE — ADC read, voltage conversion, LiPo % mapping
    ├── mqtt_publisher.cpp  MODIFY — new MQTT lib API, new topic, new payload, QoS 1, non-blocking WiFi reconnect, publish rate throttle
    └── main.cpp            MODIFY — add publish-rate guard (33 Hz), populate battery_level in FusedReading

backend/
├── realtime/
│   ├── validators.py       MODIFY — accept device_id (rename from serial_number), add battery_level validation
│   └── mqtt_client.py      MODIFY — subscribe to tremo/sensors/+ (was devices/+/reading), extract device_id
└── .env.example            MODIFY (if present) — no changes needed; MQTT broker config unchanged
```

## Implementation Strategy

### Phase 1 — Firmware Library Swap + Config (US1 foundation)

Swap PubSubClient for arduino-mqtt in `platformio.ini` and update `config.h.example` with new constants. This is a prerequisite for all firmware tasks.

**Files**: `firmware/platformio.ini`, `firmware/include/config.h.example`

### Phase 2 — Battery ADC Module (US1)

Create `battery_reader.h` and `battery_reader.cpp`. Provides `read_battery()` → float (0.0–100.0). Independent of MQTT changes.

**Files**: `firmware/include/battery_reader.h`, `firmware/src/battery_reader.cpp`

### Phase 3 — MQTT Publisher Rewrite (US1 + US2 + US3)

Update `mqtt_publisher.h/cpp`:
- Switch to `256dpi/arduino-mqtt` API (`MQTTClient` instead of `PubSubClient`)
- Change topic to `tremo/sensors/{DEVICE_SERIAL}`
- Update payload: `device_id` field (was `serial_number`), add `battery_level`
- Publish with QoS 1: `mqttClient.publish(topic, payload, false, 1)`
- Implement non-blocking WiFi reconnect in `mqtt_loop()`
- Add publish-rate throttle: publish only when `millis() - last_publish_ms >= (1000 / MQTT_PUBLISH_RATE_HZ)`

**Files**: `firmware/include/mqtt_publisher.h`, `firmware/src/mqtt_publisher.cpp`

### Phase 4 — Main Loop Integration (US1 + US2)

Update `main.cpp`:
- Add publish-rate guard so MQTT publish happens at ~33 Hz while Kalman runs at 100 Hz
- Pass `battery_level` from `read_battery()` into `g_fused.battery_level` before calling `publish_reading()`

**Files**: `firmware/src/main.cpp`

### Phase 5 — Backend Validator Update (US1 + US3)

Update `validate_biometric_reading_message()` in `validators.py`:
- Required field: `device_id` instead of `serial_number`
- Optional validated field: `battery_level` (numeric, 0–100)
- Update `validate_device_pairing()` call to pass `device_id`

**Files**: `backend/realtime/validators.py`

### Phase 6 — Backend MQTT Subscription Update (US1)

Update `mqtt_client.py`:
- Subscribe to `tremo/sensors/+` (was `devices/+/reading`)
- Extract `device_id` from payload (was `serial_number`)
- Extract `battery_level` from payload (log it; no persistence in this feature)
- Update `_extract_serial()` helper to use topic path `tremo/sensors/{device_id}` format

**Files**: `backend/realtime/mqtt_client.py`

### Phase 7 — README Update

Update `firmware/README.md`:
- New topic, new payload example
- Updated troubleshooting table

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| `firmware/` directory outside `backend/`/`frontend/` | ESP32 hardware firmware cannot be a Django or React module | No alternative: C++ hardware code cannot live in a Python or JS project directory |
| C++ / Arduino framework — outside constitutional stack | ESP32 requires embedded C++; Arduino/ESP-IDF are the only SDKs for the hardware | No alternative: the microcontroller does not run Python or JavaScript |
