/**
 * pid_controller.cpp — PID Controller Implementation for Tremor Suppression
 *
 * Feature: 031-freertos-scheduler
 *
 * Bench-validated control loop (ported from run_zizo/src/main.cpp):
 *
 *   error     = setpoint - measurement       (setpoint = 0.0 deg/s)
 *   integral  = constrain(integral + error*dt, -PID_INTEGRAL_CLAMP, +PID_INTEGRAL_CLAMP)
 *   derivative = (error - prev_error) / dt
 *   output    = Kp*error + Ki*integral + Kd*derivative
 *
 * No pre-filter, no deadband, no derivative IIR filter, no conditional anti-windup.
 */

#include "pid_controller.h"
#include "config.h"
#include <Arduino.h>
#include <string.h>

void pid_init(PidController* pid, float Kp, float Ki, float Kd, float dt) {
    memset(pid, 0, sizeof(*pid));
    pid->Kp = Kp;
    pid->Ki = Ki;
    pid->Kd = Kd;
    pid->dt = dt;
    pid->setpoint = 0.0f;
    // integral, prev_error are zeroed by memset
}

float pid_update(PidController* pid, float measurement) {
    float error = pid->setpoint - measurement;

    pid->integral = constrain(pid->integral + error * pid->dt,
                               -PID_INTEGRAL_CLAMP, PID_INTEGRAL_CLAMP);

    float derivative = (error - pid->prev_error) / pid->dt;

    float output = pid->Kp * error + pid->Ki * pid->integral + pid->Kd * derivative;

    pid->prev_error = error;

    return output;
}
