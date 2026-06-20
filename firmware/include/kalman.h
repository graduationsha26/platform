/**
 * kalman.h — Lauszus 2-State Kalman Filter for Roll and Pitch Estimation
 *
 * Feature: 025-imu-kalman-fusion
 *
 * Algorithm: Linear Kalman filter for a 2-element state vector [angle, gyro_bias].
 * Two independent instances are used — one for roll, one for pitch.
 * No quaternion math, no magnetometer, no yaw estimation.
 *
 * Reference: TKJ Electronics / Lauszus (2012)
 *   https://blog.tkjelectronics.dk/2012/09/a-practical-approach-to-kalman-filter-and-how-to-implement-it/
 *
 * State vector per axis:
 *   x = [ angle ]   Filtered angle estimate (degrees)
 *       [ bias  ]   Estimated gyroscope bias (deg/s)
 *
 * Predict step (gyroscope integration):
 *   angle += dt * (gyro_rate - bias)
 *   P updated per Lauszus formulation
 *
 * Update step (accelerometer-derived angle correction):
 *   innovation = accel_angle - angle
 *   Kalman gain computed from P and R_measure
 *   angle and bias corrected
 *
 * Adaptive R_measure:
 *   When |‖a‖ - 9.80665| > KF_ACCEL_DYNAMIC_THRESHOLD_MS2 (≈0.3g),
 *   R_measure is switched to KF_R_MEASURE_DYNAMIC to reduce
 *   accelerometer influence during active hand motion/tremor.
 */

#pragma once

#include <stdint.h>

// ─── Kalman Filter State ──────────────────────────────────────────────────────

/**
 * KalmanFilter — Internal state for one axis (roll or pitch).
 *
 * Initialize with kalman_init(). Update with kalman_update() at each sample.
 * Do not modify fields directly between calls.
 *
 *   angle:    Current filtered angle estimate (degrees)
 *   bias:     Estimated gyroscope bias (deg/s); pre-seeded from calibration mean
 *   P[2][2]:  2x2 error covariance matrix; initialized to zero
 *   Q_angle:  Process noise variance for angle state (from KF_Q_ANGLE in config.h)
 *   Q_bias:   Process noise variance for bias state  (from KF_Q_BIAS in config.h)
 *   R_measure: Static measurement noise variance      (from KF_R_MEASURE in config.h)
 */
typedef struct {
    float angle;       // Filtered angle (degrees)
    float bias;        // Gyroscope bias estimate (deg/s)
    float P[2][2];     // Error covariance matrix
    float Q_angle;     // Process noise: angle
    float Q_bias;      // Process noise: bias
    float R_measure;   // Measurement noise: accelerometer angle (static)
} KalmanFilter;

// ─── API ─────────────────────────────────────────────────────────────────────

/**
 * kalman_init() — Initialize a KalmanFilter instance.
 *
 * Sets angle=0, bias=initial_bias (from calibration gyro mean),
 * P to zero matrix, and Q/R constants from config.h.
 *
 * Call once per axis after calibrate_imu() completes.
 *
 * @param kf            Filter instance to initialize
 * @param initial_bias  Initial gyro bias estimate (deg/s) from calibration mean
 */
void kalman_init(KalmanFilter* kf, float initial_bias);

/**
 * accel_roll() — Compute roll angle from accelerometer readings.
 *
 * roll = atan2(aY, aZ) * RAD_TO_DEG
 * Range: (-180, +180] degrees. No singularity.
 *
 * @param aY  Calibrated accelerometer Y axis (m/s²)
 * @param aZ  Calibrated accelerometer Z axis (m/s²)
 * Returns: roll angle in degrees
 */
float accel_roll(float aY, float aZ);

/**
 * accel_pitch() — Compute pitch angle from accelerometer readings.
 *
 * pitch = atan2(-aX, sqrt(aY² + aZ²)) * RAD_TO_DEG
 * Range: (-90, +90] degrees. Singularity at ±90° (gimbal lock).
 * For a wrist-worn glove in clinical use, pitch rarely exceeds ±70°.
 *
 * @param aX  Calibrated accelerometer X axis (m/s²)
 * @param aY  Calibrated accelerometer Y axis (m/s²)
 * @param aZ  Calibrated accelerometer Z axis (m/s²)
 * Returns: pitch angle in degrees
 */
float accel_pitch(float aX, float aY, float aZ);

/**
 * kalman_update() — Run one predict+update cycle, return filtered angle.
 *
 * Predict step: integrate gyro_rate (minus estimated bias) over dt.
 * Update step:  correct with accel_angle via accelerometer-derived measurement.
 *
 * Adaptive R_measure: if |‖(aX,aY,aZ)‖ - 9.80665| > KF_ACCEL_DYNAMIC_THRESHOLD_MS2,
 * the filter uses KF_R_MEASURE_DYNAMIC instead of KF_R_MEASURE to reduce
 * accelerometer influence during active tremor/dynamic motion.
 *
 * @param kf           Filter instance (from kalman_init)
 * @param accel_angle  Accelerometer-derived angle for this axis (degrees)
 * @param gyro_rate    Raw gyroscope rate for this axis, bias-corrected externally
 *                     (note: Kalman will further correct with internal bias estimate)
 * @param dt           Time since last call (seconds, from CalibratedSample.dt)
 * @param aX           Calibrated accel X (m/s²) — used for adaptive R_measure
 * @param aY           Calibrated accel Y (m/s²)
 * @param aZ           Calibrated accel Z (m/s²)
 * Returns: updated filtered angle (degrees)
 */
float kalman_update(KalmanFilter* kf,
                    float         accel_angle,
                    float         gyro_rate,
                    float         dt,
                    float         aX,
                    float         aY,
                    float         aZ);
