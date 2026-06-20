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
 * Ported from the bench-validated run_zizo/src/main.cpp control loop: simple
 * constant-throttle ESC arm (no retry/verification), and a normalize →
 * slew-limit → microseconds gimbal pipeline.
 */

#include "cmg.h"
#include "config.h"
#include <Arduino.h>
#include <math.h>

static uint32_t microsToDuty(float us) {
    return (uint32_t)lroundf(us / 20000.0f * 65536.0f);
}

static float torqueToMicros(float torque) {
    torque = constrain(torque, -1.0f, 1.0f);
    float us = CMG_GIMBAL_CENTER_US + CMG_GIMBAL_TRIM_US + torque * CMG_GIMBAL_SPAN_US;
    return constrain(us, (float)CMG_GIMBAL_MIN_US, (float)CMG_GIMBAL_MAX_US);
}

void cmg_init() {
    // ESP32 Arduino 2.x channel-based LEDC API
    // --- Gimbal servo (GPIO CMG_GIMBAL_PIN, channel CMG_GIMBAL_CHANNEL) ---
    ledcSetup(CMG_GIMBAL_CHANNEL, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION);
    ledcAttachPin(CMG_GIMBAL_PIN, CMG_GIMBAL_CHANNEL);
    ledcWrite(CMG_GIMBAL_CHANNEL, microsToDuty(torqueToMicros(0.0f)));

    // --- Flywheel ESC ---
    ledcSetup(CMG_FLYWHEEL_CHANNEL, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION);
    ledcAttachPin(CMG_FLYWHEEL_PIN, CMG_FLYWHEEL_CHANNEL);

    // Arm: hold CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS, then jump to a constant
    // run throttle. No retry, no spin-up verification.
    ledcWrite(CMG_FLYWHEEL_CHANNEL, microsToDuty(CMG_ESC_ARM_PULSE_US));
    delay(CMG_ESC_ARM_MS);
    ledcWrite(CMG_FLYWHEEL_CHANNEL, microsToDuty(CMG_ESC_RUN_PULSE_US));

    Serial.printf("[CMG] Flywheel armed (%dus) and running (%dus). Gimbal (ch%d), Flywheel (ch%d)\n",
                  CMG_ESC_ARM_PULSE_US, CMG_ESC_RUN_PULSE_US,
                  CMG_GIMBAL_CHANNEL, CMG_FLYWHEEL_CHANNEL);
}

void cmg_set_gimbal(float pid_output) {
    float torqueCmd = constrain(-pid_output / CMG_TORQUE_FULL_SCALE, -1.0f, 1.0f);

    static float currentTorque = 0.0f;
    float maxStep = CMG_TORQUE_SLEW_PER_S * CONTROL_LOOP_DT_S;
    currentTorque += constrain(torqueCmd - currentTorque, -maxStep, maxStep);

    ledcWrite(CMG_GIMBAL_CHANNEL, microsToDuty(torqueToMicros(currentTorque)));
}
