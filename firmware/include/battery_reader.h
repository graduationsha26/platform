/**
 * battery_reader.h — Battery Level ADC Reader
 *
 * Feature: 030-esp32-mqtt
 *
 * Reads battery voltage via a resistive voltage divider on BATTERY_ADC_PIN
 * (GPIO34 by default — ADC1 channel 6). ADC2 pins are unreliable when WiFi
 * is active; BATTERY_ADC_PIN must always be on ADC1 (GPIO32–39).
 *
 * Usage:
 *   1. Call battery_init() once in setup() after IMU calibration.
 *   2. Call read_battery() each publish cycle to get the current level (0–100 %).
 */

#pragma once

#include <stdint.h>

// ─── BatteryReading ────────────────────────────────────────────────────────────

/**
 * BatteryReading — One ADC sample from the battery monitoring circuit.
 *
 *   adc_mv:     Raw ADC reading in millivolts via analogReadMilliVolts()
 *               (factory-calibrated, corrects ESP32 ADC non-linearity).
 *   voltage_v:  Computed: (adc_mv / 1000.0f) / BATTERY_DIVIDER_RATIO
 *   percentage: Linear map of voltage_v over LiPo range [BATTERY_V_MIN, BATTERY_V_MAX]
 *               clamped to [0.0, 100.0].
 */
typedef struct {
    uint32_t adc_mv;      // ADC reading in millivolts
    float    voltage_v;   // Battery voltage after divider compensation
    float    percentage;  // State of charge: 0.0–100.0 %
} BatteryReading;

// ─── API ──────────────────────────────────────────────────────────────────────

/**
 * battery_init() — Configure the ADC pin for battery monitoring.
 *
 * Calls analogSetAttenuation(ADC_11db) on BATTERY_ADC_PIN to configure the
 * full 0–3.3V input range. The default ESP32 ADC range (0–1.1V) is insufficient
 * for battery monitoring through a voltage divider at typical LiPo voltages.
 *
 * Call once in setup() after IMU calibration and before mqtt_connect().
 */
void battery_init();

/**
 * read_battery() — Sample the battery ADC and return state of charge.
 *
 * Averages 16 analogReadMilliVolts() readings on BATTERY_ADC_PIN to reduce
 * noise, then maps the measured voltage to a percentage over the LiPo range:
 *   percentage = (voltage_v - BATTERY_V_MIN) / (BATTERY_V_MAX - BATTERY_V_MIN) * 100.0f
 * Result is clamped to [0.0, 100.0].
 *
 * Returns: Battery level as a float in the range [0.0, 100.0].
 */
float read_battery();
