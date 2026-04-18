# Quickstart: MPU6500 SPI Firmware Upgrade

**Feature**: 042-mpu6500-firmware-upgrade  
**Date**: 2026-04-18

---

## Prerequisites

- ESP32 dev board (38-pin, CH340/CP210x USB-serial)
- MPU6500 breakout module (not GY-521/MPU6050)
- Servo motor and brushless motor + ESC
- PlatformIO installed in VS Code

---

## Step 1: Wire the Hardware

Connect the MPU6500 to the ESP32 using **VSPI** pins:

```
MPU6500 VCC  → ESP32 3.3V
MPU6500 GND  → ESP32 GND
MPU6500 SCL  → ESP32 GPIO 18  (VSPI SCK)
MPU6500 SDA  → ESP32 GPIO 23  (VSPI MOSI)
MPU6500 SDO  → ESP32 GPIO 19  (VSPI MISO)
MPU6500 NCS  → ESP32 GPIO 5   (VSPI CS)
```

Connect the actuators:

```
Servo signal wire   → ESP32 GPIO 14
ESC signal wire     → ESP32 GPIO 13
```

> **Critical**: Do NOT connect any MPU6500 pin to GPIO 13 or GPIO 14.

---

## Step 2: Open the Project

```
File > Open Folder → firmware/
```

PlatformIO auto-detects `platformio.ini`.

---

## Step 3: Build and Flash

```
# Build (Ctrl+Alt+B)
# Upload (Ctrl+Alt+U)
```

Select `esp32dev` environment (default) for production, or `esp32dev-debug` for verbose output.

---

## Step 4: Verify — Serial Monitor

Open Serial Monitor (115200 baud). Expected boot output:

```
[BOOT] TremoAI Glove Firmware starting...
[IMU] WHO_AM_I OK (0x70 — MPU6500 detected)
[IMU] Magnetometer disabled (not present in MPU6500)
[CALIB] Collecting 500 samples at 100Hz (~5 seconds)...
[CALIB] Done. Offsets:
[CALIB]   aX=... aY=... aZ=... m/s2
[CALIB]   gX=... gY=... gZ=... deg/s
[BOOT] Battery ADC initialized.
[CMG] Initialized. Gimbal GPIO14 (ch0), Flywheel GPIO13 (ch1), 50Hz 16-bit.
[BOOT] FreeRTOS tasks started.
[BOOT] Firmware running — ...
```

### Fault Indicators

| Serial Output | Cause | Fix |
|---------------|-------|-----|
| `WHO_AM_I=0x68 (expected 0x70)` | Old MPU6050 still connected | Swap to MPU6500 |
| `WHO_AM_I=0x71 (expected 0x70)` | Old MPU9250 still connected | Swap to MPU6500 |
| `WHO_AM_I=0xFF (expected 0x70)` | SPI wiring error | Check GPIO 18/19/23/5 connections |
| `MOTION DETECTED during calibration` | Glove moved during 5s cal window | Power-cycle and keep still |

---

## Step 5: Validate Sensor Ranges (Debug Build)

Switch to `esp32dev-debug` and confirm live readings via Serial Monitor stay within:

- Accelerometer: `-19.6` to `+19.6 m/s²` (±2g)
- Gyroscope: `-250` to `+250 °/s`

Readings outside these ranges indicate a misconfigured GYRO_CONFIG register.

---

## Step 6: Validate Actuator Pins

With a servo and ESC connected:

1. Servo on GPIO 14 should center (1500 µs pulse) at boot.
2. ESC on GPIO 13 should receive minimum throttle (1000 µs) for 2 seconds (arming beeps from ESC), then ramp to operating throttle.

If motors don't respond, verify GPIO 14 / GPIO 13 signal wires are connected correctly and not swapped.
