/**
 * imu.h — MPU9250 IMU Driver: Data Structures and API
 *
 * Feature: 025-imu-kalman-fusion
 *
 * Covers:
 *   - RawSample: uncorrected 6-axis reading in physical units
 *   - CalibrationOffsets: bias correction computed at startup
 *   - CalibratedSample: bias-corrected sample with timing delta
 *   - imu_init(): I2C init, WHO_AM_I check, register configuration (mag disabled)
 *   - calibrate_imu(): 500-sample startup calibration
 *   - read_raw_sample(): single 6-axis burst read
 *   - apply_calibration(): subtract biases, compute dt
 *
 * MPU9250 register config (research.md):
 *   CONFIG      (0x1A) = 0x03  DLPF 41Hz, internal rate 1kHz
 *   SMPLRT_DIV  (0x19) = 0x09  ODR = 1000/(1+9) = 100Hz
 *   GYRO_CONFIG (0x1B) = 0x18  ±2000°/s, FCHOICE_B=00
 *   ACCEL_CONFIG(0x1C) = 0x00  ±2g
 *   ACCEL_CONFIG2(0x1D)= 0x03  accel DLPF 41Hz
 *   Magnetometer: NOT initialized — AK8963 stays isolated
 *
 * Unit conventions:
 *   Accelerometer: m/s²  (raw / 16384.0 * 9.80665)
 *   Gyroscope:     °/s   (raw / 16.384)
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

// ─── MPU9250 I2C Address ──────────────────────────────────────────────────────
#define MPU9250_I2C_ADDR    0x68   // AD0 = GND (default)

// ─── MPU9250 Register Addresses ──────────────────────────────────────────────
#define MPU_REG_SMPLRT_DIV   0x19
#define MPU_REG_CONFIG       0x1A
#define MPU_REG_GYRO_CONFIG  0x1B
#define MPU_REG_ACCEL_CONFIG 0x1C
#define MPU_REG_ACCEL_CFG2   0x1D
#define MPU_REG_ACCEL_XOUT_H 0x3B  // First byte of 14-byte burst read block
#define MPU_REG_PWR_MGMT_1   0x6B
#define MPU_REG_PWR_MGMT_2   0x6C
#define MPU_REG_WHO_AM_I     0x75

#define MPU_WHO_AM_I_VAL     0x71  // Expected value for genuine MPU9250

// ─── Conversion Constants ─────────────────────────────────────────────────────
#define ACCEL_LSB_PER_G      16384.0f   // AFS_SEL=0, ±2g
#define GRAVITY_MS2          9.80665f
#define GYRO_LSB_PER_DPS     16.384f    // GFS_SEL=3, ±2000°/s

// ─── Data Structures ──────────────────────────────────────────────────────────

/**
 * RawSample — Uncorrected 6-axis reading in physical units.
 * Produced by read_raw_sample(). Not yet bias-corrected.
 *
 *   aX, aY, aZ: accelerometer axes in m/s² (range ±19.6 m/s²)
 *   gX, gY, gZ: gyroscope axes in °/s       (range ±2000 °/s)
 *   timestamp_ms: MCU millis() at moment of I2C burst read
 */
typedef struct {
    float    aX, aY, aZ;      // m/s²
    float    gX, gY, gZ;      // °/s
    uint32_t timestamp_ms;
} RawSample;

/**
 * CalibrationOffsets — Bias correction values computed during startup.
 * Applied to every RawSample via apply_calibration().
 *
 * Gyro biases: mean gyro reading over stationary window (should be ≈0 at rest)
 * Accel biases: mean accel reading; aZ_bias = mean_aZ - 9.80665 (gravity removed)
 */
typedef struct {
    float   aX_bias, aY_bias, aZ_bias;   // m/s²
    float   gX_bias, gY_bias, gZ_bias;   // °/s
    uint16_t n_samples;
    bool    valid;
} CalibrationOffsets;

/**
 * CalibratedSample — Bias-corrected 6-axis reading with timing delta.
 * Input to the Kalman filter.
 *
 *   aX..gZ: calibrated sensor values
 *   dt:     seconds since previous sample (clamped to [0.005, 0.020])
 */
typedef struct {
    float aX, aY, aZ;    // m/s², bias-corrected
    float gX, gY, gZ;    // °/s, bias-corrected
    float dt;            // seconds since previous sample
} CalibratedSample;

// ─── API ─────────────────────────────────────────────────────────────────────

/**
 * imu_init() — Initialize I2C, configure MPU9250, disable magnetometer.
 *
 * Performs:
 *   1. Wire.begin(SDA, SCL) at I2C_FREQ_HZ
 *   2. 110ms power-on delay
 *   3. Software reset (PWR_MGMT_1 = 0x80), 100ms delay
 *   4. WHO_AM_I check — returns false if not 0x71
 *   5. PLL clock source (PWR_MGMT_1 = 0x01), 200ms delay
 *   6. All axes enabled (PWR_MGMT_2 = 0x00)
 *   7. imu_configure(): ODR, DLPF, gyro/accel ranges
 *   NOTE: USER_CTRL and INT_PIN_CFG are NOT written — AK8963 stays isolated.
 *
 * Returns: true on success, false on WHO_AM_I mismatch or I2C error
 */
bool imu_init();

/**
 * calibrate_imu() — Collect 500 stationary samples, compute bias offsets.
 *
 * Motion guard: if gyro range (max-min) on any axis exceeds
 * GYRO_MOTION_THRESHOLD * 5.0f (deg/s), returns false (glove was moving).
 *
 * On success: offsets->valid = true, all bias fields populated.
 * On failure: offsets->valid = false, returns false.
 *
 * @param offsets  Output: populated CalibrationOffsets struct
 * Returns: true on success
 */
bool calibrate_imu(CalibrationOffsets* offsets);

/**
 * read_raw_sample() — Burst-read 14 bytes from MPU9250, convert to float.
 *
 * Reads registers 0x3B–0x48 (accel XYZ + temp + gyro XYZ).
 * Temperature bytes are read but discarded.
 *
 * Conversion:
 *   accel: (int16_t / 16384.0f) * 9.80665f  → m/s²
 *   gyro:  int16_t / 16.384f                → °/s
 *
 * @param out  Output: populated RawSample struct
 * Returns: true on success, false on I2C NACK
 */
bool read_raw_sample(RawSample* out);

/**
 * apply_calibration() — Subtract bias offsets, compute dt.
 *
 * dt is computed from raw->timestamp_ms minus the previous call's timestamp.
 * dt is clamped to [0.005, 0.020] seconds to handle scheduler jitter or
 * timer wrap-around.
 *
 * @param raw     Input: RawSample from read_raw_sample()
 * @param offsets Input: CalibrationOffsets from calibrate_imu()
 * @param out     Output: populated CalibratedSample
 */
void apply_calibration(const RawSample*          raw,
                       const CalibrationOffsets* offsets,
                       CalibratedSample*         out);
