# Tasks: Fix CMG Flywheel Startup Stall Using a Validated Brushless-Motor Sequence

**Input**: Design documents from `/specs/050-rework-flywheel-startup/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅
**Tests**: Not requested — no automated firmware test harness exists in this repo; validation is the manual bench testing in quickstart.md.
**Scope**: Firmware-only. 4 files modified (`firmware/platformio.ini`, `firmware/include/config.h`, `firmware/include/cmg.h`, `firmware/src/cmg.cpp`), 0 new files. No backend/frontend/database changes. `firmware/src/main.cpp` is NOT modified — the `bool cmg_init()` contract and `fault_halt()` helper added by `049-fix-esc-flywheel-stall` are reused as-is.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US1]**: User Story 1 — Reliable Flywheel Startup Using a Sequence Already Proven on This Hardware (P1, MVP)
- **[US2]**: User Story 2 — Flywheel Fix Must Not Disturb the Production Gimbal Servo Path (P1)
- **[US3]**: User Story 3 — Visible Fault Detection and Bounded Recovery Remain in Place (P2)
- All paths are relative to the repository root

US1's single rewrite of `cmg_init()`/`cmg_set_gimbal()` necessarily converts **both** the flywheel and gimbal channels to the `ESP32Servo` library together (research.md §1: mixing `ESP32Servo`'s auto-allocated channels with a manually-attached raw-LEDC gimbal channel risks a silent channel collision — converting only the flywheel is not a safe intermediate state). Because of this, US2 and US3 are not separate code edits layered on top of US1; they are independent **verification** stories that audit the US1 rewrite against their own guarantee (gimbal control path unchanged; retry/fault-detection contract preserved) and are independently bench-testable per their own quickstart section even though the underlying file edit happened once.

---

## Phase 1: Setup — New Library Dependency

**Purpose**: Make the `ESP32Servo` library available to the build before any code references it.

- [X] T001 [P] In `firmware/platformio.ini`: add `madhephaestus/ESP32Servo` as a new line under the existing `lib_deps =` block (after `https://github.com/256dpi/arduino-mqtt.git#v2.5.0`), with no version pin (let PlatformIO resolve the latest registry release on first build — pin a specific version afterward only if reproducibility becomes an issue). Result:
  ```ini
  lib_deps =
      bblanchon/ArduinoJson @ ^6.21.5
      https://github.com/256dpi/arduino-mqtt.git#v2.5.0
      madhephaestus/ESP32Servo
  ```

**Checkpoint**: `platformio.ini` declares the `ESP32Servo` dependency.

---

## Phase 2: Foundational — Corrected Actuation Constants

