/**
 * cmg.h — Control Moment Gyroscope (CMG) Actuation Interface
 *
 * Feature: 031-freertos-scheduler
 *
 * Two LEDC PWM channels at 50Hz (16-bit resolution):
 *   Channel CMG_GIMBAL_CHANNEL  (GPIO CMG_GIMBAL_PIN):
 *     Gimbal servo — pulse width driven by the raw PID output every 5ms (200Hz),
 *     normalized, slew-limited, then mapped directly to microseconds (see
 *     cmg_set_gimbal()). Pulse range: CMG_GIMBAL_MIN_US–CMG_GIMBAL_MAX_US,
 *     centered on CMG_GIMBAL_CENTER_US.
 *
 *   Channel CMG_FLYWHEEL_CHANNEL (GPIO CMG_FLYWHEEL_PIN):
 *     Flywheel ESC — constant throttle set once at startup.
 *     Arms at CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS, then commands
 *     CMG_ESC_RUN_PULSE_US directly — no software ramp, no retry, no
 *     spin-up verification (matches the bench-validated run_zizo sequence).
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
 *   CMG_PWM_FREQ_HZ Hz with CMG_PWM_RESOLUTION-bit resolution, centered at
 *   CMG_GIMBAL_CENTER_US.
 * - Configures LEDC channel CMG_FLYWHEEL_CHANNEL on GPIO CMG_FLYWHEEL_PIN.
 * - Arms flywheel ESC: holds CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS (normal ESC
 *   behavior), then commands CMG_ESC_RUN_PULSE_US directly and holds it constant.
 *
 * Call once in setup() before scheduler_start().
 * The arming delay is expected — do not skip it.
 */
void cmg_init();

/**
 * cmg_set_gimbal() — Drive the gimbal servo from the raw PID output.
 *
 * @param pid_output  Raw (unclamped) PID output — NOT pre-normalized.
 *   Normalized internally: torque = constrain(-pid_output / CMG_TORQUE_FULL_SCALE, -1, 1).
 *   Slew-limited to CMG_TORQUE_SLEW_PER_S per second.
 *   Mapped directly to a servo pulse (CMG_GIMBAL_CENTER_US + CMG_GIMBAL_TRIM_US +
 *   torque × CMG_GIMBAL_SPAN_US), clamped to [CMG_GIMBAL_MIN_US, CMG_GIMBAL_MAX_US].
 *
 * Called from ControlTask at 200Hz. LEDC hardware holds last duty between calls.
 * Safe to call faster than the 50Hz servo period (hardware latches duty at next period).
 */
void cmg_set_gimbal(float pid_output);
