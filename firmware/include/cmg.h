/**
 * cmg.h — Control Moment Gyroscope (CMG) Actuation Interface
 *
 * Feature: 031-freertos-scheduler
 *
 * Controls two LEDC PWM channels at 50Hz (16-bit resolution):
 *   Channel CMG_GIMBAL_CHANNEL  (GPIO CMG_GIMBAL_PIN):
 *     Gimbal servo — angle driven by PID output every 5ms (200Hz).
 *     Pulse range: 833–2167 µs (±CMG_GIMBAL_MAX_DEG = ±60°)
 *     Center (0°): 1500 µs → duty = (1500 × 65536) / 20000 = 4915
 *
 *   Channel CMG_FLYWHEEL_CHANNEL (GPIO CMG_FLYWHEEL_PIN):
 *     Flywheel ESC — constant throttle set once at startup.
 *     Arms at 1000 µs (duty 3277) for 2 s, then ramps to CMG_FLYWHEEL_DUTY.
 *
 * Duty formula (16-bit, 50Hz → 20ms period):
 *   duty = (pulse_us × 65536) / 20000
 *
 * Note: ledcWrite() is safe on ADC2 pins (only analogRead() conflicts with WiFi).
 */

#pragma once

/**
 * cmg_init() — Initialize LEDC channels for gimbal servo and flywheel ESC.
 *
 * - Configures LEDC channel CMG_GIMBAL_CHANNEL on GPIO CMG_GIMBAL_PIN at
 *   CMG_PWM_FREQ_HZ Hz with CMG_PWM_RESOLUTION-bit resolution.
 * - Centers gimbal servo at 1500 µs pulse.
 * - Configures LEDC channel CMG_FLYWHEEL_CHANNEL on GPIO CMG_FLYWHEEL_PIN.
 * - Arms flywheel ESC: holds 1000 µs for 2 seconds (normal ESC behavior),
 *   then ramps to CMG_FLYWHEEL_DUTY (constant throttle).
 *
 * Call once in setup() before scheduler_start().
 * The 2-second arming delay is expected — do not skip it.
 */
void cmg_init();

/**
 * cmg_set_gimbal() — Set gimbal servo position from normalized PID output.
 *
 * @param output_normalized  PID output in range [-1.0, +1.0]
 *   Clamped to [-1.0, +1.0] before conversion.
 *   Maps to gimbal angle [±CMG_GIMBAL_MAX_DEG degrees].
 *   Maps to servo pulse [833–2167 µs] → 16-bit LEDC duty.
 *
 * Called from ControlTask at 200Hz. LEDC hardware holds last duty between calls.
 * Safe to call faster than the 50Hz servo period (hardware latches duty at next period).
 */
void cmg_set_gimbal(float output_normalized);
