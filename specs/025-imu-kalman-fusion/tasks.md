# Tasks: IMU Initialization, Calibration & Kalman Filter Sensor Fusion

**Input**: Design documents from `/specs/025-imu-kalman-fusion/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in same batch)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are relative to the repository root

## Path Conventions

- Firmware source: `firmware/src/` and `firmware/include/`
- PlatformIO project root: `firmware/`
- No changes to `backend/` or `frontend/` — backend already handles the 6-axis reading payload

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `firmware/` PlatformIO project scaffolding and configuration files before any implementation begins.

- [X] T001 Create `firmware/` directory with subdirectories `firmware/include/`, `firmware/src/`, `firmware/lib/` as the PlatformIO project structure defined in plan.md
- [X] T002 Create `firmware/platformio.ini` with board target (espressif32 / esp32dev), framework (arduino), lib_deps (ArduinoJson@^6, PubSubClient, Wire), and monitor_speed 115200
- [X] T003 Create `firmware/include/config.h.example` with placeholder constants: `DEVICE_SERIAL`, `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `WIFI_SSID`, `WIFI_PASSWORD`, `IMU_SAMPLE_RATE_HZ 100`, `CALIB_N_SAMPLES 500`, `GYRO_MOTION_THRESHOLD 1.0f`, `KF_Q_ANGLE 0.001f`, `KF_Q_BIAS 0.003f`, `KF_R_MEASURE 0.03f`, `KF_R_MEASURE_DYNAMIC 0.09f`
- [X] T004 Create `firmware/src/main.cpp` with empty Arduino `setup()` and `loop()` stub, `#include` directives for `config.h`, `imu.h`, `kalman.h`, `mqtt_publisher.h`, and a `FIRMWARE_STATE` enum: `INIT`, `CALIBRATING`, `RUNNING`, `FAULT`
- [X] T005 Update root `.gitignore` to exclude `firmware/include/config.h` (real credentials), `firmware/.pio/` (PlatformIO build artifacts), and `firmware/.vscode/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Declare all shared data structures and function signatures across the three header files. These declarations are prerequisites for all three user stories.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete — all `.cpp` files include these headers.

- [X] T006 Create `firmware/include/imu.h` declaring: `RawSample` struct (aX, aY, aZ, gX, gY, gZ as float, timestamp_ms as uint32_t), `CalibrationOffsets` struct (aX_bias through gZ_bias as float, n_samples uint16_t, valid bool), `CalibratedSample` struct (aX through gZ as float, dt float), and function declarations: `bool imu_init()`, `bool calibrate_imu(CalibrationOffsets* offsets)`, `bool read_raw_sample(RawSample* out)`, `void apply_calibration(const RawSample* raw, const CalibrationOffsets* offsets, CalibratedSample* out)`
- [X] T007 [P] Create `firmware/include/kalman.h` declaring: `KalmanFilter` struct (angle float, bias float, P[2][2] float, Q_angle float, Q_bias float, R_measure float), and function declarations: `void kalman_init(KalmanFilter* kf, float initial_bias)`, `float accel_roll(float aY, float aZ)`, `float accel_pitch(float aX, float aY, float aZ)`, `float kalman_update(KalmanFilter* kf, float accel_angle, float gyro_rate, float dt)`
- [X] T008 [P] Create `firmware/include/mqtt_publisher.h` declaring: `FusedReading` struct (aX, aY, aZ, gX, gY, gZ, roll, pitch as float, timestamp_iso char[32]), and function declarations: `bool mqtt_connect()`, `void mqtt_loop()`, `bool publish_reading(const FusedReading* reading)`

**Checkpoint**: All headers compiled — implementation files can now be created in parallel across all user stories.

---

## Phase 3: User Story 1 — Reliable Sensor Startup (Priority: P1) 🎯 MVP

**Goal**: On power-on, the firmware detects the MPU9250, configures it correctly (magnetometer disabled, ±2g/±2000°/s ranges, 100Hz ODR), runs a startup calibration over 500 stationary samples, and enters a FAULT state if anything fails — all within 5 seconds and before any readings are transmitted.

**Independent Test**: Power on the glove with it flat and stationary. Observe serial monitor: expect `[IMU] WHO_AM_I OK`, `[IMU] Magnetometer disabled` (no I2C transactions to 0x0C), `[CALIB] Done` with non-zero bias offsets, and firmware state = RUNNING. Glove does not need to be connected to MQTT or transmit anything.

- [X] T009 [US1] Implement `imu_init()` in `firmware/src/imu.cpp`: call `Wire.begin()`, delay 110ms, write 0x80 to reg 0x6B (device reset), delay 100ms, read reg 0x75 (WHO_AM_I) and verify value is 0x71 (return false + log error on mismatch), write 0x01 to reg 0x6B (PLL clock, wake), write 0x00 to reg 0x6C (all axes enabled), delay 200ms; log `[IMU] WHO_AM_I OK (0x71)` and `[IMU] Magnetometer disabled` (note: USER_CTRL and INT_PIN_CFG are NOT written — AK8963 stays isolated); return true
- [X] T010 [US1] Implement ODR and range configuration in `firmware/src/imu.cpp` as a `imu_configure()` private helper called from `imu_init()`: write DLPF_CFG=0x03 to reg 0x1A (41Hz bandwidth, 1kHz internal rate), write SMPLRT_DIV=0x09 to reg 0x19 (100Hz ODR), write GYRO_CONFIG=0x18 to reg 0x1B (±2000°/s, FCHOICE_B=00), write ACCEL_CONFIG=0x00 to reg 0x1C (±2g), write ACCEL_CONFIG2=0x03 to reg 0x1D (accel 41Hz DLPF); log each register write in DEBUG mode
- [X] T011 [US1] Implement `calibrate_imu()` in `firmware/src/imu.cpp`: collect `CALIB_N_SAMPLES` (500) raw samples by calling the I2C burst read directly (not the full read_raw_sample to avoid recursion), accumulate sums for all 6 axes; compute means; apply gravity compensation: `aZ_bias = mean_aZ - 9.80665f`; motion guard: compute range (max−min) of gX, gY, gZ over the window — if any axis range exceeds `GYRO_MOTION_THRESHOLD * 5.0f` (5°/s total), log warning and set offsets->valid=false, return false; otherwise set offsets->valid=true, populate all bias fields, log `[CALIB] Done` with bias values, return true
- [X] T012 [US1] Wire US1 into `firmware/src/main.cpp` `setup()`: call `Serial.begin(115200)`, then `imu_init()` — on failure set state=FAULT; call `calibrate_imu(&g_offsets)` — on failure set state=FAULT; implement FAULT halt: `while(state == FAULT) { /* blink error LED if available; do not transmit */ delay(1000); }`; on success set state=CALIBRATING then RUNNING; declare global `CalibrationOffsets g_offsets` at file scope

**Checkpoint**: US1 complete — glove initializes, calibrates, and enters RUNNING state. FAULT path confirmed. No MQTT or sampling loop needed.

---

## Phase 4: User Story 2 — Continuous 100Hz Motion Sampling (Priority: P1)

**Goal**: From the RUNNING state, continuously read all 6 IMU axes at exactly 100Hz, apply calibration bias offsets, and produce a stream of `CalibratedSample` values timestamped to ≤5% timing jitter. No samples dropped over 60 seconds.

**Independent Test**: Add a USB serial log statement that prints `aX, aY, aZ, gX, gY, gZ, dt` for every sample. Monitor for 10 seconds and count lines — expect ~1000 lines with dt ≈ 0.010s (±0.0005s). Run without MQTT or Kalman filter active.

- [X] T013 [US2] Implement `read_raw_sample()` in `firmware/src/imu.cpp`: burst-read 14 bytes starting at register 0x3B (ACCEL_XOUT_H) using `Wire.beginTransmission` / `Wire.requestFrom`; reconstruct int16_t for each axis (high byte << 8 | low byte); convert accel to m/s²: `float_val = (int16_t / 16384.0f) * 9.80665f`; convert gyro to °/s: `float_val = int16_t / 16.384f`; set `out->timestamp_ms = millis()`; return true on success, false on I2C error (NACK)
- [X] T014 [US2] Implement `apply_calibration()` in `firmware/src/imu.cpp`: subtract each axis bias from the corresponding raw value (`out->aX = raw->aX - offsets->aX_bias`, etc.); compute `out->dt = (raw->timestamp_ms - g_prev_timestamp_ms) / 1000.0f`; clamp dt to range [0.005f, 0.020f] to guard against timer wrap or missed ticks; update `g_prev_timestamp_ms`; declare `static uint32_t g_prev_timestamp_ms` at file scope
- [X] T015 [US2] Implement 100Hz sampling tick in `firmware/src/main.cpp` `loop()`: use `millis()` scheduler — declare `static uint32_t last_tick_ms = 0`; if `(millis() - last_tick_ms) >= 10` then: call `read_raw_sample(&g_raw)`, call `apply_calibration(&g_raw, &g_offsets, &g_calib)`, update `last_tick_ms`; declare global `RawSample g_raw` and `CalibratedSample g_calib` at file scope; guard entire block with `if (state == RUNNING)`

**Checkpoint**: US2 complete — serial monitor shows 100 lines/second of calibrated 6-axis data. Timing jitter within ±5%. No MQTT or Kalman active.

---

## Phase 5: User Story 3 — Kalman Filter Sensor Fusion (Priority: P2)

**Goal**: Fuse each `CalibratedSample` through a Lauszus 2-state Kalman filter (separate instances for roll and pitch), then publish the resulting `FusedReading` as a JSON payload to `devices/{DEVICE_SERIAL}/reading` via MQTT at 100Hz, matching the backend validator schema exactly.

**Independent Test**: Subscribe to `devices/+/reading` with `mosquitto_sub`. Verify: (1) messages arrive at ~100Hz, (2) each JSON contains exactly `serial_number, timestamp, aX, aY, aZ, gX, gY, gZ`, (3) with glove stationary for 30s, `gX/gY/gZ ≈ 0 ±1°/s` after calibration, (4) verify `BiometricReading` records accumulate in Django backend at ~100 records/second.

- [X] T016 [US3] Implement `accel_roll()` and `accel_pitch()` in `firmware/src/kalman.cpp`: `float accel_roll(float aY, float aZ) { return atan2f(aY, aZ) * (180.0f / M_PI); }` and `float accel_pitch(float aX, float aY, float aZ) { return atan2f(-aX, sqrtf(aY*aY + aZ*aZ)) * (180.0f / M_PI); }`; include `<math.h>` and `"kalman.h"`
- [X] T017 [US3] Implement `kalman_init()` in `firmware/src/kalman.cpp`: set `kf->angle=0.0f`, `kf->bias=initial_bias` (pre-seeded from calibration gyro mean), `kf->P[0][0]=kf->P[0][1]=kf->P[1][0]=kf->P[1][1]=0.0f`, `kf->Q_angle=KF_Q_ANGLE`, `kf->Q_bias=KF_Q_BIAS`, `kf->R_measure=KF_R_MEASURE` from config.h constants
- [X] T018 [US3] Implement `kalman_update()` in `firmware/src/kalman.cpp` using the Lauszus formulation: **predict step** — `rate = gyro_rate - kf->bias; kf->angle += dt * rate; P[0][0] += dt*(dt*P[1][1]-P[0][1]-P[1][0]+Q_angle); P[0][1]-=dt*P[1][1]; P[1][0]-=dt*P[1][1]; P[1][1]+=Q_bias*dt;` **update step** — `y = accel_angle - kf->angle; S = P[0][0] + R_measure; K0=P[0][0]/S; K1=P[1][0]/S; kf->angle+=K0*y; kf->bias+=K1*y;` then update P using temporaries to avoid read-before-write; implement adaptive R_measure: compute `float accel_mag = sqrtf(aX*aX+aY*aY+aZ*aZ)` — if `fabsf(accel_mag-9.80665f) > 2.943f` (0.3g threshold), use `KF_R_MEASURE_DYNAMIC`; return `kf->angle`; add `aX, aY, aZ` parameters to signature for adaptive switching
- [X] T019 [P] [US3] Implement MQTT publisher in `firmware/src/mqtt_publisher.cpp`: include `<WiFi.h>`, `<PubSubClient.h>`, `<ArduinoJson.h>`, `"config.h"`, `"mqtt_publisher.h"`; implement `mqtt_connect()` — call `WiFi.begin(WIFI_SSID, WIFI_PASSWORD)`, wait up to 10s for connection, then `mqttClient.connect(DEVICE_SERIAL, MQTT_USERNAME, MQTT_PASSWORD)`, return bool success; implement `mqtt_loop()` — call `mqttClient.loop()`, reconnect if `!mqttClient.connected()`; implement `publish_reading()` — build JSON with `StaticJsonDocument<256>`, set fields: `serial_number=DEVICE_SERIAL`, `timestamp=reading->timestamp_iso`, `aX, aY, aZ, gX, gY, gZ` as doubles rounded to 4 decimal places; serialize to char buffer; publish to topic `"devices/" DEVICE_SERIAL "/reading"` via `mqttClient.publish()`; return bool success; declare `WiFiClient wifiClient` and `PubSubClient mqttClient(wifiClient)` at file scope
- [X] T020 [US3] Wire Kalman filter and MQTT into `firmware/src/main.cpp`: in `setup()` after calibration: call `mqtt_connect()` (log warning but do NOT FAULT on failure — retry in loop); declare `KalmanFilter g_roll_kf, g_pitch_kf` at file scope; call `kalman_init(&g_roll_kf, g_offsets.gX_bias)` and `kalman_init(&g_pitch_kf, g_offsets.gY_bias)` to seed initial bias from calibration; in `loop()` 100Hz tick: after `apply_calibration()`, compute `float roll = kalman_update(&g_roll_kf, accel_roll(g_calib.aX, g_calib.aY, g_calib.aZ), g_calib.gX, g_calib.dt, g_calib.aX, g_calib.aY, g_calib.aZ)` and `float pitch = kalman_update(...)` for pitch; populate `FusedReading g_fused` with calibrated sensor values + roll + pitch + ISO8601 timestamp string; call `publish_reading(&g_fused)`; call `mqtt_loop()`

**Checkpoint**: US3 complete — end-to-end pipeline operational. `mosquitto_sub` shows 100 JSON messages/second. Django backend logs `Stored BiometricReading` at ~100Hz.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Debug visibility, documentation, and end-to-end validation.

- [X] T021 [P] Add conditional `Serial.printf` debug logging throughout `firmware/src/imu.cpp` and `firmware/src/kalman.cpp`: guard all log statements with `#ifdef FIRMWARE_DEBUG` so production builds have zero overhead; log IMU register writes, calibration progress (every 100 samples), per-sample `dt` drift warning if `dt > 0.012f`, Kalman filter convergence (when `fabsf(kf->bias) < 0.1f` for first time)
- [X] T022 [P] Create `firmware/README.md` with: prerequisites (PlatformIO CLI or IDE, ESP32 board, Mosquitto), setup steps (copy config.h.example to config.h and fill credentials), build commands (`pio run`, `pio run --target upload`), serial monitor command (`pio device monitor`), and MQTT test command (`mosquitto_sub -t "devices/+/reading" -v`)
- [ ] T023 Validate end-to-end pipeline against `specs/025-imu-kalman-fusion/quickstart.md` Integration Scenarios 1–3: (1) power-on with flat glove → confirm serial log shows WHO_AM_I OK, CALIB Done, MQTT Connected; (2) run 10 seconds → confirm `mosquitto_sub` shows ~1000 messages; (3) check Django backend: `BiometricReading.objects.count()` increases by ~100/second — **MANUAL VALIDATION REQUIRED**: requires physical ESP32 hardware + MPU9250 sensor + running Mosquitto broker + running Django backend

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1, T001–T005)**: No dependencies — start immediately
- **Foundational (Phase 2, T006–T008)**: Depends on Setup completion — **BLOCKS all user stories**
- **US1 (Phase 3, T009–T012)**: Depends on Foundational (T006 for imu.h)
- **US2 (Phase 4, T013–T015)**: Depends on US1 completion (needs initialized IMU + calibration offsets)
- **US3 (Phase 5, T016–T020)**: Depends on US2 completion (needs 100Hz sampling loop) — T019 can start after T008 (mqtt_publisher.h only)
- **Polish (Phase 6, T021–T023)**: Depends on US3 completion

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 — no other story dependency
- **US2 (P1)**: Starts after US1 — needs initialized IMU and `g_offsets`
- **US3 (P2)**: Starts after US2 — needs `g_calib` CalibratedSample stream; T019 (MQTT) can start after T008 in parallel with US1/US2 work

