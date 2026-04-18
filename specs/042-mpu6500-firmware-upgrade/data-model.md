# Data Model: ESP32 Firmware Upgrade — MPU6500 SPI & Pin Management

**Feature**: 042-mpu6500-firmware-upgrade  
**Date**: 2026-04-18  
**Layer**: Firmware (ESP32 C++) — no database entities; documents C++ data structures and hardware constants.

---

## Firmware Data Structures (Unchanged)

These structs in `firmware/include/imu.h` are **unchanged** — the SPI protocol change and sensitivity update only affect how raw bytes are read and scaled, not the output structure.

### RawSample

```
RawSample {
  aX, aY, aZ : float   // m/s², ±2g range (unchanged)
  gX, gY, gZ : float   // °/s, ±250 dps range (UPDATED from ±2000 dps)
  timestamp_ms: uint32_t
}
```

### CalibrationOffsets

```
CalibrationOffsets {
  aX_bias, aY_bias, aZ_bias : float  // m/s²
  gX_bias, gY_bias, gZ_bias : float  // °/s
  n_samples : uint16_t
  valid     : bool
}
```

### CalibratedSample

```
CalibratedSample {
  aX, aY, aZ : float  // m/s², bias-corrected
  gX, gY, gZ : float  // °/s, bias-corrected
  dt          : float  // seconds since previous sample, clamped [0.005, 0.020]
}
```

---

## Hardware Configuration Constants (Updated)

All constants live in `firmware/include/config.h`.

### Removed Constants

| Constant | Old Value | Reason |
|----------|-----------|--------|
| `I2C_SDA_PIN` | 21 | I2C replaced by SPI |
| `I2C_SCL_PIN` | 22 | I2C replaced by SPI |
| `I2C_FREQ_HZ` | 400000 | I2C replaced by SPI |

### Added Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MPU6500_SPI_SCK` | 18 | VSPI clock — freed from old CMG gimbal pin |
| `MPU6500_SPI_MISO` | 19 | VSPI master-in-slave-out — freed from old CMG flywheel pin |
| `MPU6500_SPI_MOSI` | 23 | VSPI master-out-slave-in |
| `MPU6500_SPI_CS` | 5 | VSPI chip-select for MPU6500 |
| `MPU6500_SPI_FREQ` | 1000000 | 1 MHz SPI clock (safe for wiring and breadboard) |

### Modified Constants

| Constant | Old Value | New Value | Reason |
|----------|-----------|-----------|--------|
| `CMG_GIMBAL_PIN` | 18 | 14 | Servo reassigned to GPIO 14 per hardware requirement |
| `CMG_FLYWHEEL_PIN` | 19 | 13 | ESC reassigned to GPIO 13 per hardware requirement |

### Updated Sensor Constants (in `imu.h`)

| Constant | Old Value | New Value | Reason |
|----------|-----------|-----------|--------|
| `MPU_WHO_AM_I_VAL` | `0x71` | `0x70` | MPU6500 WHO_AM_I = 0x70 |
| `GYRO_LSB_PER_DPS` | `16.384f` | `131.0f` | GFS_SEL=0 (±250 dps) vs GFS_SEL=3 (±2000 dps) |

### Unchanged Sensor Constants

| Constant | Value | Note |
|----------|-------|------|
| `ACCEL_LSB_PER_G` | `16384.0f` | AFS_SEL=0, ±2g — no change |
| `GRAVITY_MS2` | `9.80665f` | Physical constant |
| `CMG_GIMBAL_CHANNEL` | `0` | LEDC channel unchanged |
| `CMG_FLYWHEEL_CHANNEL` | `1` | LEDC channel unchanged |
| `CMG_PWM_FREQ_HZ` | `50` | 50 Hz servo/ESC standard |
| `CMG_PWM_RESOLUTION` | `16` | 16-bit duty unchanged |

---

## SPI Register Write Map (MPU6500 Init Sequence)

This documents the exact register values written during `imu_init()` and `imu_configure()`:

| Register | Address | Old Value | New Value | Effect |
|----------|---------|-----------|-----------|--------|
| `PWR_MGMT_1` | 0x6B | 0x80 | 0x80 | Software reset (unchanged) |
| `PWR_MGMT_1` | 0x6B | 0x01 | 0x01 | PLL clock source (unchanged) |
| `PWR_MGMT_2` | 0x6C | 0x00 | 0x00 | All axes enabled (unchanged) |
| `CONFIG` | 0x1A | 0x03 | 0x03 | DLPF 41 Hz (unchanged) |
| `SMPLRT_DIV` | 0x19 | 0x09 | 0x09 | ODR = 100 Hz (unchanged) |
| `GYRO_CONFIG` | 0x1B | **0x18** | **0x00** | **±2000 dps → ±250 dps** |
| `ACCEL_CONFIG` | 0x1C | 0x00 | 0x00 | ±2g (unchanged) |
| `ACCEL_CFG2` | 0x1D | 0x03 | 0x03 | Accel DLPF 41 Hz (unchanged) |

---

## GPIO Pin Assignment Map (Post-Upgrade)

| GPIO | Function | Module | Notes |
|------|----------|--------|-------|
| 5 | VSPI CS | MPU6500 SPI | Active-low chip select |
| 13 | LEDC CH1 PWM | CMG Flywheel ESC | 50 Hz, 16-bit — **reassigned** |
| 14 | LEDC CH0 PWM | CMG Gimbal Servo | 50 Hz, 16-bit — **reassigned** |
| 18 | VSPI SCK | MPU6500 SPI | **reassigned from CMG gimbal** |
| 19 | VSPI MISO | MPU6500 SPI | **reassigned from CMG flywheel** |
| 21 | (free) | — | Former I2C SDA — now unused |
| 22 | (free) | — | Former I2C SCL — now unused |
| 23 | VSPI MOSI | MPU6500 SPI | Unchanged |
| 34 | ADC1 CH6 | Battery reader | Unchanged |
| 2 | Fault LED | Status | Unchanged |
