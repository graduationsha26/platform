/**
 * mqtt_publisher.h — MQTT Publisher: WiFi + MQTT Connection and JSON Payload
 *
 * Feature: 025-imu-kalman-fusion
 * Feature: 030-esp32-mqtt (QoS 1, new topic, battery_level, 33 Hz throttle)
 * Feature: 031-freertos-scheduler (adds t_sensor_us for sensor-to-actuation latency measurement)
 *
 * Publishes FusedReading structs as JSON to MQTT topic:
 *   tremo/sensors/{DEVICE_SERIAL}
 *
 * JSON payload schema (matches backend validator in
 *   backend/realtime/validators.py: validate_biometric_reading_message()):
 *
 *   {
 *     "device_id":     "GLOVE001A",
 *     "timestamp":     "2026-02-18T10:30:00.123Z",
 *     "aX":            0.42,
 *     "aY":           -0.15,
 *     "aZ":            9.75,
 *     "gX":            12.3,
 *     "gY":            -5.6,
 *     "gZ":            0.8,
 *     "battery_level": 87.5
 *   }
 *
 * The roll and pitch fields in FusedReading are firmware-internal estimates
 * and are NOT included in the MQTT payload (no corresponding backend model field).
 * The battery_level field is populated in main.cpp before each publish_reading() call.
 *
 * WiFi: ESP32 Arduino WiFi library
 * MQTT: 256dpi/arduino-mqtt (MQTTClient) — supports QoS 1 publish
 * JSON: ArduinoJson 6.x (bblanchon/ArduinoJson)
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>

// ─── FusedReading ─────────────────────────────────────────────────────────────

/**
 * FusedReading — Output of one complete Kalman fusion cycle.
 * Written by SensorTask via xQueueOverwrite; read by ControlTask and MqttTask via xQueuePeek.
 *
 *   aX..gZ:        Calibrated sensor values for MQTT payload
 *   roll, pitch:   Kalman-filtered orientation angles (firmware-internal only, not in MQTT payload)
 *   timestamp_iso: ISO 8601 UTC string, e.g. "2026-02-18T10:30:00.123Z"
 *                  Populated by publish_reading() using NTP-derived time.
 *   battery_level: Battery state of charge (0.0–100.0 %).
 *                  Populated by MqttTask via read_battery() before publish_reading().
 *   t_sensor_us:   esp_timer_get_time() at end of Kalman update (µs since boot).
 *                  Written by SensorTask; read by ControlTask to compute
 *                  sensor-to-actuation latency (target: < 70,000 µs).
 */
typedef struct {
    float    aX, aY, aZ;       // m/s², calibrated
    float    gX, gY, gZ;       // °/s, calibrated
    float    roll;              // degrees, Kalman-filtered (not in MQTT payload)
    float    pitch;             // degrees, Kalman-filtered (not in MQTT payload)
    char     timestamp_iso[32]; // ISO 8601 UTC, populated by publish_reading()
    float    battery_level;     // % (0.0–100.0), populated by MqttTask before publish
    uint64_t t_sensor_us;       // esp_timer_get_time() at end of Kalman update (µs since boot)
                                // Used by ControlTask to compute sensor-to-actuation latency
} FusedReading;

// ─── API ─────────────────────────────────────────────────────────────────────

/**
 * mqtt_connect() — Connect WiFi and MQTT broker.
 *
 * 1. WiFi.begin(WIFI_SSID, WIFI_PASSWORD) — waits up to 10s
 * 2. Initializes NTP (configTime) for ISO 8601 timestamp generation
 * 3. mqttClient.connect(DEVICE_SERIAL, MQTT_USERNAME, MQTT_PASSWORD)
 *
 * Returns: true if both WiFi and MQTT connected successfully.
 * On false: caller should log warning but NOT halt (retry via mqtt_loop).
 */
bool mqtt_connect();

/**
 * mqtt_loop() — Maintain MQTT connection and process incoming messages.
 *
 * Must be called every loop iteration (after publish_reading).
 * Reconnects automatically if connection dropped.
 *
 * Call once per 100Hz tick to maintain keepalive.
 */
void mqtt_loop();

/**
 * publish_reading() — Serialize FusedReading to JSON and publish to MQTT (QoS 1).
 *
 * Builds the JSON payload using ArduinoJson StaticJsonDocument<256>.
 * Populates reading->timestamp_iso with current NTP-derived UTC time.
 * Publishes to topic: "tremo/sensors/" DEVICE_SERIAL  (QoS 1, retain=false)
 *
 * The JSON includes the fields expected by the backend validator:
 *   device_id, timestamp, aX, aY, aZ, gX, gY, gZ, battery_level
 *
 * reading->battery_level must be populated by the caller (main.cpp) before
 * calling publish_reading(). It is included as-is in the JSON payload.
 *
 * @param reading  FusedReading with battery_level populated by caller
 * Returns: true if publish succeeded, false on MQTT error (silently drops)
 */
bool publish_reading(FusedReading* reading);
