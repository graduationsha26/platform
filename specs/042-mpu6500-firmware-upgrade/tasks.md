# Tasks: ESP32 Firmware Upgrade & Pin Management

**Input**: Design documents from `/specs/042-mpu6500-firmware-upgrade/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/spi-interface.md ✅  
**Tests**: Not requested — no test tasks included.  
**Scope**: Firmware-only. 5 files modified, 0 new files. No backend/frontend/database changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US1]**: Belongs to User Story 1 — MPU6500 SPI Sensor Integration & Pin-Safe Actuation
- All paths are relative to the repository root

---

## Phase 1: Setup — Hardware Constants

**Purpose**: Establish the pin assignment constants that ALL other firmware files depend on.

**⚠️ CRITICAL**: `config.h` defines `CMG_GIMBAL_PIN`, `CMG_FLYWHEEL_PIN`, and the new SPI pin constants. `imu.cpp` and `cmg.cpp` both read from this file, so it must be updated first.

- [x] T001 [P] Update `firmware/include/config.h` — remove the I2C block (`I2C_SDA_PIN=21`, `I2C_SCL_PIN=22`, `I2C_FREQ_HZ=400000`) and replace with a new `MPU6500 SPI` block containing: `MPU6500_SPI_SCK=18`, `MPU6500_SPI_MISO=19`, `MPU6500_SPI_MOSI=23`, `MPU6500_SPI_CS=5`, `MPU6500_SPI_FREQ=1000000`; change `CMG_GIMBAL_PIN` from `18` to `14` and `CMG_FLYWHEEL_PIN` from `19` to `13`; update the `── Hardware Pins` section comment to reflect SPI instead of I2C

**Checkpoint**: `config.h` now defines SPI pins on GPIO 18/19/23/5 and actuator pins on GPIO 14/13. No GPIO overlap exists.

---

## Phase 2: Foundational — Sensor Header Update

**Purpose**: Update `imu.h` with the corrected MPU6500 identity value, gyroscope sensitivity constant, and cleaned-up comments. `imu.cpp` includes this header, so it must be correct before the driver rewrite begins.

- [x] T002 [P] Update `firmware/include/imu.h` — remove the `// ─── MPU9250 I2C Address ──` block and the `MPU9250_I2C_ADDR 0x68` define entirely (no I2C address needed for SPI); change `MPU_WHO_AM_I_VAL` from `0x71` to `0x70` (MPU6500 identity); change `GYRO_LSB_PER_DPS` from `16.384f` to `131.0f` (GFS_SEL=0, ±250 dps); update the file header comment from "MPU9250 IMU Driver" to "MPU6500 IMU Driver"; update the register config comment block to show `GYRO_CONFIG (0x1B) = 0x00  ±250°/s`; update all docstring references from "MPU9250" / "I2C" to "MPU6500" / "SPI" in the function documentation

**Checkpoint**: `imu.h` exports the correct `MPU_WHO_AM_I_VAL=0x70` and `GYRO_LSB_PER_DPS=131.0f`. Foundation ready for driver rewrite.

---

## Phase 3: User Story 1 — MPU6500 SPI Sensor Integration & Pin-Safe Actuation (Priority: P1) 🎯

**Goal**: Replace the I2C IMU driver with an SPI driver targeting the MPU6500, enforce ±250 dps gyroscope sensitivity, and update all cross-file comments/strings so no "6050" or legacy chip references remain anywhere in the firmware.

**Independent Test**: Flash the updated firmware, open Serial Monitor at 115200 baud, and confirm:
1. `[IMU] WHO_AM_I OK (0x70 — MPU6500 detected)` appears at boot
2. Calibration completes with gyro values bounded within ±250 °/s
3. `[CMG] Initialized. Gimbal GPIO14 (ch0), Flywheel GPIO13 (ch1)` appears in the boot log
4. No `Wire.h`-related linker symbols appear in the build output
5. Grep of `firmware/src/` and `firmware/include/` returns zero matches for "6050", "MPU-9250", "MPU-6050", "Wire.h"

### Implementation

- [x] T003 [US1] In `firmware/src/imu.cpp`: replace `#include <Wire.h>` with `#include <SPI.h>` at the top of the file; add a file-scoped static `static SPIClass spi_bus(VSPI);` declaration immediately after the includes; update the file header comment from "MPU9250 IMU Driver Implementation" to "MPU6500 IMU Driver Implementation"; remove the "Feature: 025-imu-kalman-fusion" comment line (or update to 042)

