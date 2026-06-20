# Tasks: Fix CMG Flywheel ESC Arming and Stall Failure

**Input**: Design documents from `/specs/049-fix-esc-flywheel-stall/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅
**Tests**: Not requested — no automated firmware test harness exists in this repo; validation is the manual bench testing in quickstart.md.
**Scope**: Firmware-only. 4 files modified (`firmware/include/config.h`, `firmware/include/cmg.h`, `firmware/src/cmg.cpp`, `firmware/src/main.cpp`), 0 new files. No backend/frontend/database changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US1]**: User Story 1 — Reliable Flywheel Startup for Therapy Delivery (P1)
- **[US2]**: User Story 2 — Visible Fault Detection When Startup Fails (P2)
- **[US3]**: User Story 3 — Automatic Recovery Without a Full Power Cycle (P3)
- All paths are relative to the repository root

The three stories are designed as incremental layers over the same `cmg_init()` flow (see data-model.md): US1 lands the arm/throttle fix alone (the part already validated empirically on the bench), US2 adds failure *detection* on top of it, US3 wraps that detection in a bounded retry loop. Each story is a complete, independently flashable/testable increment.

---

## Phase 1: Setup — Config Constants

**Purpose**: Establish the arm-pulse constant every story's code depends on, and remove the now-dead ramp constants.

- [X] T001 [P] In `firmware/include/config.h`: remove the `#define CMG_ESC_RAMP_STEPS 20` and `#define CMG_ESC_RAMP_STEP_MS 50` lines (the gradual ramp they drove was already removed from `cmg.cpp` — `grep -n CMG_ESC_RAMP firmware/src/cmg.cpp` currently returns no matches, confirming they're dead); add `#define CMG_ESC_ARM_PULSE_US  900    // µs arm/idle pulse — below the ESC's calibrated low-throttle threshold, clears the pre-start fault-beep` directly below the existing `#define CMG_ESC_ARM_MS 5000` line.

**Checkpoint**: `config.h` defines `CMG_ESC_ARM_PULSE_US` and no longer references the unused ramp constants.

---

## Phase 2: Foundational — Success/Failure Reporting Contract

