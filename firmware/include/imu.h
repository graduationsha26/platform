/**
 * imu.h — MPU6500 IMU Driver: Data Structures and API
 *
 * Feature: 042-mpu6500-firmware-upgrade
 *
 * Covers:
 *   - RawSample: uncorrected 6-axis reading in physical units
 *   - CalibrationOffsets: bias correction computed at startup
 *   - CalibratedSample: bias-corrected sample with timing delta
 *   - imu_init(): SPI init, WHO_AM_I check, register configuration (no magnetometer)
 *   - calibrate_imu(): 500-sample startup calibration
 *   - read_raw_sample(): single 6-axis SPI burst read
 *   - apply_calibration(): subtract biases, compute dt
 *
 * MPU6500 register config (research.md):
 *   CONFIG      (0x1A) = 0x03  DLPF 41Hz, internal rate 1kHz
 *   SMPLRT_DIV  (0x19) = 0x09  ODR = 1000/(1+9) = 100Hz
 *   GYRO_CONFIG (0x1B) = 0x00  ±250°/s, FCHOICE_B=00
 *   ACCEL_CONFIG(0x1C) = 0x00  ±2g
 *   ACCEL_CONFIG2(0x1D)= 0x03  accel DLPF 41Hz
 *   No magnetometer — MPU6500 is accel/gyro only
 *
 * Unit conventions:
 *   Accelerometer: m/s²  (raw / 16384.0 * 9.80665)
 *   Gyroscope:     °/s   (raw / 131.0)
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

// ─── MPU6500 Register Addresses ──────────────────────────────────────────────
#define MPU_REG_SMPLRT_DIV   0x19
#define MPU_REG_CONFIG       0x1A
#define MPU_REG_GYRO_CONFIG  0x1B
#define MPU_REG_ACCEL_CONFIG 0x1C
#define MPU_REG_ACCEL_CFG2   0x1D
#define MPU_REG_ACCEL_XOUT_H 0x3B  // First byte of 14-byte burst read block
#define MPU_REG_PWR_MGMT_1   0x6B
#define MPU_REG_PWR_MGMT_2   0x6C
#define MPU_REG_WHO_AM_I     0x75

#define MPU_WHO_AM_I_VAL     0x70  // Expected value for MPU6500

// ─── Conversion Constants ─────────────────────────────────────────────────────
#define ACCEL_LSB_PER_G      16384.0f   // AFS_SEL=0, ±2g
#define GRAVITY_MS2          9.80665f
#define GYRO_LSB_PER_DPS     131.0f     // GFS_SEL=0, ±250°/s

// ─── Data Structures ──────────────────────────────────────────────────────────

/**
 * RawSample — Uncorrected 6-axis reading in physical units.
 * Produced by read_raw_sample(). Not yet bias-corrected.
 *
 *   aX, aY, aZ: accelerometer axes in m/s² (range ±19.6 m/s²)
 *   gX, gY, gZ: gyroscope axes in °/s       (range ±250 °/s)
 *   timestamp_ms: MCU millis() at moment of SPI burst read
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
 * imu_init() — Initialize SPI bus, configure MPU6500.
 *
 * Performs:
 *   1. pinMode(CS, OUTPUT); digitalWrite(CS, HIGH); spi_bus.begin(SCK,MISO,MOSI,CS)
 *   2. 110ms power-on delay
 *   3. Software reset (PWR_MGMT_1 = 0x80), 100ms delay
 *   4. WHO_AM_I check — returns false if not 0x70 (MPU6500)
 *   5. PLL clock source (PWR_MGMT_1 = 0x01), 200ms delay
 *   6. All axes enabled (PWR_MGMT_2 = 0x00)
 *   7. imu_configure(): ODR, DLPF, gyro/accel ranges
 *   NOTE: MPU6500 has no magnetometer — no AK8963 isolation needed.
 *
 * Returns: true on success, false on WHO_AM_I mismatch or SPI error
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
 * read_raw_sample() — SPI burst-read 14 bytes from MPU6500, convert to float.
 *
 * Reads registers 0x3B–0x48 (accel XYZ + temp + gyro XYZ).
 * Temperature bytes are read but discarded.
 *
 * Conversion:
 *   accel: (int16_t / 16384.0f) * 9.80665f  → m/s²
 *   gyro:  int16_t / 131.0f                 → °/s
 *
 * @param out  Output: populated RawSample struct
 * Returns: true on success, false on SPI error
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