- [x] T004 [US1] In `firmware/src/imu.cpp`: rewrite the `mpu_write()` static helper — remove all `Wire.beginTransmission()`, `Wire.write()`, `Wire.endTransmission()` calls; replace with: `spi_bus.beginTransaction(SPISettings(MPU6500_SPI_FREQ, MSBFIRST, SPI_MODE3))`, `digitalWrite(MPU6500_SPI_CS, LOW)`, `spi_bus.transfer(reg & 0x7F)` (write bit: MSB=0), `spi_bus.transfer(value)`, `digitalWrite(MPU6500_SPI_CS, HIGH)`, `spi_bus.endTransaction()`

- [x] T005 [US1] In `firmware/src/imu.cpp`: rewrite the `mpu_read()` static helper — remove all Wire calls; replace with: `spi_bus.beginTransaction(SPISettings(MPU6500_SPI_FREQ, MSBFIRST, SPI_MODE3))`, `digitalWrite(MPU6500_SPI_CS, LOW)`, `spi_bus.transfer(0x80 | reg)` (read bit: MSB=1), `uint8_t val = spi_bus.transfer(0x00)` (dummy write to clock in data), `digitalWrite(MPU6500_SPI_CS, HIGH)`, `spi_bus.endTransaction()`, `return val`; update the `return Wire.available() ? Wire.read() : 0xFF` fallback to just `return val`

- [x] T006 [US1] In `firmware/src/imu.cpp`, rewrite `imu_init()` — replace `Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ_HZ)` with `pinMode(MPU6500_SPI_CS, OUTPUT)`, `digitalWrite(MPU6500_SPI_CS, HIGH)`, `spi_bus.begin(MPU6500_SPI_SCK, MPU6500_SPI_MISO, MPU6500_SPI_MOSI, MPU6500_SPI_CS)`; update the WHO_AM_I check: remove the `whoami != 0x68` fallback condition so only `whoami != MPU_WHO_AM_I_VAL` (i.e. `!= 0x70`) triggers the error; update the error message from "expected 0x71 or 0x68. Check I2C wiring." to "expected 0x70 for MPU6500. Check SPI wiring."; remove the `chip` variable and the "MPU-6050" / "MPU-9250" ternary detection string; replace the success log with `[IMU] WHO_AM_I OK (0x70 — MPU6500 detected)`; update the comment about magnetometer from "Magnetometer disabled (AK8963 isolated — zero latency impact)" to "Magnetometer not present (MPU6500 is accel/gyro only)"

- [x] T007 [US1] In `firmware/src/imu.cpp`, update `imu_configure()` — change the `mpu_write(MPU_REG_GYRO_CONFIG, 0x18)` line to `mpu_write(MPU_REG_GYRO_CONFIG, 0x00)`; update the inline comment from `GFS_SEL=3: ±2000°/s; FCHOICE_B=00` to `GFS_SEL=0: ±250°/s; FCHOICE_B=00`; update the function header comment block to reflect the new GYRO_CONFIG value

- [x] T008 [US1] In `firmware/src/imu.cpp`, rewrite the 14-byte burst read inside `calibrate_imu()` — remove the three Wire calls (`Wire.beginTransmission(MPU9250_I2C_ADDR)`, `Wire.write(MPU_REG_ACCEL_XOUT_H)`, `Wire.endTransmission(false)`, `Wire.requestFrom(MPU9250_I2C_ADDR, (uint8_t)14)`, and the `Wire.available()` read loop); replace with: `spi_bus.beginTransaction(SPISettings(MPU6500_SPI_FREQ, MSBFIRST, SPI_MODE3))`, `digitalWrite(MPU6500_SPI_CS, LOW)`, `spi_bus.transfer(0x80 | MPU_REG_ACCEL_XOUT_H)` (= `0xBB`), then a 14-iteration loop `buf[b] = spi_bus.transfer(0x00)`, followed by `digitalWrite(MPU6500_SPI_CS, HIGH)`, `spi_bus.endTransaction()`

- [x] T009 [US1] In `firmware/src/imu.cpp`, rewrite the 14-byte burst read inside `read_raw_sample()` — remove all Wire calls (`Wire.beginTransmission`, `Wire.write`, `Wire.endTransmission(false)` with its error check, `Wire.requestFrom`, and the `Wire.read()` loop); replace with the same SPI burst pattern as T008; replace the I2C NACK error message `"[IMU] I2C error on read (code %d)\n"` with `"[IMU] SPI CS assert failed\n"` (or simply remove since SPI CS failures are silent); replace `"[IMU] I2C NACK — fewer than 14 bytes received"` with `"[IMU] SPI burst read incomplete"` and check that `received` count is removed (SPI always delivers exactly the bytes clocked)

