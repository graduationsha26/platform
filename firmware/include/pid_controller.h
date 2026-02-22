/**
 * pid_controller.h — PID Controller for Tremor Suppression
 *
 * Feature: 031-freertos-scheduler
 *
 * Two independent PID instances suppress Parkinsonian tremor (4–8Hz oscillation):
 *   Instance 1: roll-rate  feedback (FusedReading.gX, deg/s)
 *   Instance 2: pitch-rate feedback (FusedReading.gY, deg/s)
 *
 * Feedback signal: gyroscope angular velocity (deg/s), NOT Kalman-filtered angle.
 * Gyro directly measures tremor oscillation rate without Kalman filter lag.
 * Setpoint: 0.0 deg/s — any angular velocity represents tremor to suppress.
 *
 * Derivative IIR filter (fc ≈ 20Hz, tau = PID_TAU = 0.008s):
 *   alpha  = dt / (tau + dt)   →  at dt=0.005, tau=0.008: alpha ≈ 0.385
 *   d_filt = alpha × d_raw + (1 − alpha) × prev_d_filt
 *   Passes tremor-band dynamics (4–8Hz), strongly rejects gyro noise (>30Hz).
 *
 * Anti-windup: Conditional clamping.
 *   When output saturates (hits out_min or out_max): do NOT update integral.
 *   Resume integral accumulation only when output returns within bounds.
 */

#pragma once

/**
 * PidController — State and configuration for one PID axis.
 *
 * Initialize with pid_init(). Update with pid_update() at each control cycle.
 * Do not modify fields directly between calls.
 *
 * Two instances required: one for roll-rate (gX), one for pitch-rate (gY).
 */
typedef struct {
    float Kp;              // Proportional gain (e.g. 1.0f — start conservative)
    float Ki;              // Integral gain (e.g. 0.01f — very small for tremor rejection)
    float Kd;              // Derivative gain (e.g. 0.03f — primary damping term)
    float tau;             // Derivative LPF time constant in seconds (e.g. 0.008f → fc≈20Hz)
    float dt;              // Fixed control period in seconds (0.005f for 200Hz)
    float setpoint;        // Target angular velocity in deg/s (default: 0.0 — suppress all rotation)
    float integral;        // Accumulated integral term; held when output saturated (anti-windup)
    float prev_error;      // Error at previous pid_update() call (for derivative)
    float prev_deriv_filt; // IIR state: filtered derivative from previous call
    float out_min;         // Output clamp lower bound (e.g. -1.0f → -60° gimbal)
    float out_max;         // Output clamp upper bound (e.g. +1.0f → +60° gimbal)
} PidController;

/**
 * pid_init() — Initialize a PidController instance.
 *
 * Zeros all state fields (integral, prev_error, prev_deriv_filt).
 * Sets setpoint to 0.0 deg/s (suppress all angular velocity).
 *
 * @param pid      Controller instance to initialize
 * @param Kp       Proportional gain (see PID_KP in config.h)
 * @param Ki       Integral gain (see PID_KI in config.h)
 * @param Kd       Derivative gain (see PID_KD in config.h)
 * @param tau      Derivative LPF time constant in seconds (see PID_TAU in config.h)
 * @param dt       Fixed control period in seconds (0.005f for 200Hz ControlTask)
 * @param out_min  Output lower clamp (see PID_OUTPUT_MIN in config.h)
 * @param out_max  Output upper clamp (see PID_OUTPUT_MAX in config.h)
 */
void pid_init(PidController* pid,
              float Kp, float Ki, float Kd,
              float tau, float dt,
              float out_min, float out_max);

/**
 * pid_update() — Run one PID control cycle and return clamped output.
 *
 * Computes: output = Kp×error + integral + Kd×d_filt
 *   where integral is only updated when output is within [out_min, out_max].
 *
 * @param pid          Controller instance (from pid_init)
 * @param measurement  Current gyro angular velocity in deg/s:
 *                     use gX for roll-rate instance, gY for pitch-rate instance
 * Returns: clamped output in [out_min, out_max]
 */
float pid_update(PidController* pid, float measurement);
