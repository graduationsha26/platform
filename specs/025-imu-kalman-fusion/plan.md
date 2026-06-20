# Implementation Plan: IMU Initialization, Calibration & Kalman Filter Sensor Fusion

**Branch**: `025-imu-kalman-fusion` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-imu-kalman-fusion/spec.md`

## Summary

Implement firmware-side IMU initialization, startup calibration, and Kalman filter sensor fusion for the TremoAI smart glove. The MPU9250 IMU sensor is configured over I2C at 100Hz (accelerometer + gyroscope only; magnetometer disabled to eliminate latency). A startup calibration routine computes per-axis bias offsets. A 4-state Kalman filter (roll, pitch, gyro bias x, gyro bias y) fuses gyroscope integration (predict step) with accelerometer-derived orientation (update step) to produce clean, drift-free orientation estimates at 100Hz. Fused readings are published to the TremoAI MQTT broker as JSON on topic `devices/{serial}/reading`, matching the existing backend validator schema (`aX, aY, aZ, gX, gY, gZ, timestamp, serial_number`).

## Technical Context

**Firmware Platform**: Embedded C/C++ on an MQTT-capable microcontroller (e.g., ESP32 or compatible). Platform-agnostic where possible; wire protocol is I2C + WiFi MQTT.
**IMU Sensor**: MPU9250 — 3-axis accelerometer + 3-axis gyroscope, connected via I2C.
**Magnetometer**: AK8963 (on-chip in MPU9250) — explicitly disabled; never initialized.
**Sensor Fusion Algorithm**: 4-state linear Kalman filter (roll, pitch, gyro bias x/y). No quaternion math required. Yaw is not estimated (no magnetometer for yaw reference).
**Sampling Rate**: 100Hz (10ms period). Achieved by DLPF + SMPLRT_DIV = 9 on gyro.
**MQTT Protocol**: JSON over MQTT to broker at `MQTT_BROKER_URL`. Topic: `devices/{serial}/reading`.
**Accel Range**: ±2g (AFS_SEL=0) → ±19.6 m/s². Backend accepts ±20 m/s².
**Gyro Range**: ±2000°/s (FS_SEL=3). Backend accepts ±2000°/s.
**Performance Goals**: Kalman update loop must complete within 10ms (one sample period) on the target MCU.
**Constraints**: Local development only. No cloud deployment. MQTT credentials in `.env` equivalent (device config header or NVS on ESP32).
**Scale/Scope**: One glove device per patient. Continuous streaming during active monitoring sessions.
**Backend Integration**: Backend subscriber at `devices/{serial}/reading` is already implemented and validates the 6-axis JSON payload (see `backend/realtime/validators.py`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Firmware lives in `firmware/` at monorepo root — **JUSTIFIED EXTENSION** (see Complexity Tracking). Not a violation: the constitution governs `backend/` and `frontend/`; `firmware/` is the data source layer required for the system to function.
- [x] **Tech Stack Immutability**: Firmware uses C/C++ on embedded MCU — **JUSTIFIED EXTENSION** (see Complexity Tracking). The web stack (Django/React) is untouched.
- [x] **Database Strategy**: Firmware has no direct database access. Sensor data flows → MQTT → Django backend → Supabase PostgreSQL. ✅ PASS (N/A to firmware layer)
- [x] **Authentication**: Firmware authenticates to MQTT broker via username/password credentials stored in device config (not JWT). ✅ PASS (JWT is web-layer auth; MQTT is broker-layer auth)
- [x] **Security-First**: MQTT broker credentials stored in device config header (not hardcoded literals). Device serial number identifies the glove. ✅ PASS
- [x] **Real-time Requirements**: Firmware is the upstream source. It publishes to MQTT → Django backend → Django Channels WebSocket → frontend. ✅ PASS (pipeline intact)
- [x] **MQTT Integration**: Firmware IS the MQTT publisher. Backend subscriber already exists (`backend/realtime/mqtt_client.py`). ✅ PASS
- [x] **AI Model Serving**: Firmware does not serve AI models. Inference happens in Django backend. ✅ PASS (N/A)
- [x] **API Standards**: MQTT payloads use JSON with snake_case keys matching backend validator schema. ✅ PASS
- [x] **Development Scope**: Firmware development is local only. No CI/CD or cloud deployment. ✅ PASS

**Result**: ✅ PASS with two JUSTIFIED EXTENSIONS (see Complexity Tracking)

## Project Structure

### Documentation (this feature)

```text
specs/025-imu-kalman-fusion/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — firmware data structures
├── quickstart.md        # Phase 1 output — integration guide
├── contracts/           # Phase 1 output
│   └── mqtt-reading.yaml   # MQTT payload contract for devices/{serial}/reading
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
firmware/
├── platformio.ini              # PlatformIO project config (or CMakeLists.txt)
├── include/
│   ├── config.h                # Device serial, MQTT broker config, WiFi credentials
│   ├── imu.h                   # IMU init, calibration, read functions
│   ├── kalman.h                # Kalman filter struct and function declarations
│   └── mqtt_publisher.h        # MQTT connection and publish functions
├── src/
│   ├── main.cpp                # Entry point: init, 100Hz loop
│   ├── imu.cpp                 # MPU9250 I2C driver: init, calibrate, read_6axis
│   ├── kalman.cpp              # Kalman filter: init, predict, update, get_estimate
│   └── mqtt_publisher.cpp      # MQTT connect, publish_reading, reconnect
└── lib/
    └── (third-party I2C/MQTT libraries as submodules or PlatformIO deps)

backend/                        # NO CHANGES REQUIRED
realtime/validators.py          # Already accepts 6-axis reading schema — no change
realtime/mqtt_client.py         # Already handles devices/{serial}/reading — no change
```

**Structure Decision**: Firmware is new code in a new `firmware/` directory. Zero changes to existing Django backend — the `devices/{serial}/reading` handler and 6-axis validator are already production-ready.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| New `firmware/` project directory (not `backend/` or `frontend/`) | The smart glove firmware is the physical sensor data source; without it, the platform has no data to process | Moving firmware to a separate repo would break the atomic commit model and complicate version synchronization between firmware payload format and backend validator |
| C/C++ embedded code (not Django/React) | MPU9250 is a hardware component; it requires embedded C/C++ driver code and cannot be driven from a web framework | Python/Django cannot execute on a bare-metal microcontroller; no alternative exists |
