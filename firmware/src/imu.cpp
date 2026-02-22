/**
 * imu.cpp — MPU9250 IMU Driver Implementation
 *
 * Feature: 025-imu-kalman-fusion
 *
 * Implements:
 *   T009: imu_init()       — I2C init, WHO_AM_I check, register config
 *   T010: imu_configure()  — ODR, DLPF, gyro/accel range registers
 *   T011: calibrate_imu()  — 500-sample bias collection with motion guard
 *   T013: read_raw_sample() — 14-byte burst read, int16→float conversion
 *   T014: apply_calibration() — bias subtraction, dt computation
 */

#include "imu.h"
#include "config.h"
#include <Wire.h>
#include <Arduino.h>
#include <math.h>

// ─── Internal helpers ─────────────────────────────────────────────────────────

static void mpu_write(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(MPU9250_I2C_ADDR);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
#ifdef FIRMWARE_DEBUG
    Serial.printf("[IMU] Write reg=0x%02X val=0x%02X\n", reg, value);
#endif
}

static uint8_t mpu_read(uint8_t reg) {
    Wire.beginTransmission(MPU9250_I2C_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU9250_I2C_ADDR, (uint8_t)1);
    return Wire.available() ? Wire.read() : 0xFF;
}

// ─── T010: imu_configure() ───────────────────────────────────────────────────

/**
 * Configure MPU9250 ODR, DLPF, and sensor ranges.
 * Called from imu_init() after clock source is established.
 *
 * Register map (from research.md):
 *   CONFIG      (0x1A) = 0x03  DLPF_CFG=3, gyro 41Hz BW, internal 1kHz
 *   SMPLRT_DIV  (0x19) = 0x09  ODR = 1000/(1+9) = 100Hz
 *   GYRO_CONFIG (0x1B) = 0x18  GFS_SEL=3 (±2000°/s), FCHOICE_B=00
 *   ACCEL_CONFIG(0x1C) = 0x00  AFS_SEL=0 (±2g)
 *   ACCEL_CFG2  (0x1D) = 0x03  accel DLPF 41Hz, 1kHz internal rate
 *
 * Magnetometer: USER_CTRL and INT_PIN_CFG are NOT written.
 * AK8963 stays isolated on internal aux I2C bus — zero latency impact.
 */
static void imu_configure() {
    mpu_write(MPU_REG_CONFIG,       0x03);  // DLPF_CFG=3: 41Hz gyro BW, 1kHz internal
    mpu_write(MPU_REG_SMPLRT_DIV,   0x09);  // ODR = 1000/(1+9) = 100Hz
    mpu_write(MPU_REG_GYRO_CONFIG,  0x18);  // GFS_SEL=3: ±2000°/s; FCHOICE_B=00
    mpu_write(MPU_REG_ACCEL_CONFIG, 0x00);  // AFS_SEL=0: ±2g
    mpu_write(MPU_REG_ACCEL_CFG2,   0x03);  // A_DLPFCFG=3: accel 41Hz BW
}

// ─── T009: imu_init() ────────────────────────────────────────────────────────

bool imu_init() {
    // Start I2C bus with configured pins and frequency
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ_HZ);
    delay(110);  // Power-on stabilization (datasheet: 100ms max)

    // Software reset — clears all internal registers to default
    mpu_write(MPU_REG_PWR_MGMT_1, 0x80);
    delay(100);  // Wait for reset to complete

    // WHO_AM_I check — verify sensor is present and responding
    uint8_t whoami = mpu_read(MPU_REG_WHO_AM_I);
    if (whoami != MPU_WHO_AM_I_VAL) {
        Serial.printf("[IMU] ERROR: WHO_AM_I=0x%02X (expected 0x71). Check I2C wiring.\n", whoami);
        return false;
    }
    Serial.printf("[IMU] WHO_AM_I OK (0x%02X)\n", whoami);

    // Wake device; select PLL clock source (auto-selects best available)
    mpu_write(MPU_REG_PWR_MGMT_1, 0x01);  // CLKSEL=1: PLL with gyro X reference
    delay(200);  // Allow PLL to stabilize

    // Enable all accelerometer and gyroscope axes
    mpu_write(MPU_REG_PWR_MGMT_2, 0x00);

    // Configure ODR, DLPF, gyro/accel ranges
    imu_configure();

    // Magnetometer confirmation:
    // USER_CTRL (0x6A) and INT_PIN_CFG (0x37) are intentionally NOT written.
    // AK8963 (I2C address 0x0C) stays isolated on the internal auxiliary bus.
    // No I2C transactions will occur to 0x0C during normal operation.
    Serial.println("[IMU] Magnetometer disabled (AK8963 isolated — zero latency impact)");

    return true;
}