### Within Each User Story

- US1: T009 (imu_init) → T010 (configure registers, called from imu_init) → T011 (calibrate) → T012 (wire into main)
- US2: T013 (read raw) → T014 (apply calib) → T015 (100Hz loop in main)
- US3: T016 (angle helpers) → T017 (kalman_init) → T018 (kalman_update); T019 [P] runs concurrently with T016–T018; T020 (wire all) after T018 + T019

---

## Parallel Opportunities

### Phase 2 Parallel
```
Run concurrently:
  T006: Create firmware/include/imu.h         (imu data structs + declarations)
  T007: Create firmware/include/kalman.h      (kalman structs + declarations)  [P]
  T008: Create firmware/include/mqtt_publisher.h (fused reading + mqtt decls)  [P]
```

### User Story 3 Partial Parallel
```
Run concurrently once US2 (T015) is complete:
  T016→T017→T018: kalman.cpp implementation (sequential within kalman.cpp)
  T019:           mqtt_publisher.cpp (different file — fully parallel)  [P]

T020 (wire pipeline in main.cpp) starts after T018 AND T019 are both done.
```

### Polish Parallel
```
Run concurrently:
  T021: Debug logging additions    [P]
  T022: firmware/README.md         [P]
```

---

## Implementation Strategy

### MVP First (US1 Only — Glove Powers On Correctly)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational headers (T006–T008)
3. Complete Phase 3: US1 — IMU init + calibration (T009–T012)
4. **STOP and VALIDATE**: Serial monitor shows WHO_AM_I OK + CALIB Done + RUNNING state
5. Confirm magnetometer is never addressed (no 0x0C I2C transactions)

