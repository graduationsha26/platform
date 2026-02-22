/**
 * kalman.cpp — Lauszus 2-State Kalman Filter Implementation
 *
 * Feature: 025-imu-kalman-fusion
 *
 * Implements:
 *   T016: accel_roll(), accel_pitch() — accelerometer angle derivation
 *   T017: kalman_init()               — filter initialization
 *   T018: kalman_update()             — predict + update cycle with adaptive R_measure
 *
 * Algorithm: Lauszus 2-state linear Kalman filter.
 * Reference: https://blog.tkjelectronics.dk/2012/09/a-practical-approach-to-kalman-filter-and-how-to-implement-it/
 *
 * State per axis: x = [angle, bias]
 *   angle: filtered orientation estimate (degrees)
 *   bias:  estimated gyroscope bias (deg/s)
 *
 * Two independent instances: one for roll, one for pitch.
 * No quaternion math. No yaw (no magnetometer reference).
 */

#include "kalman.h"
#include "config.h"
#include "imu.h"
#include <math.h>
#include <Arduino.h>

// ─── T016: Accelerometer Angle Derivation ────────────────────────────────────

/**
 * accel_roll() — Roll from atan2(aY, aZ).
 *
 * Range: (-180, +180] degrees. No singularity.
 * When glove is flat (Z-axis up, X-axis forward), roll ≈ 0°.
 */
float accel_roll(float aY, float aZ) {
    return atan2f(aY, aZ) * (180.0f / M_PI);
}

/**
 * accel_pitch() — Pitch from atan2(-aX, sqrt(aY² + aZ²)).
 *
 * Range: (-90, +90] degrees. Singularity at ±90° (gimbal lock).
 * Safe for wrist tremor monitoring where pitch stays within ±70°.
 * When glove is flat, pitch ≈ 0°.
 */
float accel_pitch(float aX, float aY, float aZ) {
    return atan2f(-aX, sqrtf(aY * aY + aZ * aZ)) * (180.0f / M_PI);
}

// ─── T017: kalman_init() ─────────────────────────────────────────────────────

/**
 * kalman_init() — Initialize filter state.
 *
 * Pre-seeding bias from the calibration gyro mean dramatically speeds up
 * filter convergence — the bias estimate starts near the true value
 * rather than at zero.
 *
 * Error covariance P is initialized to zero (the standard starting
 * condition for a Kalman filter with known initial state).
 */
void kalman_init(KalmanFilter* kf, float initial_bias) {
    if (!kf) return;

    kf->angle     = 0.0f;
    kf->bias      = initial_bias;   // Pre-seeded from startup calibration
    kf->P[0][0]   = 0.0f;
    kf->P[0][1]   = 0.0f;
    kf->P[1][0]   = 0.0f;
    kf->P[1][1]   = 0.0f;
    kf->Q_angle   = KF_Q_ANGLE;
    kf->Q_bias    = KF_Q_BIAS;
    kf->R_measure = KF_R_MEASURE;

#ifdef FIRMWARE_DEBUG
    Serial.printf("[KF] Init: bias=%.4f Q_angle=%.4f Q_bias=%.4f R=%.4f\n",
                  initial_bias, KF_Q_ANGLE, KF_Q_BIAS, KF_R_MEASURE);
#endif
}

// ─── T018: kalman_update() ───────────────────────────────────────────────────

/**
 * kalman_update() — Run one predict + update cycle.
 *
 * Adaptive R_measure:
 *   If the accelerometer magnitude deviates from 1g by more than
 *   KF_ACCEL_DYNAMIC_THRESHOLD_MS2, the device is experiencing linear
 *   acceleration (e.g., active tremor). In this case, the accelerometer-
 *   derived angle is less reliable, so R_measure is increased to reduce
 *   the accelerometer's influence on the angle estimate.
 *
 * Returns the updated filtered angle.
 */
float kalman_update(KalmanFilter* kf,
                    float         accel_angle,
                    float         gyro_rate,
                    float         dt,
                    float         aX,
                    float         aY,
                    float         aZ) {
    if (!kf) return 0.0f;

    // ── Adaptive R_measure ──────────────────────────────────────────────────
    // Detect dynamic acceleration: if ‖a‖ ≠ 1g, trust accel angle less.
    float accel_mag = sqrtf(aX * aX + aY * aY + aZ * aZ);
    float R = (fabsf(accel_mag - GRAVITY_MS2) > KF_ACCEL_DYNAMIC_THRESHOLD_MS2)
              ? KF_R_MEASURE_DYNAMIC
              : kf->R_measure;

    // ── Predict Step (Gyroscope Integration) ───────────────────────────────
    // Remove estimated bias from raw gyro rate
    float rate = gyro_rate - kf->bias;

    // Integrate corrected rate to update angle estimate
    kf->angle += dt * rate;

    // Propagate error covariance: P_new = F * P * F^T + Q
    // F = [[1, -dt], [0, 1]]
    // Expanded closed-form for 2x2 case (uses temporaries to avoid overwrites):
    float P00 = kf->P[0][0];
    float P01 = kf->P[0][1];
    float P10 = kf->P[1][0];
    float P11 = kf->P[1][1];

    kf->P[0][0] = P00 + dt * (dt * P11 - P01 - P10 + kf->Q_angle);
    kf->P[0][1] = P01 - dt * P11;
    kf->P[1][0] = P10 - dt * P11;
    kf->P[1][1] = P11 + kf->Q_bias * dt;

    // ── Update Step (Accelerometer Correction) ─────────────────────────────
    // Innovation: difference between accelerometer-derived angle and prediction
    float y = accel_angle - kf->angle;

    // Innovation covariance (scalar since H = [1, 0])
    // S = H * P * H^T + R = P[0][0] + R
    float S = kf->P[0][0] + R;

    // Kalman gain (2-element vector)
    // K = P * H^T * S^-1 = [P[0][0]/S, P[1][0]/S]
    float K0 = kf->P[0][0] / S;
    float K1 = kf->P[1][0] / S;

    // State update
    kf->angle += K0 * y;
    kf->bias  += K1 * y;

    // Covariance update: P_new = (I - K*H) * P
    // Use temporaries to avoid reading overwritten values
    float P00_new = kf->P[0][0];
    float P01_new = kf->P[0][1];
    kf->P[0][0] -= K0 * P00_new;
    kf->P[0][1] -= K0 * P01_new;
    kf->P[1][0] -= K1 * P00_new;
    kf->P[1][1] -= K1 * P01_new;

#ifdef FIRMWARE_DEBUG
    static bool bias_converged = false;
    if (!bias_converged && fabsf(kf->bias) < 0.1f) {
        Serial.printf("[KF] Bias converged: bias=%.4f deg/s\n", kf->bias);
        bias_converged = true;
    }
#endif

    return kf->angle;
}