**Purpose**: Replace the raw-LEDC-era config constants with the ones the `ESP32Servo`-based `cmg.cpp` rewrite (Phase 3) depends on. Every user story's code change depends on this block existing first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 In `firmware/include/config.h`: replace the entire `─── CMG Actuation ───` block (from the `// ─── CMG Actuation ───...` comment line through the `#define CMG_ESC_MAX_ATTEMPTS 3 ...` line) with:
  ```c
  // ─── CMG Actuation ────────────────────────────────────────────────────────────
  // Uses the ESP32Servo library (Servo class) for both PWM outputs — replaces the
  // raw channel-based LEDC API (ledcSetup/ledcAttachPin/ledcWrite). Matches the
  // sequence validated to reliably start this exact ESC/motor/flywheel combination
  // on a standalone bench-test program (run_zizo.cpp); see
  // specs/050-rework-flywheel-startup/research.md.
  // GPIO12 and GPIO14 are exclusively reserved for actuators — never assign SPI here.
  #define CMG_GIMBAL_PIN              12      // GPIO12 — gimbal servo signal
  #define CMG_FLYWHEEL_PIN            14      // GPIO14 — flywheel ESC signal
  #define CMG_GIMBAL_ATTACH_MIN_US   500      // µs — gimbalServo.attach() floor (matches validated reference's stabilizerServo range)
  #define CMG_GIMBAL_ATTACH_MAX_US  2500      // µs — gimbalServo.attach() ceiling
  #define CMG_ESC_ATTACH_MIN_US     1000      // µs — flywheelMotor.attach() floor (matches validated reference's brushlessMotor range)
  #define CMG_ESC_ATTACH_MAX_US     2000      // µs — flywheelMotor.attach() ceiling
  #define CMG_GIMBAL_MAX_DEG       60.0f      // ±60° gimbal range (avoid gimbal lock at ±90°)
  #define CMG_FLYWHEEL_IDLE_US      1080      // µs constant flywheel running pulse — small step above CMG_ESC_ARM_PULSE_US, matching the validated reference; raise in small increments (re-validate via quickstart.md §1-2) if more counter-torque is needed

  #define CMG_ESC_ARM_MS            5000      // ms to hold the arm pulse (CMG_ESC_ARM_PULSE_US) before commanding CMG_FLYWHEEL_IDLE_US
  #define CMG_ESC_ARM_PULSE_US      1000      // µs arm/idle pulse — standard ESC zero-throttle signal, matching the validated reference sequence
  #define CMG_ESC_SETTLE_MS         1500      // ms to wait after commanding CMG_FLYWHEEL_IDLE_US before checking for a successful spin-up
  #define CMG_ESC_VOLTAGE_SAG_MV      20      // min. battery-ADC mV drop across the settle window taken as evidence of genuine spin-up current draw (heuristic — lowered from 80; the smaller arm→run step now draws less current; re-tune on bench, see quickstart.md §4)
  #define CMG_ESC_MAX_ATTEMPTS         3      // total arm/spin-up attempts (1 initial + 2 retries) before latching a fault
  ```
  This removes `CMG_GIMBAL_CHANNEL`, `CMG_FLYWHEEL_CHANNEL`, `CMG_PWM_FREQ_HZ`, `CMG_PWM_RESOLUTION`, and `CMG_FLYWHEEL_DUTY` (all dead once `cmg.cpp` no longer uses the raw LEDC API), adds the four new `_ATTACH_` range constants, and changes `CMG_ESC_ARM_PULSE_US` (900→1000), `CMG_FLYWHEEL_IDLE_US` (1600→1080), and `CMG_ESC_VOLTAGE_SAG_MV` (80→20).

**Checkpoint**: `config.h` defines the `ESP32Servo`-era constants; no code yet references them (compiles only after Phase 3).

---

## Phase 3: User Story 1 - Reliable Flywheel Startup Using a Sequence Already Proven on This Hardware (Priority: P1) 🎯 MVP

**Goal**: Replace `cmg_init()`'s flywheel arm/run sequence with the one validated in `run_zizo.cpp` (1000µs arm → small step to 1080µs running, via `ESP32Servo`), keeping the existing bounded-retry/voltage-sag wrapper intact around the corrected inner sequence. The gimbal channel is converted to `ESP32Servo` in the same edit, since `research.md` §1 establishes that converting only the flywheel channel risks a PWM-channel collision with the gimbal's manually-attached raw LEDC channel.

**Independent Test**: Flash, power-cycle 20 consecutive times, and confirm via Serial Monitor + physical observation that the flywheel reaches and sustains operating speed every time with no fault-beep pattern (quickstart.md §1).

### Implementation