// ─── T011: calibrate_imu() ───────────────────────────────────────────────────

bool calibrate_imu(CalibrationOffsets* offsets) {
    if (!offsets) return false;

    offsets->valid     = false;
    offsets->n_samples = 0;

    // Accumulators for mean computation
    double sum_aX = 0, sum_aY = 0, sum_aZ = 0;
    double sum_gX = 0, sum_gY = 0, sum_gZ = 0;

    // Min/max trackers for motion guard
    float min_gX =  1e9f, max_gX = -1e9f;
    float min_gY =  1e9f, max_gY = -1e9f;
    float min_gZ =  1e9f, max_gZ = -1e9f;

    Serial.printf("[CALIB] Collecting %d samples at %dHz (~%d seconds)...\n",
                  CALIB_N_SAMPLES, IMU_SAMPLE_RATE_HZ,
                  CALIB_N_SAMPLES / IMU_SAMPLE_RATE_HZ);

    for (int i = 0; i < CALIB_N_SAMPLES; i++) {
        // Burst-read 14 bytes directly (not via read_raw_sample to avoid recursion)
        uint8_t buf[14];
        Wire.beginTransmission(MPU9250_I2C_ADDR);
        Wire.write(MPU_REG_ACCEL_XOUT_H);
        Wire.endTransmission(false);
        Wire.requestFrom(MPU9250_I2C_ADDR, (uint8_t)14);
        for (int b = 0; b < 14 && Wire.available(); b++) {
            buf[b] = Wire.read();
        }

        // Reconstruct int16_t (big-endian, high byte first)
        int16_t raw_ax = (int16_t)((buf[0]  << 8) | buf[1]);
        int16_t raw_ay = (int16_t)((buf[2]  << 8) | buf[3]);
        int16_t raw_az = (int16_t)((buf[4]  << 8) | buf[5]);
        // buf[6], buf[7] = temperature (skip)
        int16_t raw_gx = (int16_t)((buf[8]  << 8) | buf[9]);
        int16_t raw_gy = (int16_t)((buf[10] << 8) | buf[11]);
        int16_t raw_gz = (int16_t)((buf[12] << 8) | buf[13]);

        // Convert to physical units
        float aX = (raw_ax / ACCEL_LSB_PER_G) * GRAVITY_MS2;
        float aY = (raw_ay / ACCEL_LSB_PER_G) * GRAVITY_MS2;
        float aZ = (raw_az / ACCEL_LSB_PER_G) * GRAVITY_MS2;
        float gX = raw_gx / GYRO_LSB_PER_DPS;
        float gY = raw_gy / GYRO_LSB_PER_DPS;
        float gZ = raw_gz / GYRO_LSB_PER_DPS;

        // Accumulate sums
        sum_aX += aX; sum_aY += aY; sum_aZ += aZ;
        sum_gX += gX; sum_gY += gY; sum_gZ += gZ;

        // Track gyro min/max for motion guard
        if (gX < min_gX) min_gX = gX; if (gX > max_gX) max_gX = gX;
        if (gY < min_gY) min_gY = gY; if (gY > max_gY) max_gY = gY;
        if (gZ < min_gZ) min_gZ = gZ; if (gZ > max_gZ) max_gZ = gZ;

#ifdef FIRMWARE_DEBUG
        if (i % 100 == 0) {
            Serial.printf("[CALIB] Sample %d/%d\n", i, CALIB_N_SAMPLES);
        }
#endif
        // Maintain ~100Hz collection rate
        delay(IMU_SAMPLE_PERIOD_MS);
    }

    // Motion guard: if any gyro axis range exceeds threshold, calibration is invalid
    float motion_threshold = GYRO_MOTION_THRESHOLD * 5.0f;  // 5 deg/s total range
    float range_gX = max_gX - min_gX;
    float range_gY = max_gY - min_gY;
    float range_gZ = max_gZ - min_gZ;

    if (range_gX > motion_threshold || range_gY > motion_threshold || range_gZ > motion_threshold) {
        Serial.printf("[CALIB] MOTION DETECTED during calibration window:\n");
        Serial.printf("[CALIB]   gX range=%.2f, gY range=%.2f, gZ range=%.2f (threshold=%.2f deg/s)\n",
                      range_gX, range_gY, range_gZ, motion_threshold);
        Serial.println("[CALIB] Keep the glove flat and stationary. Please power-cycle and retry.");
        offsets->valid = false;
        return false;
    }

    // Compute means
    int n = CALIB_N_SAMPLES;
    offsets->aX_bias = (float)(sum_aX / n);
    offsets->aY_bias = (float)(sum_aY / n);
    // aZ_bias: subtract gravity so calibrated aZ ≈ 0 at rest (glove flat, Z-axis up)
    offsets->aZ_bias = (float)(sum_aZ / n) - GRAVITY_MS2;
    offsets->gX_bias = (float)(sum_gX / n);
    offsets->gY_bias = (float)(sum_gY / n);
    offsets->gZ_bias = (float)(sum_gZ / n);
    offsets->n_samples = (uint16_t)n;
    offsets->valid = true;

    Serial.printf("[CALIB] Done. Offsets:\n");
    Serial.printf("[CALIB]   aX=%.4f aY=%.4f aZ=%.4f m/s2\n",
                  offsets->aX_bias, offsets->aY_bias, offsets->aZ_bias);
    Serial.printf("[CALIB]   gX=%.4f gY=%.4f gZ=%.4f deg/s\n",
                  offsets->gX_bias, offsets->gY_bias, offsets->gZ_bias);

    return true;
}