- [x] T010 [P] [US1] Update `firmware/src/main.cpp` — change the pipeline comment on line 9 from `MPU9250 init → calibration → battery init` to `MPU6500 init → calibration → battery init`; change the boot sequence comment item 2 from `IMU init (I2C, WHO_AM_I, register config, magnetometer disabled)` to `IMU init (SPI, WHO_AM_I, register config — no magnetometer)`; change the `Serial.println` on line 93 from `"[BOOT] CMG initialized (GPIO18 gimbal, GPIO19 flywheel, 50Hz 16-bit)."` to `"[BOOT] CMG initialized (GPIO14 gimbal, GPIO13 flywheel, 50Hz 16-bit)."`

- [x] T011 [P] [US1] Update `firmware/platformio.ini` — add `042-mpu6500-firmware-upgrade  MPU6500 SPI sensor, GPIO13/14 actuator pin reassignment` to the features comment block at the top of the file alongside the existing 025/030/031 feature entries

**Checkpoint**: At this point, US1 is fully implemented. Flash and verify via Serial Monitor using the independent test criteria above.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final verification that no legacy string references remain and no GPIO conflicts exist.

- [x] T012 [P] String audit — run `grep -r "6050\|MPU-9250\|MPU-6050\|MPU9250\|Wire\.h\|MPU9250_I2C" firmware/src firmware/include` from the repository root and confirm zero matches; if any match is found, locate the file and fix the remaining reference

- [x] T013 [P] GPIO pin audit — open `firmware/include/config.h` and confirm: `MPU6500_SPI_SCK`, `MPU6500_SPI_MISO`, `MPU6500_SPI_MOSI`, `MPU6500_SPI_CS` are all set to values ≠ 13 and ≠ 14; confirm `CMG_GIMBAL_PIN=14` and `CMG_FLYWHEEL_PIN=13`; confirm `I2C_SDA_PIN` and `I2C_SCL_PIN` no longer exist in the file

- [x] T014 Build firmware — run `pio run -e esp32dev` inside `firmware/` and confirm zero compilation errors and zero "Wire" or "MPU9250_I2C" undefined-symbol warnings in the build output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Can run in parallel with Phase 1 (T002 does not include config.h)
- **US1 (Phase 3)**: MUST wait for T001 (config.h) and T002 (imu.h) to complete before T003 begins
  - T003 → T004 → T005 → T006 → T007 → T008 → T009 sequential (same file)
  - T010 and T011 are [P] — can run alongside any of T003–T009
- **Polish (Phase 4)**: T012 and T013 require all Phase 3 tasks complete; T014 requires T012 + T013

### Within US1

```
T001 ──┬──> T003 → T004 → T005 → T006 → T007 → T008 → T009
T002 ──┘                                                     ──> T012
                                                             ──> T013 ──> T014
T010 (parallel with T003–T009, different file)
T011 (parallel with T003–T011, different file)
```

---

## Parallel Opportunities

```bash
# Phase 1 & 2 can run simultaneously:
Task T001: Update firmware/include/config.h (SPI pins + actuator pin reassignment)
Task T002: Update firmware/include/imu.h (WHO_AM_I, GYRO_LSB, comments)

# While rewriting imu.cpp (T003–T009), these can run in parallel:
Task T010: Update firmware/src/main.cpp (comment/string updates only)
Task T011: Update firmware/platformio.ini (feature comment)

# Polish tasks run in parallel with each other:
Task T012: String audit (grep)
Task T013: GPIO pin audit (config.h review)
# Then T014 (build) after both T012 and T013 pass
```

---

## Implementation Strategy

### MVP: Single Story — Complete US1

1. Complete T001 + T002 in parallel (Phase 1 + 2)
2. Complete T003 → T009 sequentially in `imu.cpp`
3. Complete T010 + T011 in parallel (can overlap with step 2)
4. **STOP and VALIDATE**: Flash firmware, check Serial Monitor for `WHO_AM_I OK (0x70 — MPU6500 detected)`
5. Run T012 + T013 audit tasks
6. Run T014 build verification
7. **Done** — single story, single delivery

---

## Notes

- `cmg.cpp` requires **zero changes** — it reads `CMG_GIMBAL_PIN` and `CMG_FLYWHEEL_PIN` directly from `config.h`
- `Wire.h` must be completely removed from `imu.cpp`; it is not used anywhere else in the firmware
- The 14-byte burst read byte layout (accel → temp → gyro) is **identical** over SPI and I2C — only the transport layer changes
- SPI CS must be explicitly driven HIGH before `spi_bus.begin()` is called, otherwise the sensor may latch an incorrect transaction on boot
- `SPISettings(MPU6500_SPI_FREQ, MSBFIRST, SPI_MODE3)` is the correct mode — any other SPI mode will produce garbage reads