- [X] T003 [US1] In `firmware/src/cmg.cpp` (depends on T001, T002): replace the entire file contents with:
  ```cpp
  /**
   * cmg.cpp — Control Moment Gyroscope (CMG) Actuation Implementation
   *
   * Feature: 031-freertos-scheduler
   * Feature: 050-rework-flywheel-startup (ESP32Servo-based actuation, validated arm/run sequence)
   *
   * Two ESP32Servo Servo objects, matching the sequence validated on a standalone
   * bench-test program (run_zizo.cpp) wired to the same GPIO/SPI pins as production:
   *   gimbalServo    (GPIO CMG_GIMBAL_PIN):    Gimbal servo (PID-driven)
   *   flywheelMotor  (GPIO CMG_FLYWHEEL_PIN):  Flywheel ESC (constant speed)
   *
   * Both channels moved off the raw channel-based LEDC API (ledcSetup/ledcAttachPin/
   * ledcWrite) to ESP32Servo's Servo class: ESP32Servo manages its own internal
   * channel/timer allocation, and mixing it with a manually-attached raw LEDC channel
   * risks a silent channel collision (see specs/050-rework-flywheel-startup/research.md §1).
   */

  #include "cmg.h"
  #include "config.h"
  #include <Arduino.h>
  #include <ESP32Servo.h>

  static Servo gimbalServo;
  static Servo flywheelMotor;

  bool cmg_init() {
      // --- Gimbal servo (GPIO CMG_GIMBAL_PIN) ---
      gimbalServo.attach(CMG_GIMBAL_PIN, CMG_GIMBAL_ATTACH_MIN_US, CMG_GIMBAL_ATTACH_MAX_US);
      // Center gimbal at 1500µs
      gimbalServo.writeMicroseconds(1500);

      // --- Flywheel ESC ---
      flywheelMotor.attach(CMG_FLYWHEEL_PIN, CMG_ESC_ATTACH_MIN_US, CMG_ESC_ATTACH_MAX_US);

      for (int attempt = 1; attempt <= CMG_ESC_MAX_ATTEMPTS; attempt++) {
          // 1. Arm ESC: Hold CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS (5 seconds)
          // Standard 1000µs zero-throttle signal — matches the sequence validated to
          // arm this ESC cleanly without the pre-start fault-beep (Phase 1).
          flywheelMotor.writeMicroseconds(CMG_ESC_ARM_PULSE_US);
          delay(CMG_ESC_ARM_MS);

          // 2. Command running speed: a small step above the arm pulse (not a large
          // jump) — matches the validated reference, letting the ESC's own closed-loop
          // startup algorithm hand off from forced commutation without desyncing
          // against the flywheel's high rotational inertia (Phase 2).
          uint32_t v_before_mv = analogReadMilliVolts(BATTERY_ADC_PIN);
          flywheelMotor.writeMicroseconds(CMG_FLYWHEEL_IDLE_US);

          // 3. Verify: a genuine spin-up draws a sustained current — look for the
          // resulting battery-voltage sag as a best-effort confirmation signal
          // (no RPM/current telemetry is wired; battery_init() already ran before
          // cmg_init(), so the ADC attenuation is already configured here).
          delay(CMG_ESC_SETTLE_MS);
          uint32_t v_after_mv = analogReadMilliVolts(BATTERY_ADC_PIN);
          uint32_t sag_mv = (v_before_mv > v_after_mv) ? (v_before_mv - v_after_mv) : 0;
          if (sag_mv < CMG_ESC_VOLTAGE_SAG_MV) {
              Serial.printf("[CMG] WARNING flywheel startup attempt %d/%d not confirmed (sag=%lumV) — retrying.\n",
                            attempt, CMG_ESC_MAX_ATTEMPTS, (unsigned long)sag_mv);
              continue;
          }

          Serial.printf("[CMG] Flywheel startup confirmed (sag=%lumV).\n", (unsigned long)sag_mv);
          Serial.printf("[CMG] ESP32Servo CMG Initialized. Gimbal (GPIO%d), Flywheel (GPIO%d)\n",
                        CMG_GIMBAL_PIN, CMG_FLYWHEEL_PIN);
          return true;
      }

      Serial.printf("[FAULT] CMG flywheel startup failed after %d attempts.\n", CMG_ESC_MAX_ATTEMPTS);
      return false;
  }

  void cmg_set_gimbal(float output_normalized) {
      // Clamp to [-1.0, +1.0] before angle conversion
      if (output_normalized > 1.0f)  output_normalized = 1.0f;
      if (output_normalized < -1.0f) output_normalized = -1.0f;

      // Map normalized output to gimbal angle: [-1.0, +1.0] -> [+-CMG_GIMBAL_MAX_DEG]
      float angle_deg = output_normalized * CMG_GIMBAL_MAX_DEG;

      // Map angle to pulse width:
      //   center = 1500us, full range = +-1000us across +-CMG_GIMBAL_MAX_DEG
      uint32_t pulse_us = (uint32_t)(1500.0f + angle_deg * (1000.0f / CMG_GIMBAL_MAX_DEG));

      // Clamp to servo-safe range (standard RC hobby range at +-60 deg)
      if (pulse_us > 2167) pulse_us = 2167;
      if (pulse_us < 833)  pulse_us = 833;

      gimbalServo.writeMicroseconds(pulse_us);
  }
  ```
  Note that `cmg_set_gimbal()`'s clamps, angle mapping, and pulse-width formula are byte-for-byte unchanged from the prior raw-LEDC version — only the final write call changes (`ledcWrite(channel, duty)` → `gimbalServo.writeMicroseconds(pulse_us)`), preserving its external behavior exactly (this is what US2 audits).