### Incremental Delivery

1. Setup + Foundational → Project compiles, headers defined
2. US1 → Glove powers on, calibrates, reaches RUNNING state (MVP)
3. US2 → 100Hz stream of calibrated 6-axis readings visible in serial monitor
4. US3 → Kalman-filtered readings published to MQTT → stored in Django backend

### Single Developer Sequential Order

```
T001 → T002 → T003 → T004 → T005
T006 → T007 → T008              (headers: can do T007, T008 in parallel)
T009 → T010 → T011 → T012      (US1)
T013 → T014 → T015              (US2)
T016 → T017 → T018              (US3 Kalman — T019 can overlap with T016)
T019                             (US3 MQTT publisher)
T020                             (US3 wire pipeline)
T021 → T022 → T023              (Polish — T021, T022 in parallel)
```

---

## Notes

- All tasks write to `firmware/` only — zero changes to `backend/` or `frontend/`
- `config.h` must be copied from `config.h.example` and filled before `pio run`
- The `[P]` marker indicates different output files with no dependency on sibling [P] tasks completing first
- Each phase checkpoint can be validated independently using serial monitor output alone (no MQTT/backend required until US3)
- Backend integration (quickstart.md Scenario 2) requires: Django backend running, Mosquitto running, device registered with matching `DEVICE_SERIAL`
- Commit after each task or logical checkpoint to preserve incremental progress
