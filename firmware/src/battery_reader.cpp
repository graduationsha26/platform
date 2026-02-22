/**
 * battery_reader.cpp — Battery Level ADC Reader
 *
 * Feature: 030-esp32-mqtt
 *
 * Reads battery level from a resistive voltage divider connected to
 * BATTERY_ADC_PIN (GPIO34 by default — ADC1 channel 6, input-only).
 *
 * ADC pin MUST be on ADC1 (GPIO32–39). ADC2 pins (GPIO0/2/4/12–15/25–27)
 * are unreliable when WiFi is active.
 *
 * Voltage divider wiring (default values in config.h.example):
 *   Battery+ → R1 (100kΩ) → BATTERY_ADC_PIN → R2 (47kΩ) → GND
 *   Divider ratio = 47 / (100 + 47) ≈ 0.3197
 *   At 4.2V (full): ADC pin sees ≈ 1.34V
 *   At 3.0V (empty): ADC pin sees ≈ 0.96V
 */

#include "battery_reader.h"
#include "config.h"
#include <Arduino.h>

// ─── battery_init ─────────────────────────────────────────────────────────────

void battery_init() {
    // Configure attenuation for BATTERY_ADC_PIN to cover the full 0–3.3V input
    // range. The default ESP32 ADC range (0–1.1V) is insufficient for battery
    // monitoring through the voltage divider at typical LiPo voltages.
    analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);
}

// ─── read_battery ─────────────────────────────────────────────────────────────

float read_battery() {
    // Average 16 samples to reduce ADC noise
    uint32_t sum = 0;
    for (int i = 0; i < 16; i++) {
        sum += analogReadMilliVolts(BATTERY_ADC_PIN);
    }
    uint32_t avg_mv = sum / 16;

    // Compensate for voltage divider to recover the actual battery voltage
    float voltage_v = (avg_mv / 1000.0f) / BATTERY_DIVIDER_RATIO;

    // Map battery voltage linearly onto 0–100 % over the LiPo operating range
    float percentage = (voltage_v - BATTERY_V_MIN) / (BATTERY_V_MAX - BATTERY_V_MIN) * 100.0f;

    // Clamp to valid percentage range
    return constrain(percentage, 0.0f, 100.0f);
}