- [X] T004 [US1] In `firmware/include/cmg.h` (depends on T002, T003): replace the entire file contents with:
  ```cpp
  /**
   * cmg.h — Control Moment Gyroscope (CMG) Actuation Interface
   *
   * Feature: 031-freertos-scheduler
   * Feature: 050-rework-flywheel-startup (ESP32Servo-based actuation, validated arm/run sequence)
   *
   * Drives two ESP32Servo Servo objects:
   *   Gimbal servo   (GPIO CMG_GIMBAL_PIN):
   *     Angle driven by PID output every 5ms (200Hz).
   *     Pulse range: 833–2167 µs (±CMG_GIMBAL_MAX_DEG = ±60°), center (0°) = 1500 µs.
   *     Servo.attach() range: CMG_GIMBAL_ATTACH_MIN_US–CMG_GIMBAL_ATTACH_MAX_US (wider than
   *     the code-level clamp above, matching the validated reference's attach() call).
   *
   *   Flywheel ESC   (GPIO CMG_FLYWHEEL_PIN):
   *     Constant throttle set once at startup via a validated arm-then-run sequence:
   *     arms at CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS, then commands CMG_FLYWHEEL_IDLE_US
   *     directly — a small step above the arm pulse, not a large jump or software ramp.
   *     Retries up to CMG_ESC_MAX_ATTEMPTS times if startup isn't confirmed (see cmg_init()).
   *
   * Note: this replaces the previous raw channel-based LEDC API (ledcSetup/ledcAttachPin/
   * ledcWrite) with the ESP32Servo library, matching the sequence validated on a standalone
   * bench-test program wired to the same pins (specs/050-rework-flywheel-startup/research.md).
   */

  #pragma once

  /**
   * cmg_init() — Initialize the gimbal servo and flywheel ESC via ESP32Servo.
   *
   * - Attaches gimbalServo to CMG_GIMBAL_PIN (range CMG_GIMBAL_ATTACH_MIN_US–CMG_GIMBAL_ATTACH_MAX_US)
   *   and centers it at 1500 µs.
   * - Attaches flywheelMotor to CMG_FLYWHEEL_PIN (range CMG_ESC_ATTACH_MIN_US–CMG_ESC_ATTACH_MAX_US).
   * - Arms flywheel ESC: holds CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS (normal ESC behavior),
   *   then commands CMG_FLYWHEEL_IDLE_US directly — a small step above the arm pulse, matching
   *   the validated reference sequence (no large jump, no software ramp).
   *
   * Call once in setup() before scheduler_start().
   * The 5-second arming delay is expected — do not skip it.
   *
   * Samples battery voltage immediately before and CMG_ESC_SETTLE_MS after the
   * running-speed command; if the expected current-draw sag isn't observed, the
   * attempt is considered failed. Retries the full arm-and-spin-up sequence
   * up to CMG_ESC_MAX_ATTEMPTS times before giving up.
   *
   * @return true if startup was confirmed via the voltage-sag check within CMG_ESC_MAX_ATTEMPTS tries; false if every attempt failed (caller must treat as a fault).
   */
  bool cmg_init();

  /**
   * cmg_set_gimbal() — Set gimbal servo position from normalized PID output.
   *
   * @param output_normalized  PID output in range [-1.0, +1.0]
   *   Clamped to [-1.0, +1.0] before conversion.
   *   Maps to gimbal angle [±CMG_GIMBAL_MAX_DEG degrees].
   *   Maps to servo pulse [833–2167 µs], written via Servo::writeMicroseconds().
   *
   * Called from ControlTask at 200Hz. Unchanged production PID/sensor-fusion/task-scheduling
   * control path — only the underlying pulse-write primitive uses ESP32Servo now.
   */
  void cmg_set_gimbal(float output_normalized);
  ```