**Purpose**: Give `cmg_init()` a way to report failure upward (it's currently `void` and cannot signal anything), and give `main.cpp` a reusable, parameterized fault-halt routine instead of one fault halt block hardcoded to the IMU/calibration case. Every later story needs this contract to exist; `cmg_init()` returns `true` unconditionally for now — no detection logic yet.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] In `firmware/include/cmg.h`: change the declaration `void cmg_init();` to `bool cmg_init();`; update its doc comment block to add `* @return true if the flywheel reached stable operating speed; false if the startup attempt failed (caller must halt).`

- [X] T003 In `firmware/src/cmg.cpp` (depends on T002): change `void cmg_init() {` to `bool cmg_init() {`; add `return true;` as the new last line of the function body, immediately after the existing `Serial.printf("[CMG] BLHeli ESC Initialized. ...")` call.

- [X] T004 In `firmware/src/main.cpp` (depends on T002, T003): extract the existing inline IMU/calibration fault-halt `while (true) { ... }` block (currently inside the `if (state == STATE_FAULT)` section of `setup()`) into a new static helper defined above `setup()`: `static void fault_halt(const char* serial_msg, int blink_ms) { Serial.println(serial_msg); if (FAULT_LED_PIN >= 0) pinMode(FAULT_LED_PIN, OUTPUT); while (true) { if (FAULT_LED_PIN >= 0) { digitalWrite(FAULT_LED_PIN, HIGH); delay(blink_ms); digitalWrite(FAULT_LED_PIN, LOW); delay(blink_ms); } else { delay(1000); } } }`; update the existing IMU-init-failure and calibration-failure call sites to call `fault_halt("[FAULT] IMU initialization failed. Halting.", 250);` and `fault_halt("[FAULT] Calibration failed (motion detected or IMU error). Halting.", 250);` respectively (preserving the existing messages and the existing 250ms blink cadence exactly); change the `cmg_init();` call to `if (!cmg_init()) { fault_halt("[FAULT] CMG flywheel startup failed. Halting.", 100); }` immediately after it — 100ms is a deliberately faster blink than the 250ms IMU/calibration fault, so the two are visually distinguishable (FR-004).

**Checkpoint**: Firmware builds with the new `bool cmg_init()` contract and a shared `fault_halt()` helper; behavior is unchanged (the CMG branch is unreachable since `cmg_init()` always returns `true` until US2).

---

## Phase 3: User Story 1 - Reliable Flywheel Startup for Therapy Delivery (Priority: P1) 🎯 MVP

**Goal**: The flywheel arms without the Phase 1 pre-start beep and reaches operating speed without the Phase 2 stall/cutout, using the already bench-validated low arm pulse and direct (no-ramp) throttle command — now expressed via a named constant instead of a magic number.

**Independent Test**: Flash, power-cycle 20 consecutive times, and confirm via Serial Monitor + physical observation that the flywheel reaches and sustains operating speed every time with no fault-beep pattern (quickstart.md §1).

### Implementation

- [X] T005 [US1] In `firmware/src/cmg.cpp` (depends on T001, T003): replace `ledcWrite(CMG_FLYWHEEL_CHANNEL, (900UL * 65536UL) / 20000UL);` with `ledcWrite(CMG_FLYWHEEL_CHANNEL, (CMG_ESC_ARM_PULSE_US * 65536UL) / 20000UL);`; update the comment directly above it from `// 1. Arm ESC: Hold 900µs for CMG_ESC_ARM_MS (5 seconds)` to `// 1. Arm ESC: Hold CMG_ESC_ARM_PULSE_US for CMG_ESC_ARM_MS (5 seconds)`.

- [X] T006 [P] [US1] In `firmware/include/cmg.h` (depends on T002): update `* Arms at 1000 µs (duty 3277) for 5 s, then ramps to CMG_FLYWHEEL_DUTY.` to `* Arms at CMG_ESC_ARM_PULSE_US (900 µs) for CMG_ESC_ARM_MS (5 s), then commands CMG_FLYWHEEL_DUTY directly — no software ramp.`; update `* - Arms flywheel ESC: holds 1000 µs for 5 seconds (normal ESC behavior),` / `*   then ramps to CMG_FLYWHEEL_DUTY (constant throttle).` to `* - Arms flywheel ESC: holds CMG_ESC_ARM_PULSE_US for 5 seconds (normal ESC behavior),` / `*   then commands CMG_FLYWHEEL_DUTY directly (no ramp — the ESC's own startup algorithm needs a clear target).`

- [X] T007 [US1] In `firmware/src/cmg.cpp` (depends on T005): update the file-header "Pulse-to-duty reference" comment block's line `*   1000 µs (ESC arm)     → duty = 3277` to `*    900 µs (ESC arm, CMG_ESC_ARM_PULSE_US) → duty = 2949`.

**Checkpoint**: At this point, User Story 1 is fully implemented and independently testable — flash and run quickstart.md §1.

---

## Phase 4: User Story 2 - Visible Fault Detection When Startup Fails (Priority: P2)

**Goal**: When a single startup attempt doesn't produce the current-draw signature of a successful spin-up, report a distinguishable fault via the existing `fault_halt()` mechanism instead of leaving the device silently non-functional.

**Independent Test**: Induce a stall (e.g., briefly hold the flywheel shaft stationary during the settle window) and confirm Serial reports a distinct "CMG flywheel startup failed" message with a 100ms blink cadence, distinguishable from an IMU/calibration fault (quickstart.md §2).

### Implementation

- [X] T008 [US2] In `firmware/include/config.h` (depends on T001): add directly below `CMG_ESC_ARM_PULSE_US`: `#define CMG_ESC_SETTLE_MS        1500   // ms to wait after commanding target throttle before checking for a successful spin-up` and `#define CMG_ESC_VOLTAGE_SAG_MV   80     // min. battery-ADC mV drop across the settle window taken as evidence of genuine spin-up current draw (heuristic — tune on bench if needed)`.

- [X] T009 [US2] In `firmware/src/cmg.cpp` (depends on T007, T008): immediately before `ledcWrite(CMG_FLYWHEEL_CHANNEL, CMG_FLYWHEEL_DUTY);`, add `uint32_t v_before_mv = analogReadMilliVolts(BATTERY_ADC_PIN);`; after that `ledcWrite` call, replace the trailing `Serial.printf("[CMG] BLHeli ESC Initialized. ...")` + `return true;` with: `delay(CMG_ESC_SETTLE_MS); uint32_t v_after_mv = analogReadMilliVolts(BATTERY_ADC_PIN); uint32_t sag_mv = (v_before_mv > v_after_mv) ? (v_before_mv - v_after_mv) : 0; if (sag_mv < CMG_ESC_VOLTAGE_SAG_MV) { Serial.printf("[CMG] WARNING flywheel startup sag=%lumV below %dmV threshold — startup not confirmed.\n", (unsigned long)sag_mv, CMG_ESC_VOLTAGE_SAG_MV); return false; } Serial.printf("[CMG] Flywheel startup confirmed (sag=%lumV).\n", (unsigned long)sag_mv); Serial.printf("[CMG] BLHeli ESC Initialized. Gimbal (ch%d), Flywheel (ch%d)\n", CMG_GIMBAL_CHANNEL, CMG_FLYWHEEL_CHANNEL); return true;`. (Reading `BATTERY_ADC_PIN` here is safe without calling `battery_init()` again — `main.cpp` already calls `battery_init()` before `cmg_init()`, so attenuation is already configured.)

- [X] T010 [P] [US2] In `firmware/include/cmg.h` (depends on T006, T009): in the `cmg_init()` doc comment, add a line documenting the new check: `* Samples battery voltage immediately before and CMG_ESC_SETTLE_MS after the startup command;` / `* if the expected current-draw sag isn't observed, the attempt is considered failed.`; update the `@return` line added in T002 to read `* @return true if startup was confirmed via the voltage-sag check; false if the flywheel failed to confirm spin-up (caller must treat as a fault).`

**Checkpoint**: User Stories 1 AND 2 both work independently — run quickstart.md §1 and §2.

---

## Phase 5: User Story 3 - Automatic Recovery Without a Full Power Cycle (Priority: P3)

**Goal**: Instead of latching a fault on the very first unconfirmed attempt, retry the full arm-and-spin-up sequence a bounded number of times — giving a transient, rotor-position-dependent startup failure a chance to self-correct without operator intervention — before finally giving up.

**Independent Test**: Induce a single transient stall and confirm automatic retry recovers without a power cycle; separately, induce a persistent stall through all attempts and confirm the device stops retrying and latches the fault rather than retrying forever (quickstart.md §3).

### Implementation

- [X] T011 [US3] In `firmware/include/config.h` (depends on T008): add directly below `CMG_ESC_VOLTAGE_SAG_MV`: `#define CMG_ESC_MAX_ATTEMPTS  3      // total arm/spin-up attempts (1 initial + 2 retries) before latching a fault`.

- [X] T012 [US3] In `firmware/src/cmg.cpp` (depends on T009, T011): wrap the full arm → command → settle → check sequence (from the `ledcWrite(CMG_FLYWHEEL_CHANNEL, (CMG_ESC_ARM_PULSE_US ...` line through the success-path `return true;` added in T009) in `for (int attempt = 1; attempt <= CMG_ESC_MAX_ATTEMPTS; attempt++) { ... }`; change the failure branch from `return false;` to: log `Serial.printf("[CMG] WARNING flywheel startup attempt %d/%d not confirmed (sag=%lumV) — retrying.\n", attempt, CMG_ESC_MAX_ATTEMPTS, (unsigned long)sag_mv);` and `continue;` the loop instead of returning; after the `for` loop exits (all attempts exhausted), add `Serial.printf("[FAULT] CMG flywheel startup failed after %d attempts.\n", CMG_ESC_MAX_ATTEMPTS); return false;`.

- [X] T013 [P] [US3] In `firmware/include/cmg.h` (depends on T010, T012): update the `cmg_init()` doc comment to add `* Retries the full arm-and-spin-up sequence up to CMG_ESC_MAX_ATTEMPTS times before giving up.`; update the flywheel channel description near the top of the file to mention the bounded retry behavior alongside the existing arm/command description.

**Checkpoint**: All three user stories are independently functional — run quickstart.md §1, §2, and §3.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm no dead config remains, no magic numbers crept back in, the firmware builds clean, and the full bench validation passes.

- [X] T014 [P] Dead-constant audit — run `grep -rn "CMG_ESC_RAMP_STEPS\|CMG_ESC_RAMP_STEP_MS" firmware/` from the repository root and confirm zero matches.

- [X] T015 [P] Magic-number audit — run `grep -n "900UL" firmware/src/cmg.cpp` from the repository root and confirm zero matches (the arm pulse must only be referenced via `CMG_ESC_ARM_PULSE_US`).

- [X] T016 Build firmware — run `pio run -e esp32dev` and `pio run -e esp32dev-debug` inside `firmware/` and confirm zero compilation errors (the `bool cmg_init()` signature change, the new `fault_halt()` helper, and the new `analogReadMilliVolts`/`for`-loop logic in `cmg.cpp` must all compile cleanly).

- [ ] T017 Run the full quickstart.md validation (§1, §2, §3) on real hardware and record results against its Pass/Fail summary table. **(Not run by the agent — requires physical hardware in hand; see completion report.)**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: T002 has no dependency on T001 (different files) and can run in parallel with it; T003 depends on T002; T004 depends on T002 + T003. Foundational BLOCKS all user stories.
- **User Stories (Phase 3-5)**: Each depends on Foundational being complete, and each depends on the *previous* story's `cmg.cpp`/`cmg.h` edits since they incrementally build the same function (US1 → US2 → US3 is a strict sequence here, not parallel stories, because each layers directly on top of the prior one's code).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each File

