# Research: ESP32 WiFi + MQTT Client (Feature 030)

**Branch**: `030-esp32-mqtt`
**Date**: 2026-02-19

---

## Decision 1: MQTT Library for QoS 1 Publish

**Decision**: Replace `PubSubClient` (knolleary) with `MQTT` (256dpi/arduino-mqtt) for QoS 1 publish support.

**Rationale**: PubSubClient v2.8 does NOT support QoS 1 for the PUBLISH direction. The `publish()` call always sends a QoS 0 PUBLISH packet — the library omits QoS bits in the PUBLISH header. The spec explicitly requires QoS 1 (at-least-once delivery). The `256dpi/arduino-mqtt` library (Joel Gaehwiler) supports QoS 0 and 1 for both publish and subscribe, with a simple synchronous API similar to PubSubClient.

**Migration**:
- PlatformIO `lib_deps`: swap `knolleary/PubSubClient @ ^2.8.0` → `256dpi/arduino-mqtt @ ^2.5.0`
- API change: `mqttClient.publish(topic, payload, retained, qos)` (4th argument = QoS level)
- `mqttClient.begin(host, port, client)` replaces `mqttClient.setServer()`
- `mqttClient.connect(clientId)` same signature

**Alternatives considered**:
- `AsyncMQTT_ESP32` (khoih-prog fork of marvinroger/AsyncMqttClient): Supports QoS 1 natively with FreeRTOS timers and handles PUBACK/PUBREC/PUBCOMP correctly. However, its async model requires callback-based publish rather than the inline synchronous `publish()` call — incompatible with the existing synchronous Kalman loop without significant refactoring. A known TCP disconnect bug (~60 s) with Mosquitto 2.x also makes it less attractive for development.
- `esp-mqtt` (Espressif IDF component): Requires ESP-IDF framework, not Arduino — incompatible with existing Arduino build.
- Keep PubSubClient v2.8 with `loop()`-before-`publish()` workaround: PubSubClient's `publish()` always sends a QoS 0 PUBLISH packet regardless of the QoS argument — it does not set the QoS bits in the MQTT fixed header and does not await or process PUBACK at high publish rates. At 30–50 Hz, this means effectively QoS 0 delivery semantics. Rejected because the spec explicitly requires QoS 1.

---

## Decision 2: Publish Rate vs IMU Sampling Rate

**Decision**: IMU continues to sample and run the Kalman filter at 100 Hz. MQTT publishes every 3rd Kalman tick (≈33 Hz), which satisfies the 30–50 Hz spec.

**Rationale**: The Kalman filter accuracy improves with higher input frequency. Reducing the IMU ODR to 33 Hz would degrade orientation estimation and potentially affect the PID controller (Feature 029). A software-level publish throttle (one `uint32_t last_publish_ms` guard with a 30 ms threshold) cleanly decouples IMU rate from publish rate with no hardware changes.

At 33 Hz, the inter-publish interval is 30 ms. The MQTT library's `loop()` still runs on every 100 Hz tick to maintain keepalive and process PUBACK packets.

**Alternatives considered**:
- Set IMU ODR to 33 Hz (SMPLRT_DIV = 0x1D): Reduces Kalman filter quality; rejected.
- Publish on every IMU tick (100 Hz): Exceeds the 30–50 Hz spec; also increases broker load and battery drain.

---

## Decision 3: Battery ADC Reading

**Decision**: Read battery level via `analogReadMilliVolts()` on a dedicated ADC pin (GPIO34) connected to a resistive voltage divider. Average 16 samples. Map the LiPo voltage range (3.0 V = 0 %, 4.2 V = 100 %) to a percentage, clamped to [0, 100].

**Rationale**: The ESP32 has a 12-bit ADC (0–4095 counts, 0–3.3 V input). `analogReadMilliVolts()` is preferred over raw `analogRead()` because the ESP32 Arduino core applies a factory-calibrated ADC correction curve when reading in millivolts, eliminating much of the hardware non-linearity near the rail ends. Without this correction, `analogRead()` values are inaccurate especially below 0.15 V and above 3.1 V at the ADC pin. A voltage divider (e.g. 100 kΩ high-side + 47 kΩ low-side, ratio ≈ 0.32) keeps the ADC-pin voltage well within the accurate range for a 3.7 V LiPo (3.0–4.2 V → ~0.96–1.34 V at ADC pin). Averaging 16 samples reduces noise without meaningful latency.