**Checkpoint**: User Story 1 is fully implemented and independently testable — flash and run quickstart.md §1 (and §2 to start gauging whether `CMG_FLYWHEEL_IDLE_US` needs raising).

---

## Phase 4: User Story 2 - Flywheel Fix Must Not Disturb the Production Gimbal Servo Path (Priority: P1)

**Goal**: Confirm the T003 rewrite did not alter, simplify, or regress the production gimbal control path (sensor fusion → PID → task scheduler → `cmg_set_gimbal()`), and that none of `run_zizo.cpp`'s simplified single-axis servo-stabilization logic was ported in.

**Independent Test**: After T003 is applied, induce a simulated tremor input on the bench rig and verify the gimbal servo's response is still produced exclusively by the existing production sensor-fusion + PID + task-scheduling pipeline, with no change in behavior, responsiveness, or accuracy compared to before this fix (quickstart.md §3).

### Implementation

- [X] T005 [P] [US2] Audit (depends on T003): run `grep -rn "writeMicroseconds\|attach(" firmware/src/cmg.cpp` and confirm `cmg_set_gimbal()`'s only behavioral change from the pre-`050` version is the final call (`gimbalServo.writeMicroseconds(pulse_us)` replacing `ledcWrite(CMG_GIMBAL_CHANNEL, duty)`) — the clamp values (833/2167), the angle-mapping formula, and the function signature must be identical to the version read at the start of this feature. Separately, run `git diff --stat -- firmware/src/pid_controller.cpp firmware/src/task_scheduler.cpp firmware/include/pid_controller.h firmware/include/task_scheduler.h firmware/src/main.cpp` against the base of this branch and confirm zero changes — these files must not be touched by this feature (FR-011). Record both confirmations in the completion report for this feature.

**Checkpoint**: User Stories 1 AND 2 both verified — run quickstart.md §1 and §3.

---

## Phase 5: User Story 3 - Visible Fault Detection and Bounded Recovery Remain in Place (Priority: P2)

**Goal**: Confirm the bounded-retry / distinguishable-fault-state contract from `049-fix-esc-flywheel-stall` (FR-004, FR-008, FR-009) survived the T003 rewrite intact, now wrapped around the corrected sequence instead of the old one.

**Independent Test**: Deliberately induce a stall (e.g., briefly hold the flywheel shaft stationary during the running-pulse/settle window) and confirm Serial reports a distinct "CMG flywheel startup failed" message; separately confirm transient stalls auto-recover and persistent stalls latch a fault rather than retrying forever (quickstart.md §4, §5).

### Implementation

- [X] T006 [P] [US3] Audit (depends on T003): run `grep -n "for (int attempt = 1; attempt <= CMG_ESC_MAX_ATTEMPTS" firmware/src/cmg.cpp` and confirm the bounded retry loop is present (not flattened to a single attempt during the T003 rewrite); run `grep -n "FAULT.*CMG flywheel startup failed" firmware/src/cmg.cpp` and confirm the post-loop fault message is present; confirm `main.cpp`'s `if (!cmg_init()) { fault_halt("[FAULT] CMG flywheel startup failed. Halting.", 100); }` call site (added by `049`) is unchanged (covered by T005's `main.cpp` diff check). Record confirmation in the completion report for this feature.

**Checkpoint**: All three user stories verified — run quickstart.md §1 through §5.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm no dead LEDC-era code/config remains, the firmware builds clean with the new dependency, and the full bench validation passes.