- `config.h`: T001 → T008 → T011 (sequential — each adds constants below the previous block)
- `cmg.h`: T002 → T006 → T010 → T013 (sequential doc updates, each [P] against the same-story `.cpp`/`config.h` task)
- `cmg.cpp`: T003 → T005 → T007 → T009 → T012 (sequential — cumulative edits to the same function)
- `main.cpp`: T004 only (no further edits needed in later stories)

```
T001 ──────────────────────────────┬──> T005 ──> T007 ──> T009 ──> T012 ──> T014 ──┐
T002 ──> T003 ──> T004 (main.cpp)  │                                              ├──> T016 ──> T017
                  T002 ──> T006 ──> T010 ──> T013                                  T015 ──┘
T008 (needs T001) ──> T011 (needs T008)
```

### Parallel Opportunities

- T001 and T002 (different files: `config.h` vs `cmg.h`) can run in parallel at the very start.
- Within each story, the `cmg.h` doc task (T006, T010, T013) is marked `[P]` — it's a different file from that story's `cmg.cpp`/`config.h` task and can be written alongside it, as long as it accurately describes the resulting behavior.
- T014 and T015 (independent greps) can run in parallel with each other.

---

## Parallel Example: Foundational Phase

```bash
# T001 and T002 touch different files and have no dependency on each other:
Task: "Remove dead ramp constants + add CMG_ESC_ARM_PULSE_US in firmware/include/config.h"
Task: "Change cmg_init() declaration to bool in firmware/include/cmg.h"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (US1).
3. **STOP and VALIDATE**: run quickstart.md §1 — 20 consecutive power-on cycles, zero fault cutoffs.
4. This alone may already satisfy the core reported symptom, since it formalizes the arm-pulse/no-ramp fix already validated empirically on the bench.

### Incremental Delivery

1. Setup + Foundational → contract ready, no behavior change yet.
2. Add US1 → validate independently (quickstart §1) → this is the MVP.
3. Add US2 → validate independently (quickstart §2) → failures are now visible instead of silent.
4. Add US3 → validate independently (quickstart §3) → transient failures self-heal; persistent failures still latch a clear fault.
5. Polish → build + grep audits + full quickstart re-run.

---

## Notes

- There is no automated firmware test suite in this repo (`firmware/test/` does not exist) — every checkpoint above is a manual bench-test step against the real EMAX 30A ESC + 2200KV motor + 35g aluminum flywheel, per quickstart.md.
- `CMG_ESC_VOLTAGE_SAG_MV` (T008) is an explicitly best-effort heuristic (research.md §4) — if bench testing shows it doesn't reliably distinguish success from failure, the threshold value is the first thing to retune; the retry loop (US3) provides resilience even if the heuristic is occasionally wrong in either direction.
- The gimbal servo channel is untouched by this entire feature — only the flywheel ESC channel's arm/command/retry logic changes.
- This feature does not add any new FreeRTOS task or touch `task_scheduler.cpp` — the whole retry loop is a bounded, blocking sequence inside `cmg_init()`, called once from `setup()` before the scheduler starts, matching how arming already worked before this feature.