**Critical ADC pin constraint**: ESP32's ADC2 pins (GPIO0, 2, 4, 12–15, 25–27) share hardware with the WiFi radio and produce unreliable readings whenever WiFi is active. The battery ADC pin MUST be on ADC1 (GPIO32–39). GPIO34–39 are input-only pins, ideal for analog monitoring. `BATTERY_ADC_PIN = 34` (GPIO34) is the recommended default. Call `analogSetAttenuation(ADC_11db)` once during setup to configure the full 0–3.3 V input range.

Battery is read once per MQTT publish cycle (~33 Hz) — no separate timer needed.

**Alternatives considered**:
- Fuel gauge IC (e.g. MAX17048 via I2C): Higher accuracy but requires hardware addition not in existing BOM.
- ADC2 pins: Unreliable when WiFi active — must not be used.
- Raw `analogRead()` without `ADC_11db` attenuation: Defaults to 0–1.1 V range on ESP32, causing premature saturation for a battery voltage divider. Must set attenuation.
- Read every 100 Hz tick: No benefit; battery charge changes slowly.

---

## Decision 4: Credential and Configuration Storage

**Decision**: Retain the existing `firmware/include/config.h` pattern (template at `config.h.example`, real values in gitignored `config.h`).

**Rationale**: The pattern is already established in Feature 025 and documented in the README. PlatformIO build_flags with environment variables were considered but add build-system complexity; the config.h approach is simpler for a local development project.

New constants added to `config.h.example`: `BATTERY_ADC_PIN`, `MQTT_PUBLISH_RATE_HZ`.

---

## Decision 5: Topic and Payload Field Naming Alignment

**Decision**: Both firmware and backend are updated to the new canonical names:
- MQTT topic: `tremo/sensors/{device_id}` (was `devices/{serial}/reading`)
- Payload field: `device_id` (was `serial_number`)
- New payload field: `battery_level` (float 0.0–100.0)

**Rationale**: `tremo/sensors/` is a cleaner namespace for the platform. Using `device_id` as the field name aligns with the rest of the platform's JSON naming (`device_id` is the foreign key name used in backend models). The backend validator `validate_biometric_reading_message()` and the MQTT subscription in `mqtt_client.py` must be updated to match.

**Alternatives considered**:
- Publish to both old and new topics simultaneously: Adds complexity and doubles broker load; no backward-compatibility requirement in a development project.
- Accept both field names in the backend validator: More complex validator for no benefit.

---

## Decision 6: Non-Blocking WiFi Reconnection

**Decision**: Replace the blocking `while (!WiFi.connected()) { delay(250); }` in `wifi_connect()` with a non-blocking retry called from `mqtt_loop()`.

**Rationale**: The current startup WiFi connection (Feature 025) uses a blocking wait with a 10-second timeout. This is acceptable at boot. However, the spec requires automatic reconnection mid-session (US2). Blocking the main loop for up to 10 seconds during reconnect would halt MQTT keepalive, potentially closing the TCP socket. Implementing a non-blocking WiFi reconnect state (`wifi_reconnecting` flag) in `mqtt_loop()` allows the loop to continue calling `mqttClient.loop()` and attempt WiFi reconnect in parallel.

**Pattern**:
```
mqtt_loop():
  if WiFi.status() != WL_CONNECTED:
    attempt WiFi.reconnect() with backoff
    return early (no MQTT loop while WiFi down)
  if !mqttClient.connected():
    attempt broker_connect()
  mqttClient.loop()
```

---

## Decision 7: ArduinoJson Document Size for New Payload

**Decision**: Retain `StaticJsonDocument<256>` for the new payload.

**Rationale**: The new 9-field payload serializes to approximately:
```json
{"device_id":"GLOVE001A","timestamp":"2026-02-18T10:30:00.123Z","aX":0.1234,"aY":-0.0456,"aZ":9.7654,"gX":12.345,"gY":-5.678,"gZ":0.123,"battery_level":87.5}
```
This is ~175 bytes serialized. A `StaticJsonDocument<256>` (for the in-memory tree, not the serialized output) is sufficient. The `char payload[256]` buffer for `serializeJson()` remains adequate.

The `256dpi/arduino-mqtt` library's default max packet size is configurable via `MQTT_MAX_PACKET_SIZE`. Setting it to 512 bytes in `platformio.ini` build_flags (`-DMQTT_MAX_PACKET_SIZE=512`) provides headroom.
