/**
 * mqtt_publisher.cpp — WiFi + MQTT Connection and JSON Payload Publisher
 *
 * Feature: 025-imu-kalman-fusion
 * Feature: 030-esp32-mqtt (256dpi/arduino-mqtt, QoS 1, tremo/sensors/ topic,
 *                          battery_level field, 33 Hz throttle via main.cpp)
 *
 * Implements:
 *   mqtt_connect()    — WiFi + NTP + MQTT broker connection
 *   mqtt_loop()       — keepalive and reconnect
 *   publish_reading() — JSON serialization and QoS 1 MQTT publish
 *
 * MQTT topic: tremo/sensors/{DEVICE_SERIAL}
 *
 * JSON payload (matches backend/realtime/validators.py:
 *   validate_biometric_reading_message()):
 *   {
 *     "device_id":     "GLOVE001A",
 *     "timestamp":     "2026-02-18T10:30:00.123Z",
 *     "aX": 0.42, "aY": -0.15, "aZ": 9.75,
 *     "gX": 12.3, "gY": -5.6,  "gZ": 0.8,
 *     "battery_level": 87.5
 *   }
 *
 * Note: roll and pitch from FusedReading are firmware-internal only
 * and are NOT included in the MQTT payload.
 */

#include "mqtt_publisher.h"
#include "config.h"
#include <WiFi.h>
#include <MQTT.h>           // 256dpi/arduino-mqtt @ ^2.5.0 — supports QoS 1 publish
#include <ArduinoJson.h>
#include <Arduino.h>
#include <time.h>

// ─── MQTT client instances ────────────────────────────────────────────────────

static WiFiClient  wifiClient;
static MQTTClient  mqttClient(512);   // 512-byte buffer (MQTT_MAX_PACKET_SIZE=512)

// ─── MQTT topic ───────────────────────────────────────────────────────────────

static char mqtt_topic[64];   // "tremo/sensors/{DEVICE_SERIAL}"

// ─── Internal helpers ─────────────────────────────────────────────────────────

/**
 * wifi_connect() — Connect to WiFi and initialize NTP.
 * Returns true if WiFi connected within 10 seconds.
 */
static bool wifi_connect() {
    Serial.printf("[MQTT] Connecting to WiFi SSID: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - start > 10000) {
            Serial.println("[MQTT] WiFi connect timeout.");
            return false;
        }
        delay(250);
        Serial.print(".");
    }
    Serial.printf("\n[MQTT] WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());

    // Initialize NTP for ISO 8601 timestamp generation
    // Uses pool.ntp.org; device must have internet access
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    Serial.println("[MQTT] NTP initialized.");
    return true;
}

/**
 * broker_connect() — Connect to MQTT broker using 256dpi/arduino-mqtt API.
 * Returns true on successful MQTT connection.
 */
static bool broker_connect() {
    Serial.printf("[MQTT] Connecting to broker %s:%d as %s\n",
                  MQTT_BROKER_HOST, MQTT_BROKER_PORT, DEVICE_SERIAL);

    bool connected;
    if (strlen(MQTT_USERNAME) > 0) {
        connected = mqttClient.connect(DEVICE_SERIAL, MQTT_USERNAME, MQTT_PASSWORD);
    } else {
        connected = mqttClient.connect(DEVICE_SERIAL);
    }

    if (connected) {
        Serial.println("[MQTT] Broker connected.");
    } else {
        Serial.printf("[MQTT] Broker connect failed (rc=%d).\n", mqttClient.lastError());
    }
    return connected;
}

/**
 * format_iso8601() — Format current NTP time as ISO 8601 UTC string.
 * Output: "2026-02-18T10:30:00.123Z" (milliseconds from millis() % 1000)
 * Uses getLocalTime() with 0ms timeout (non-blocking).
 */
static void format_iso8601(char* buf, size_t buf_size) {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo, 0)) {
        // NTP not synced yet — use a fallback with millis()
        snprintf(buf, buf_size, "1970-01-01T00:%02lu:%02lu.%03luZ",
                 (millis() / 60000UL) % 60,
                 (millis() / 1000UL)  % 60,
                 millis() % 1000UL);
        return;
    }
    uint32_t ms = millis() % 1000;
    snprintf(buf, buf_size, "%04d-%02d-%02dT%02d:%02d:%02d.%03luZ",
             timeinfo.tm_year + 1900,
             timeinfo.tm_mon  + 1,
             timeinfo.tm_mday,
             timeinfo.tm_hour,
             timeinfo.tm_min,
             timeinfo.tm_sec,
             (unsigned long)ms);
}

// ─── Connection FSM (US2: non-blocking reconnect) ─────────────────────────────

typedef enum {
    CONN_WIFI_DOWN,       // WiFi not connected; waiting to retry
    CONN_WIFI_CONNECTING, // WiFi.begin() called; polling for WL_CONNECTED
    CONN_MQTT_DOWN,       // WiFi up, MQTT not connected; waiting to retry
    CONN_READY            // WiFi + MQTT connected; streaming active
} ConnState;

static ConnState  conn_state        = CONN_READY;  // assume success at startup
static uint32_t   lastWifiAttemptMs  = 0;
static uint32_t   lastMqttAttemptMs  = 0;

static const uint32_t WIFI_RETRY_MS          = 10000; // 10s between WiFi retry attempts
static const uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000; // 15s max to achieve WL_CONNECTED
static const uint32_t MQTT_RETRY_MS          = 5000;  // 5s between MQTT retry attempts

// ─── Public API ───────────────────────────────────────────────────────────────

