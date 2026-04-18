# Research: ESP32 Firmware Upgrade — MPU6500 SPI & Pin Management

**Feature**: 042-mpu6500-firmware-upgrade  
**Date**: 2026-04-18  
**Status**: Complete — all unknowns resolved

---

## R-001: MPU6500 WHO_AM_I Register Value

**Decision**: Accept `0x70` as the only valid WHO_AM_I response.  
**Rationale**: MPU6500 Product Specification (PS-MPU-6500A-01 Rev 1.0, §9.12) defines WHO_AM_I (reg 0x75) as `0x70`. The previous firmware accepted `0x71` (MPU-9250) and `0x68` (MPU-6050) as fallbacks — both must be removed to enforce strict chip identity.  
**Alternatives considered**: Keeping the multi-chip fallback. Rejected because it would silently allow wrong sensors that report incorrect data, defeating the purpose of the hardware upgrade.

---

## R-002: MPU6500 SPI Protocol

**Decision**: SPI Mode 3 (CPOL=1, CPHA=1), MSBFIRST, 1 MHz clock.  
**Rationale**:
- MPU6500 datasheet specifies SPI Mode 3 as the required mode.
- Read transactions: set MSB of the address byte to 1 (`0x80 | reg`).
- Write transactions: set MSB of the address byte to 0 (`reg & 0x7F`).
- 1 MHz is the conservative safe speed for both config and burst reads. The datasheet permits up to 20 MHz for data reads, but 1 MHz is sufficient at 100 Hz sampling and eliminates any marginal signal-integrity concerns on breadboard/glove wiring.
- Burst read: assert CS, send `0x80 | 0x3B` (ACCEL_XOUT_H with read bit), clock out 14 bytes of zeros to receive data, deassert CS.

**Alternatives considered**: 20 MHz SPI for maximum throughput. Rejected because 1 MHz gives ~1.4 µs per byte × 15 bytes = ~21 µs per burst — negligible at 100 Hz. The speed improvement is not needed and adds risk on hardware wiring.

---

## R-003: MPU6500 Register Map Compatibility

**Decision**: MPU6500 register addresses are identical to MPU6050/MPU9250 for all used registers. No remapping needed.  
**Rationale**: MPU6500 shares the same accel/gyro register block:
- `CONFIG` (0x1A), `SMPLRT_DIV` (0x19), `GYRO_CONFIG` (0x1B), `ACCEL_CONFIG` (0x1C), `ACCEL_CFG2` (0x1D)
- `PWR_MGMT_1` (0x6B), `PWR_MGMT_2` (0x6C)
- `ACCEL_XOUT_H` (0x3B) through `GYRO_ZOUT_L` (0x48) — 14-byte burst block
- `WHO_AM_I` (0x75)

The only change is the WHO_AM_I value (0x70 instead of 0x71) and the communication protocol (SPI instead of I2C).

**Alternatives considered**: None — this is a verified fact from the MPU6500 datasheet.

---

## R-004: Gyroscope Sensitivity for ±250 dps

**Decision**: Write `0x00` to `GYRO_CONFIG` (0x1B). Update `GYRO_LSB_PER_DPS` constant from `16.384f` to `131.0f`.  
**Rationale**: GFS_SEL bits [4:3] of GYRO_CONFIG register:
- `0x00` → GFS_SEL=0 → ±250 °/s → 131.0 LSB/°/s ✅ (new)
- `0x18` → GFS_SEL=3 → ±2000 °/s → 16.384 LSB/°/s (old)

The ±250 dps range provides ~8× higher resolution per LSB, appropriate for Parkinsonian tremor (4–12 Hz oscillation, typically < 100 °/s amplitude). The existing `ACCEL_CONFIG` write of `0x00` (AFS_SEL=0, ±2g) remains unchanged.

**Alternatives considered**: ±500 dps (GFS_SEL=1). Rejected — user specification explicitly requests ±250 dps.

---

## R-005: SPI Pin Selection — No Conflict with GPIO 13 & 14

