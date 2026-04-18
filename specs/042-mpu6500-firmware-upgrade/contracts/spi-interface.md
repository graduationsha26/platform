# Hardware Interface Contract: MPU6500 SPI Driver

**Feature**: 042-mpu6500-firmware-upgrade  
**Contract Type**: Firmware hardware interface (replaces API contract for this firmware-only feature)  
**Date**: 2026-04-18

---

## SPI Bus Configuration

```
Bus:         VSPI (ESP32 hardware SPI peripheral)
Mode:        SPI Mode 3 (CPOL=1, CPHA=1)
Bit order:   MSBFIRST
Clock:       1,000,000 Hz (1 MHz)
CS polarity: Active LOW
```

---

## Wiring Contract

| ESP32 GPIO | MPU6500 Pin | Signal |
|------------|-------------|--------|
| GPIO 18 | SCL/SCLK | SPI Clock |
| GPIO 19 | AD0/SDO | MISO (sensor → ESP32) |
| GPIO 23 | SDA/SDI | MOSI (ESP32 → sensor) |
| GPIO 5 | NCS/CS | Chip Select (active LOW) |
| 3.3V | VCC | Power |
| GND | GND | Ground |

**CRITICAL — Protected Pins**: GPIO 13 and GPIO 14 MUST NOT be connected to the MPU6500.

| GPIO | Reserved For | Do Not Connect To MPU6500 |
|------|-------------|--------------------------|
| GPIO 13 | Brushless motor ESC (LEDC CH1) | Any SPI signal |
| GPIO 14 | Servo motor (LEDC CH0) | Any SPI signal |

---

## SPI Transaction Protocol

### Single Register Write

```
1. spi.beginTransaction(SPISettings(1MHz, MSBFIRST, SPI_MODE3))
2. digitalWrite(CS, LOW)
3. spi.transfer(reg & 0x7F)   // address byte, MSB=0 for write
4. spi.transfer(value)         // data byte
5. digitalWrite(CS, HIGH)
6. spi.endTransaction()
```

### Single Register Read

```
1. spi.beginTransaction(SPISettings(1MHz, MSBFIRST, SPI_MODE3))
2. digitalWrite(CS, LOW)
3. spi.transfer(0x80 | reg)   // address byte, MSB=1 for read
4. value = spi.transfer(0x00) // dummy write to clock in data
5. digitalWrite(CS, HIGH)
6. spi.endTransaction()
7. return value
```

### 14-Byte Burst Read (accel + temp + gyro)

```
Start register: 0x3B (ACCEL_XOUT_H), read bit set → 0xBB

1. spi.beginTransaction(SPISettings(1MHz, MSBFIRST, SPI_MODE3))
2. digitalWrite(CS, LOW)
3. spi.transfer(0xBB)          // 0x80 | 0x3B
4. for b in 0..13:
     buf[b] = spi.transfer(0x00)
5. digitalWrite(CS, HIGH)
6. spi.endTransaction()

Byte layout (identical to I2C burst read):
  buf[0..1]  : ACCEL_XOUT (big-endian int16)
  buf[2..3]  : ACCEL_YOUT
  buf[4..5]  : ACCEL_ZOUT
  buf[6..7]  : TEMP_OUT (discarded)
  buf[8..9]  : GYRO_XOUT
  buf[10..11]: GYRO_YOUT
  buf[12..13]: GYRO_ZOUT
```

---

## Initialization Sequence Contract

```
Step 1: pinMode(CS, OUTPUT); digitalWrite(CS, HIGH)   // Deassert CS before SPI.begin
Step 2: spi.begin(SCK=18, MISO=19, MOSI=23, CS=5)
Step 3: delay(110)                                     // Power-on stabilization
Step 4: Write PWR_MGMT_1 (0x6B) = 0x80               // Software reset
Step 5: delay(100)                                     // Reset completion
Step 6: Read WHO_AM_I (0x75) → must equal 0x70        // MPU6500 identity check
Step 7: Write PWR_MGMT_1 (0x6B) = 0x01               // PLL clock source
Step 8: delay(200)                                     // PLL stabilization
Step 9: Write PWR_MGMT_2 (0x6C) = 0x00               // Enable all axes
Step 10: imu_configure() → write ODR, DLPF, ranges    // See register table below
```

### imu_configure() Register Writes

```
CONFIG      (0x1A) = 0x03   DLPF_CFG=3, 41Hz gyro BW, 1kHz internal
SMPLRT_DIV  (0x19) = 0x09   ODR = 1000/(1+9) = 100 Hz
GYRO_CONFIG (0x1B) = 0x00   GFS_SEL=0: ±250°/s, FCHOICE_B=00
ACCEL_CONFIG(0x1C) = 0x00   AFS_SEL=0: ±2g
ACCEL_CFG2  (0x1D) = 0x03   A_DLPFCFG=3: accel 41Hz BW
```

---

## Actuator PWM Contract

| Actuator | GPIO | LEDC Channel | Frequency | Resolution | Signal Type |
|----------|------|-------------|-----------|------------|-------------|
| Servo (gimbal) | 14 | 0 | 50 Hz | 16-bit | Standard RC servo: 1000–2000 µs |
| ESC (flywheel) | 13 | 1 | 50 Hz | 16-bit | Standard RC ESC: 1000–2000 µs |

**Duty formula**: `duty = (pulse_us × 65536) / 20000`

**ESC arming**: ESC must receive minimum throttle (1000 µs = duty 3277) for 2 seconds before ramp to operating throttle.

---

## Error Handling Contract

| Condition | Detection | Action |
|-----------|-----------|--------|
| WHO_AM_I ≠ 0x70 | Read reg 0x75 | Serial error + return false → STATE_FAULT in main.cpp |
| SPI bus failure | SPIClass methods return 0xFF consistently | Same as WHO_AM_I failure path |