- [X] T007 [P] Dead-API audit — run `grep -rn "ledcSetup\|ledcAttachPin\|ledcWrite\|CMG_FLYWHEEL_DUTY\|CMG_PWM_FREQ_HZ\|CMG_PWM_RESOLUTION\|CMG_GIMBAL_CHANNEL\|CMG_FLYWHEEL_CHANNEL" firmware/src firmware/include` from the repository root and confirm zero matches (the raw LEDC API and its associated constants must be fully retired from this feature's scope).

- [X] T008 [P] Build firmware — run `pio run -e esp32dev` and `pio run -e esp32dev-debug` inside `firmware/` and confirm zero compilation errors (the `ESP32Servo` dependency resolves, and the rewritten `cmg.cpp`/`cmg.h` compile cleanly against it).

- [ ] T009 Run the full quickstart.md validation (§1–§5) on real hardware and record results against its Pass/Fail summary table, including the `CMG_FLYWHEEL_IDLE_US` bench-tuning check in §2. **(Not run by the agent — requires physical hardware in hand; see completion report.)**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: No dependency on Phase 1 (different file: `config.h` vs `platformio.ini`) — can run in parallel with it, but BLOCKS all user stories (T003 needs the new constants to compile).
- **User Stories (Phase 3-5)**: T003/T004 (US1) depend on T001 + T002. T005 (US2) and T006 (US3) are read-only audits that depend on T003 existing (they verify its output) but not on each other — they can run in parallel once T003 lands.
- **Polish (Phase 6)**: T007/T008 depend on T003/T004 (auditing/building the final code); T009 depends on all of Phase 3-5 being complete.

### Within Each File

- `platformio.ini`: T001 only.
- `config.h`: T002 only.
- `cmg.h`: T004 only (single full-file rewrite).
- `cmg.cpp`: T003 only (single full-file rewrite) — T005/T006 read it but don't modify it further.

```
T001 ──┐
       ├──> T003 ──> T004 ──┬──> T005 ──┬──> T007 ──┐
T002 ──┘                    └──> T006 ──┘           ├──> T009
                                          T008 ──────┘
```

### Parallel Opportunities

- T001 and T002 (different files: `platformio.ini` vs `config.h`) can run in parallel at the very start.
- T005 and T006 (independent read-only audits, no file writes) can run in parallel once T003/T004 land.
- T007 and T008 (independent: a grep audit and a build) can run in parallel with each other.

---

## Parallel Example: Setup + Foundational

```bash
# T001 and T002 touch different files and have no dependency on each other:
Task: "Add ESP32Servo to lib_deps in firmware/platformio.ini"
Task: "Rewrite CMG Actuation constants block in firmware/include/config.h"
```

## Parallel Example: Verification Stories

```bash
# T005 and T006 are both read-only audits of the same T003/T004 rewrite:
Task: "Audit gimbal control path is unchanged (US2) — grep + git diff check"
Task: "Audit retry/fault-detection contract survived (US3) — grep check"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (US1).
3. **STOP and VALIDATE**: run quickstart.md §1 — 20 consecutive power-on cycles, zero fault cutoffs.
4. This alone delivers the core fix: a flywheel startup sequence matching the one already proven to work on this exact hardware.

### Incremental Delivery

1. Setup + Foundational → new dependency and constants ready.
2. Add US1 → validate independently (quickstart §1, §2) → this is the MVP.
3. Verify US2 → audit + bench-confirm the gimbal path is untouched (quickstart §3).
4. Verify US3 → audit + bench-confirm fault detection/retry still works on the corrected sequence (quickstart §4, §5).
5. Polish → dead-API grep audit + build + full quickstart re-run.

---

## Notes

- There is no automated firmware test suite in this repo (`firmware/test/` does not exist) — every checkpoint above is a manual bench-test step against the real ESC + 2200KV motor + 35g aluminum flywheel, per quickstart.md.
- Unlike `049-fix-esc-flywheel-stall` (which built the arm/detect/retry mechanism up from nothing across three sequential code layers), this feature modifies an existing implementation: the single T003 rewrite necessarily touches the whole `cmg_init()`/`cmg_set_gimbal()` body, so US2 and US3 are verification stories over that one edit rather than separate incremental code layers.
- `CMG_FLYWHEEL_IDLE_US` (T002) is intentionally lowered to match the validated reference as a starting point, not a final tuned value — quickstart.md §2 covers raising it in small increments if bench testing shows insufficient counter-torque, re-validating with the full 20-cycle test after each change.
- `CMG_ESC_VOLTAGE_SAG_MV` (T002) is an explicitly best-effort heuristic, now re-baselined to 20mV for the smaller running-pulse step — if bench testing shows it doesn't reliably distinguish success from failure, the threshold value is the first thing to retune (quickstart.md §4).
- This feature does not add any new FreeRTOS task or touch `task_scheduler.cpp`/`main.cpp` — the whole sequence remains a bounded, blocking routine inside `cmg_init()`, called once from `setup()` before the scheduler starts.
