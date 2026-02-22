/**
 * cmg.cpp — Control Moment Gyroscope (CMG) Actuation Implementation
 *
 * Feature: 031-freertos-scheduler
 *
 * Two LEDC PWM channels at 50Hz, 16-bit resolution:
 *   Channel CMG_GIMBAL_CHANNEL  (GPIO CMG_GIMBAL_PIN):  Gimbal servo (PID-driven)
 *   Channel CMG_FLYWHEEL_CHANNEL (GPIO CMG_FLYWHEEL_PIN): Flywheel ESC (constant speed)
 *
 * Duty formula (16-bit, 50Hz → 20ms period):
 *   duty = (pulse_us × 65536) / 20000
 *
 * Pulse-to-duty reference:
 *   1500 µs (center, 0°)  → duty = 4915
 *   2167 µs (+60°)        → duty = 7104
 *    833 µs (-60°)        → duty = 2730
 *   1000 µs (ESC arm)     → duty = 3277
 */

#include "cmg.h"
#include "config.h"
#include <Arduino.h>

void cmg_init() {
    // ESP32 Arduino 3.x pin-based LEDC API:
    //   ledcAttach(pin, freq, resolution) — replaces ledcSetup + ledcAttachPin
    //   ledcWrite(pin, duty)              — replaces ledcWrite(channel, duty)

    // --- Gimbal servo (GPIO CMG_GIMBAL_PIN) ---
    ledcAttach(CMG_GIMBAL_PIN, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION);
    // Center gimbal at 1500µs: duty = (1500 × 65536) / 20000 = 4915
    ledcWrite(CMG_GIMBAL_PIN, (1500UL * 65536UL) / 20000UL);

    // --- Flywheel ESC (GPIO CMG_FLYWHEEL_PIN) ---
    ledcAttach(CMG_FLYWHEEL_PIN, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION);

    // Arm ESC: hold minimum throttle (1000µs) for 2 seconds — required by ESC firmware
    // duty = (1000 × 65536) / 20000 = 3277
    ledcWrite(CMG_FLYWHEEL_PIN, (1000UL * 65536UL) / 20000UL);
    delay(2000);  // ESC arming sequence — normal behavior; do not remove

    // Ramp to constant operating throttle
    ledcWrite(CMG_FLYWHEEL_PIN, CMG_FLYWHEEL_DUTY);

    Serial.printf("[CMG] Initialized. Gimbal GPIO%d, Flywheel GPIO%d, 50Hz 16-bit.\n",
                  CMG_GIMBAL_PIN, CMG_FLYWHEEL_PIN);
}

void cmg_set_gimbal(float output_normalized) {
    // Clamp to [-1.0, +1.0] before angle conversion
    if (output_normalized > 1.0f)  output_normalized = 1.0f;
    if (output_normalized < -1.0f) output_normalized = -1.0f;

    // Map normalized output to gimbal angle: [-1.0, +1.0] -> [+-CMG_GIMBAL_MAX_DEG]
    float angle_deg = output_normalized * CMG_GIMBAL_MAX_DEG;

    // Map angle to pulse width:
    //   center = 1500us, full range = +-1000us across +-CMG_GIMBAL_MAX_DEG
    uint32_t pulse_us = (uint32_t)(1500.0f + angle_deg * (1000.0f / CMG_GIMBAL_MAX_DEG));

    // Clamp to servo-safe range (standard RC hobby range at +-60 deg)
    if (pulse_us > 2167) pulse_us = 2167;
    if (pulse_us < 833)  pulse_us = 833;

    // Compute 16-bit LEDC duty and apply (pin-based API)
    uint32_t duty = (pulse_us * 65536UL) / 20000UL;
    ledcWrite(CMG_GIMBAL_PIN, duty);
}
