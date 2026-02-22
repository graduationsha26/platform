/**
 * pid_controller.cpp — PID Controller Implementation for Tremor Suppression
 *
 * Feature: 031-freertos-scheduler
 *
 * PID algorithm with IIR derivative filter and conditional anti-windup:
 *
 *   error      = setpoint - measurement           (setpoint = 0.0 deg/s)
 *   d_raw      = (error - prev_error) / dt
 *   alpha      = dt / (tau + dt)                  (at tau=0.008, dt=0.005: alpha≈0.385)
 *   d_filt     = alpha × d_raw + (1−alpha) × prev_deriv_filt
 *   output     = Kp×error + integral + Kd×d_filt
 *
 *   Anti-windup: if output saturates → clamp output, do NOT update integral.
 *                if output within bounds → accept integral update.
 */

#include "pid_controller.h"
#include <string.h>

void pid_init(PidController* pid,
              float Kp, float Ki, float Kd,
              float tau, float dt,
              float out_min, float out_max) {
    memset(pid, 0, sizeof(*pid));
    pid->Kp      = Kp;
    pid->Ki      = Ki;
    pid->Kd      = Kd;
    pid->tau     = tau;
    pid->dt      = dt;
    pid->out_min = out_min;
    pid->out_max = out_max;
    pid->setpoint = 0.0f;
    // integral, prev_error, prev_deriv_filt are zeroed by memset
}

float pid_update(PidController* pid, float measurement) {
    float error = pid->setpoint - measurement;

    // Derivative: finite difference → IIR low-pass filter (fc ≈ 20Hz at tau=0.008s)
    float d_raw  = (error - pid->prev_error) / pid->dt;
    float alpha  = pid->dt / (pid->tau + pid->dt);
    float d_filt = alpha * d_raw + (1.0f - alpha) * pid->prev_deriv_filt;

    // Tentative integral update (accepted only if output stays within bounds)
    float integral_new = pid->integral + pid->Ki * error * pid->dt;

    // Compute unsaturated output
    float output = pid->Kp * error + integral_new + pid->Kd * d_filt;

    // Conditional anti-windup: clamp output; hold integral when saturated
    if (output > pid->out_max) {
        output = pid->out_max;
        // Do NOT update pid->integral — hold last valid accumulated value
    } else if (output < pid->out_min) {
        output = pid->out_min;
        // Do NOT update pid->integral — hold last valid accumulated value
    } else {
        // Output within bounds: accept the integral update
        pid->integral = integral_new;
    }

    // Update filter state for next call
    pid->prev_error      = error;
    pid->prev_deriv_filt = d_filt;

    return output;
}
