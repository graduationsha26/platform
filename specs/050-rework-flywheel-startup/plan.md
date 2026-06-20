# Implementation Plan: Fix CMG Flywheel Startup Stall Using a Validated Brushless-Motor Sequence

**Branch**: `050-rework-flywheel-startup` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/050-rework-flywheel-startup/spec.md`

## Summary

The CMG flywheel's ESC still fails to reliably drive the motor against the 35g solid-aluminum flywheel's high rotational inertia even after the prior fix (`049-fix-esc-flywheel-stall`: a 900µs arm pulse, a direct jump to full target throttle, and a battery-voltage-sag retry heuristic) was bench-tested on the real assembled device. A separate standalone bench-test program (`run_zizo.cpp`), wired to the identical GPIO/SPI pin assignments as production, has empirically demonstrated a startup sequence that reliably spins the same motor up without the three-phase failure — using the `ESP32Servo` library instead of raw LEDC calls, a standard 1000µs arm pulse, and a small step (1000µs→1080µs) from arm to running speed instead of a large jump. This plan replaces `cmg.cpp`'s flywheel (and, to avoid a PWM-channel-allocation conflict, gimbal) actuation with `ESP32Servo`, replicates the validated arm/run pulse pattern, and keeps the existing bounded-retry/distinguishable-fault-state wrapper (`049`'s FR-004/008/009 carried forward) around the corrected sequence. The reference program's own servo-stabilization PID loop is explicitly not ported — the production gimbal control path (sensor fusion + PID + FreeRTOS task scheduler) is unchanged; only the low-level pulse-write primitive underneath it switches library.

## Technical Context

**Language/Version**: C++ (Arduino core for ESP32 — `framework-arduinoespressif32` v2.0.17 confirmed installed, PlatformIO `espressif32` platform)
**Primary Dependencies**: `ESP32Servo` library (new — added to `lib_deps`; not previously used in this codebase), existing `battery_reader` module (ADC), existing `FAULT_LED_PIN` fault indicator
**Storage**: N/A — no persistence; in-memory state machine only, scoped to a single boot cycle
**Testing**: No automated firmware test harness exists in this repo (`firmware/test/` does not exist); validation is manual bench testing against real hardware, per quickstart.md
**Target Platform**: ESP32 (PlatformIO `esp32dev` board), local development only
**Project Type**: monorepo — this feature touches `firmware/` exclusively; no `backend/` or `frontend/` changes
**Performance Goals**: Flywheel reaches stable operating speed within 10s on the happy path (SC-002); fault detection/retry path is allowed to take longer (each retry re-runs the multi-second arm hold), same as `049`
**Constraints**: Firmware/PWM-only fix — no flywheel/motor/gearing hardware changes (FR-006), no ESC reconfiguration via vendor tooling/cable (FR-007); must not alter the gimbal's production sensor-fusion/PID/task-scheduling control path (FR-011) — only the actuation primitive beneath it may change
**Scale/Scope**: Single embedded device; changes confined to `firmware/platformio.ini` (new `lib_deps` entry), `firmware/include/config.h`, `firmware/include/cmg.h`, `firmware/src/cmg.cpp`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature is **firmware-only** with zero backend, frontend, database, auth, or web-API surface. Most constitutional principles target the web platform and don't apply here; marked N/A rather than forced.

- [x] **Monorepo Architecture**: All changes live in `firmware/` — fits the existing structure.
- [x] **Tech Stack Immutability**: No new backend/frontend frameworks. `ESP32Servo` is a new firmware-only PlatformIO library; the constitution's stack lock (§II) covers Django/React only and does not restrict firmware libraries — this is within the existing PlatformIO/Arduino-ESP32 firmware architecture, not a stack change.
- [x] **Database Strategy**: N/A — no data persistence involved.
- [x] **Authentication**: N/A — no user-facing or web-API surface.
- [x] **Security-First**: N/A — no secrets/credentials involved.
- [x] **Real-time Requirements**: N/A — no WebSocket/dashboard surface for this feature.
- [x] **MQTT Integration**: N/A — not changing the MQTT publish pipeline.
- [x] **AI Model Serving**: N/A.
- [x] **API Standards**: N/A — no REST endpoints (see Project Structure; no `contracts/` generated for this feature).
- [x] **Development Scope**: Local/bench development only, consistent with constitution.

**Result**: ✅ PASS — no violations; inapplicable principles marked N/A rather than checked against a non-existent surface. The new `ESP32Servo` dependency is evaluated above and found not to conflict with Tech Stack Immutability, which scopes only the Django/React stacks.

## Project Structure

### Documentation (this feature)

```text
specs/050-rework-flywheel-startup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — startup/fault state machine (no DB entities)
├── quickstart.md         # Phase 1 output — bench validation steps
└── tasks.md              # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

No `contracts/` directory is generated for this feature — there is no REST/API surface to contract (pure firmware/hardware behavior, no backend or frontend interaction).

### Source Code (repository root)

```text
firmware/
├── platformio.ini   # New `lib_deps` entry: ESP32Servo
├── include/
│   ├── config.h     # CMG_ESC_ARM_PULSE_US 900→1000; CMG_FLYWHEEL_IDLE_US lowered to match validated reference; CMG_ESC_VOLTAGE_SAG_MV retuned
│   └── cmg.h         # Updated cmg_init()/cmg_set_gimbal() contract docs (ESP32Servo-based)
├── src/
│   └── cmg.cpp        # Both LEDC channels replaced with ESP32Servo Servo objects; flywheel arm/run sequence replaced with the validated pattern; retry/fault-detection wrapper retained around it
```

`firmware/src/main.cpp` is NOT modified by this feature — the `bool cmg_init()` contract and `fault_halt()` helper introduced by `049` are already in place and are reused as-is.

**Structure Decision**: All work is in the existing `firmware/` actuation module (`cmg.cpp`/`cmg.h`) plus its config constants and its PlatformIO library dependency. No new files, no new modules, no `task_scheduler.cpp` or `main.cpp` changes — the corrected sequence still runs as a bounded, blocking routine inside `cmg_init()`, called once from `setup()` before the FreeRTOS scheduler starts, matching the existing structure from `049`.

## Complexity Tracking

*No constitution violations — this section is intentionally empty.*
