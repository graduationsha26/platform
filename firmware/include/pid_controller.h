/**
 * pid_controller.h — PID Controller for Tremor Suppression
 *
 * Feature: 031-freertos-scheduler
 *
 * Single PID instance suppresses Parkinsonian tremor (4–8Hz oscillation) on
 * TARGET_TREMOR_AXIS (see config.h): pitch-rate feedback (FusedReading.gY, deg/s).
 *
 * Feedback signal: gyroscope angular velocity (deg/s), NOT Kalman-filtered angle.
 * Gyro directly measures tremor oscillation rate without Kalman filter lag.
 * Setpoint: 0.0 deg/s — any angular velocity represents tremor to suppress.
 *
 * Matches the bench-validated control loop from run_zizo/src/main.cpp exactly:
 * raw finite-difference derivative (no filter), fixed integral clamp
 * (PID_INTEGRAL_CLAMP), unclamped output (normalization happens in
 * cmg_set_gimbal()).
 */

#pragma once

/**
 * PidController — State and configuration for the tremor-suppression PID axis.
 *
 * Initialize with pid_init(). Update with pid_update() at each control cycle.
 * Do not modify fields directly between calls.
 */
typedef struct {
    float Kp;         // Proportional gain (see PID_KP in config.h)
    float Ki;         // Integral gain (see PID_KI in config.h)
    float Kd;         // Derivative gain (see PID_KD in config.h)
    float dt;         // Fixed control period in seconds (CONTROL_LOOP_DT_S)
    float setpoint;   // Target angular velocity in deg/s (default: 0.0 — suppress all rotation)
    float integral;   // Accumulated integral term, clamped to ±PID_INTEGRAL_CLAMP
    float prev_error; // Error at previous pid_update() call (for derivative)
} PidController;

/**
 * pid_init() — Initialize a PidController instance.
 *
 * Zeros all state fields (integral, prev_error) and sets setpoint to 0.0 deg/s.
 *
 * @param pid  Controller instance to initialize
 * @param Kp   Proportional gain (see PID_KP in config.h)
 * @param Ki   Integral gain (see PID_KI in config.h)
 * @param Kd   Derivative gain (see PID_KD in config.h)
 * @param dt   Fixed control period in seconds (see CONTROL_LOOP_DT_S in config.h)
 */
void pid_init(PidController* pid, float Kp, float Ki, float Kd, float dt);

/**
 * pid_update() — Run one PID control cycle and return the raw output.
 *
 * Computes: output = Kp×error + Ki×integral + Kd×derivative
 * Output is NOT clamped here — cmg_set_gimbal() normalizes it (÷CMG_TORQUE_FULL_SCALE)
 * and applies slew limiting before driving the gimbal servo.
 *
 * @param pid          Controller instance (from pid_init)
 * @param measurement  Current gyro angular velocity in deg/s (TARGET_TREMOR_AXIS)
 * Returns: raw PID output (unclamped)
 */
float pid_update(PidController* pid, float measurement);