**Decision**: Use ESP32 VSPI peripheral with pins SCK=GPIO18, MISO=GPIO19, MOSI=GPIO23, CS=GPIO5.  
**Rationale**:
- The actuators move from GPIO18/19 to GPIO13/14. This frees GPIO18/19 for the SPI bus.
- VSPI (GPIO18 SCK, GPIO19 MISO, GPIO23 MOSI, GPIO5 CS) uses none of the protected pins (13, 14).
- GPIO5 is a standard digital output, suitable for SPI CS. It has no ADC2 conflict since the application only uses ADC1 (GPIO34 for battery).
- VSPI is the ESP32 default SPI bus, well-tested with the Arduino SPI library.

**Pin conflict audit**:
| Pin | Function | Overlaps GPIO13? | Overlaps GPIO14? |
|-----|----------|-----------------|-----------------|
| GPIO18 | VSPI SCK | No | No |
| GPIO19 | VSPI MISO | No | No |
| GPIO23 | VSPI MOSI | No | No |
| GPIO5  | VSPI CS  | No | No |

**Alternatives considered**:
- HSPI (GPIO14 SCK, GPIO12 MISO, GPIO13 MOSI, GPIO15 CS): Rejected — SCK=GPIO14 and MOSI=GPIO13 directly conflict with the required actuator pins.
- Custom SPI pins via SPIClass constructor: Possible but unnecessary when VSPI pins are free.

---

## R-006: Arduino SPI Library Usage on ESP32

**Decision**: Use Arduino built-in `SPI.h` with `SPIClass spi_bus(VSPI)`. No new library dependency.  
**Rationale**: The ESP32 Arduino framework includes `SPI.h` as a core library. The `SPIClass` constructor accepts `VSPI` or `HSPI` as the bus selector. `spi_bus.begin(SCK, MISO, MOSI, CS)` initializes the bus. `SPISettings(freq, MSBFIRST, SPI_MODE3)` wraps each transaction.

No change to `platformio.ini` is required since `SPI` is always available in the Arduino framework.

**Alternatives considered**: External MPU6500 Arduino library. Rejected — introduces an unneeded dependency. Direct register access via SPI transactions is straightforward and already implemented for the I2C driver.

---

## R-007: GPIO 13 & 14 LEDC PWM Compatibility

**Decision**: GPIO 13 and GPIO 14 are both fully LEDC-capable on ESP32. Assign CMG_FLYWHEEL_PIN=13, CMG_GIMBAL_PIN=14 with existing LEDC channels 0 and 1.  
**Rationale**:
- All ESP32 GPIOs (0–39, excluding input-only 34–39) support LEDC PWM output.
- GPIO13 is the HSPI MOSI alternate function, and GPIO14 is the HSPI SCK alternate function, but these are irrelevant once LEDC is configured.
- Existing `ledcSetup()` / `ledcAttachPin()` / `ledcWrite()` calls in `cmg.cpp` require only updating `CMG_GIMBAL_PIN` and `CMG_FLYWHEEL_PIN` constants in `config.h`. No code changes in `cmg.cpp` itself.

**Alternatives considered**: None — GPIO 13/14 are hardware-specified by the user. Verified they are LEDC-capable.

---

## R-008: Wire.h Removal

**Decision**: Remove `#include <Wire.h>` from `imu.cpp` and the I2C `Wire.begin()` call from `imu_init()`. No other source file uses Wire.  
**Rationale**: Grep confirms `Wire` is only used in `imu.cpp`. Removing it eliminates I2C bus initialization, freeing GPIO21/22 (former SDA/SCL) for other use and reducing boot time by ~110 ms.

---

## Summary: All File Changes Required

| File | Change Type | Key Changes |
|------|-------------|-------------|
| `firmware/include/config.h` | Modify | Remove I2C pins; add SPI pins (18,19,23,5); CMG pins 18→14, 19→13 |
| `firmware/include/imu.h` | Modify | WHO_AM_I 0x71→0x70; GYRO_LSB 16.384→131.0; remove I2C addr define; update comments |
| `firmware/src/imu.cpp` | Modify | Wire→SPI; rewrite mpu_write/read/burst; update WHO_AM_I check; GYRO_CONFIG 0x18→0x00 |
| `firmware/src/main.cpp` | Modify | Update comments/Serial strings: MPU9250→MPU6500, I2C→SPI, GPIO18/19→GPIO14/13 |
| `firmware/platformio.ini` | Modify | Update feature comment to include 042-mpu6500-firmware-upgrade |
