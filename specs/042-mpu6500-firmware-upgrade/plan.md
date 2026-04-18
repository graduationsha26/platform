# Implementation Plan: ESP32 Firmware Upgrade & Pin Management

**Branch**: `042-mpu6500-firmware-upgrade` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/042-mpu6500-firmware-upgrade/spec.md`

## Summary

Upgrade the ESP32 firmware sensor driver from I2C-based MPU6050/MPU9250 to SPI-based MPU6500, configuring the sensor for ±2g / ±250 dps sensitivity. Simultaneously reassign the gimbal servo to GPIO 14 and the brushless motor ESC to GPIO 13, using the VSPI bus (SCK=18, MISO=19, MOSI=23, CS=5) for the MPU6500 to ensure zero overlap with actuator pins. All changes are confined to `firmware/` — no backend, frontend, or database impact.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework + Django Channels  
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts  
**Database**: Supabase PostgreSQL (remote)  
**Authentication**: JWT (SimpleJWT) with roles (doctor/admin)  
**Testing**: pytest (backend), Jest/Vitest (frontend)  
**Project Type**: Monorepo (backend/, frontend/, firmware/)  
**Real-time**: Django Channels WebSocket for live tremor data  
**Integration**: Bidirectional MQTT (ESP32 sensor data in, actuator commands out)  
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django `inference` app  
**Performance Goals**: 100 Hz IMU sampling over SPI; <70 ms sensor-to-actuation latency (unchanged from current)  
**Constraints**: Firmware-only change; flashed via USB. No backend/frontend changes. GPIO 13 and 14 strictly reserved for actuators.  
**Scale/Scope**: Single glove device. 5 source files modified, 0 new files created.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: All changes in `firmware/` — fits existing monorepo structure
- [x] **Tech Stack Immutability**: Arduino `SPI.h` is a built-in core library — no new frameworks or external libraries added
- [x] **Database Strategy**: Not applicable — firmware has no database access
- [x] **Authentication**: Not applicable — firmware uses MQTT with credentials in gitignored `config.h`
- [x] **Security-First**: WiFi and MQTT credentials remain in `config.h` (gitignored) — no change to credential handling
- [x] **Real-time Requirements**: Not applicable — Django Channels WebSocket layer is unchanged
- [x] **MQTT Integration**: `mqtt_publisher.cpp` is unchanged; the MQTT publish pipeline continues to operate identically
- [x] **AI Model Serving**: Not applicable — firmware does not serve ML models
- [x] **API Standards**: Not applicable — no REST endpoints changed
- [x] **Development Scope**: Local development only; firmware flashed via USB with PlatformIO

**Result**: ✅ PASS — No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/042-mpu6500-firmware-upgrade/
├── plan.md              ← this file
├── spec.md              ← feature specification
├── research.md          ← Phase 0: SPI protocol, pin analysis, register map
├── data-model.md        ← Phase 1: hardware constants, GPIO pin map, register table
├── quickstart.md        ← Phase 1: wiring guide and boot verification steps
├── contracts/
│   └── spi-interface.md ← Phase 1: SPI transaction protocol, wiring contract
└── checklists/
    └── requirements.md  ← spec quality checklist (all pass)
```

### Source Code (files modified — no new files)

```text
firmware/
├── include/
│   ├── config.h          ← MODIFY: remove I2C pins; add SPI pins; CMG 18/19→14/13
│   └── imu.h             ← MODIFY: WHO_AM_I 0x71→0x70; GYRO_LSB 16.384→131.0; comments
└── src/
    ├── imu.cpp           ← MODIFY: Wire→SPI; rewrite mpu_write/read/burst; GYRO_CONFIG 0x18→0x00
    ├── main.cpp          ← MODIFY: update comments and Serial strings (MPU9250→MPU6500, GPIO18/19→14/13)
    └── (cmg.cpp)         ← NO CHANGE: reads CMG_GIMBAL_PIN and CMG_FLYWHEEL_PIN from config.h only
├── platformio.ini        ← MODIFY: add 042 feature comment
```

**Structure Decision**: Five files modified, zero new files. The CMG actuation module (`cmg.cpp`) requires no code changes — it already reads pin numbers from `config.h` via `CMG_GIMBAL_PIN` and `CMG_FLYWHEEL_PIN`, so updating those constants is sufficient.

## Implementation Phases

### Phase: Setup

Configure SPI pins in `config.h` and update sensor constants in `imu.h`. These are the foundational constants that all subsequent changes depend on.

### Phase: Foundational — IMU Driver Rewrite

Rewrite the IMU driver (`imu.cpp`) to use SPI instead of I2C. This is the core of the feature and touches every I2C transaction in the file.

### Phase: User Story — US1 Full Integration

Update `main.cpp` comments and Serial strings, then update `platformio.ini` comment to complete the cross-file rename from MPU9250/MPU6050 to MPU6500.

### Phase: Polish

Verify no "6050" or "MPU-9250" strings remain. Confirm GPIO audit passes (no SPI pin equals 13 or 14).

## Complexity Tracking

No constitution violations. No complexity tracking required.