bool mqtt_connect() {
    // Build MQTT topic string once
    snprintf(mqtt_topic, sizeof(mqtt_topic), "tremo/sensors/%s", DEVICE_SERIAL);
    Serial.printf("[MQTT] Publishing to topic: %s\n", mqtt_topic);

    if (!wifi_connect()) return false;

    // Configure MQTT client once: set broker host, port, and underlying TCP client
    mqttClient.begin(MQTT_BROKER_HOST, MQTT_BROKER_PORT, wifiClient);

    return broker_connect();
}

void mqtt_loop() {
    /**
     * Non-blocking 4-state connection FSM.
     *
     * States and transitions:
     *   CONN_WIFI_DOWN       Retries WiFi.begin() every WIFI_RETRY_MS (10s).
     *                        → CONN_WIFI_CONNECTING once WiFi.begin() is called.
     *
     *   CONN_WIFI_CONNECTING Polls WiFi.status() each call.
     *                        → CONN_MQTT_DOWN when WL_CONNECTED (also re-inits NTP).
     *                        → CONN_WIFI_DOWN if WIFI_CONNECT_TIMEOUT_MS (15s) elapses.
     *
     *   CONN_MQTT_DOWN       Retries broker_connect() every MQTT_RETRY_MS (5s).
     *                        Falls back to CONN_WIFI_DOWN if WiFi drops mid-wait.
     *                        → CONN_READY on successful connect().
     *
     *   CONN_READY           Both WiFi and MQTT connected.
     *                        Calls mqttClient.loop() for keepalive and PUBACK processing.
     *                        → CONN_WIFI_DOWN if WiFi drops.
     *                        → CONN_MQTT_DOWN if only MQTT drops.
     */
    uint32_t now = millis();

    switch (conn_state) {

        case CONN_WIFI_DOWN:
            if ((now - lastWifiAttemptMs) >= WIFI_RETRY_MS) {
                lastWifiAttemptMs = now;
                Serial.println("[MQTT] WiFi down — retrying WiFi.begin()...");
                WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
                conn_state = CONN_WIFI_CONNECTING;
            }
            break;

        case CONN_WIFI_CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                Serial.printf("[MQTT] WiFi reconnected. IP: %s\n",
                              WiFi.localIP().toString().c_str());
                configTime(0, 0, "pool.ntp.org");
                conn_state        = CONN_MQTT_DOWN;
                lastMqttAttemptMs = 0;  // attempt MQTT immediately
            } else if ((now - lastWifiAttemptMs) >= WIFI_CONNECT_TIMEOUT_MS) {
                Serial.println("[MQTT] WiFi connect timeout — will retry.");
                WiFi.disconnect();
                conn_state        = CONN_WIFI_DOWN;
                lastWifiAttemptMs = now;
            }
            break;

        case CONN_MQTT_DOWN:
            if (WiFi.status() != WL_CONNECTED) {
                conn_state        = CONN_WIFI_DOWN;
                lastWifiAttemptMs = 0;
                break;
            }
            if ((now - lastMqttAttemptMs) >= MQTT_RETRY_MS) {
                lastMqttAttemptMs = now;
                Serial.println("[MQTT] MQTT down — attempting broker reconnect...");
                if (broker_connect()) {
                    conn_state = CONN_READY;
                }
            }
            break;

        case CONN_READY:
            if (WiFi.status() != WL_CONNECTED) {
                Serial.println("[MQTT] WiFi lost — transitioning to CONN_WIFI_DOWN.");
                conn_state        = CONN_WIFI_DOWN;
                lastWifiAttemptMs = 0;
                break;
            }
            if (!mqttClient.connected()) {
                Serial.println("[MQTT] MQTT connection lost — transitioning to CONN_MQTT_DOWN.");
                conn_state        = CONN_MQTT_DOWN;
                lastMqttAttemptMs = 0;
                break;
            }
            // Both connected — process keepalive and incoming PUBACK packets
            mqttClient.loop();
            break;
    }
}

bool publish_reading(FusedReading* reading) {
    if (!reading) return false;

    // Populate ISO 8601 timestamp into the FusedReading struct
    format_iso8601(reading->timestamp_iso, sizeof(reading->timestamp_iso));

    // Build JSON payload using ArduinoJson 6.x
    // StaticJsonDocument<256> uses stack memory — safe for 33Hz publish loop
    StaticJsonDocument<256> doc;
    doc["device_id"]  = DEVICE_SERIAL;
    doc["timestamp"]  = reading->timestamp_iso;
    // Round to 4 decimal places before serialization
    doc["aX"] = roundf(reading->aX * 10000.0f) / 10000.0f;
    doc["aY"] = roundf(reading->aY * 10000.0f) / 10000.0f;
    doc["aZ"] = roundf(reading->aZ * 10000.0f) / 10000.0f;
    doc["gX"] = roundf(reading->gX * 10000.0f) / 10000.0f;
    doc["gY"] = roundf(reading->gY * 10000.0f) / 10000.0f;
    doc["gZ"] = roundf(reading->gZ * 10000.0f) / 10000.0f;
    doc["battery_level"] = roundf(reading->battery_level * 10.0f) / 10.0f;

    // Serialize to char buffer
    char payload[256];
    size_t len = serializeJson(doc, payload, sizeof(payload));
    if (len == 0) {
        Serial.println("[MQTT] JSON serialization failed.");
        return false;
    }

    // Publish QoS 1 (at-least-once delivery) — broker sends PUBACK for each message
    bool ok = mqttClient.publish(mqtt_topic, payload, false, 1);

#ifdef FIRMWARE_DEBUG
    if (!ok) {
        Serial.printf("[MQTT] Publish failed (rc=%d)\n", mqttClient.lastError());
    }
#endif

    return ok;
}