// ─── T013: read_raw_sample() ─────────────────────────────────────────────────

bool read_raw_sample(RawSample* out) {
    if (!out) return false;

    // Burst-read 14 bytes: ACCEL_XOUT_H (0x3B) through GYRO_ZOUT_L (0x48)
    Wire.beginTransmission(MPU9250_I2C_ADDR);
    Wire.write(MPU_REG_ACCEL_XOUT_H);
    uint8_t err = Wire.endTransmission(false);
    if (err != 0) {
        Serial.printf("[IMU] I2C error on read (code %d)\n", err);
        return false;
    }

    uint8_t received = Wire.requestFrom(MPU9250_I2C_ADDR, (uint8_t)14);
    if (received < 14) {
        Serial.println("[IMU] I2C NACK — fewer than 14 bytes received");
        return false;
    }

    uint8_t buf[14];
    for (int i = 0; i < 14; i++) {
        buf[i] = Wire.read();
    }

    // Reconstruct signed 16-bit integers (big-endian)
    int16_t raw_ax = (int16_t)((buf[0]  << 8) | buf[1]);
    int16_t raw_ay = (int16_t)((buf[2]  << 8) | buf[3]);
    int16_t raw_az = (int16_t)((buf[4]  << 8) | buf[5]);
    // buf[6], buf[7] = TEMP_OUT — read but discarded
    int16_t raw_gx = (int16_t)((buf[8]  << 8) | buf[9]);
    int16_t raw_gy = (int16_t)((buf[10] << 8) | buf[11]);
    int16_t raw_gz = (int16_t)((buf[12] << 8) | buf[13]);

    // Convert to physical units
    out->aX = (raw_ax / ACCEL_LSB_PER_G) * GRAVITY_MS2;   // m/s²
    out->aY = (raw_ay / ACCEL_LSB_PER_G) * GRAVITY_MS2;
    out->aZ = (raw_az / ACCEL_LSB_PER_G) * GRAVITY_MS2;
    out->gX = raw_gx / GYRO_LSB_PER_DPS;                   // °/s
    out->gY = raw_gy / GYRO_LSB_PER_DPS;
    out->gZ = raw_gz / GYRO_LSB_PER_DPS;
    out->timestamp_ms = millis();

    return true;
}

// ─── T014: apply_calibration() ───────────────────────────────────────────────

void apply_calibration(const RawSample*          raw,
                       const CalibrationOffsets* offsets,
                       CalibratedSample*         out) {
    // Persistent previous timestamp for dt computation
    static uint32_t prev_timestamp_ms = 0;

    if (!raw || !offsets || !out) return;

    // Subtract bias offsets
    out->aX = raw->aX - offsets->aX_bias;
    out->aY = raw->aY - offsets->aY_bias;
    out->aZ = raw->aZ - offsets->aZ_bias;
    out->gX = raw->gX - offsets->gX_bias;
    out->gY = raw->gY - offsets->gY_bias;
    out->gZ = raw->gZ - offsets->gZ_bias;

    // Compute dt in seconds from millis() delta
    if (prev_timestamp_ms == 0) {
        // First call after boot — use nominal period
        out->dt = (float)IMU_SAMPLE_PERIOD_MS / 1000.0f;
    } else {
        uint32_t delta_ms = raw->timestamp_ms - prev_timestamp_ms;
        out->dt = (float)delta_ms / 1000.0f;
    }
    prev_timestamp_ms = raw->timestamp_ms;

    // Clamp dt to [0.005, 0.020] seconds to guard against scheduler jitter
    if (out->dt < 0.005f) out->dt = 0.005f;
    if (out->dt > 0.020f) out->dt = 0.020f;

#ifdef FIRMWARE_DEBUG
    if (out->dt > 0.012f) {
        Serial.printf("[IMU] dt=%.4fs (>12ms — tick drift detected)\n", out->dt);
    }
#endif
}
