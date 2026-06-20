# Implementation Plan: Fix CMG Flywheel ESC Arming and Stall Failure

**Branch**: `049-fix-esc-flywheel-stall` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/049-fix-esc-flywheel-stall/spec.md`

## Summary

The CMG flywheel's EMAX 30A BLHeli ESC fails to reliably drive the motor against the 35g solid-aluminum flywheel's high rotational inertia: it beeps continuously before start (Phase 1), spins for ~1s then cuts power on a stall/desync (Phase 2), then beeps continuously and ignores further commands (Phase 3). The fix is firmware-only and PWM-only (per clarified scope): tune the ESC arm pulse and startup-throttle command shape, and — critically — add a runtime supervisory retry loop in `cmg_init()` that currently does not exist at all, since the firmware today commands the flywheel once at boot and never revisits it, which is why a stalled ESC (Phase 2) is never re-armed and sits beeping forever (Phase 3). Detection of success/failure has no dedicated telemetry (no RPM/current sensor wired); the approach uses the existing battery-voltage ADC as a best-effort heuristic plus a bounded blind-retry safety net, escalating to a distinguishable persistent fault state after exhausting retries.

## Technical Context

**Language/Version**: C++ (Arduino core for ESP32, PlatformIO `espressif32` platform)
**Primary Dependencies**: Arduino `ledcSetup`/`ledcAttachPin`/`ledcWrite` (LEDC PWM), existing `battery_reader` module (ADC), existing `FAULT_LED_PIN` fault indicator
**Storage**: N/A (no persistence; in-memory state machine only, scoped to a single boot cycle)
**Testing**: No automated firmware test harness exists in this repo (`firmware/test/` does not exist); validation is manual bench testing against real hardware (EMAX 30A ESC + 2200KV motor + 35g aluminum flywheel), per the Independent Test descriptions in spec.md and quickstart.md below
**Target Platform**: ESP32 (PlatformIO `esp32dev` board), local development only
**Project Type**: monorepo — this feature touches `firmware/` exclusively; no `backend/` or `frontend/` changes
**Performance Goals**: Flywheel reaches stable operating speed within 10s on the happy path (SC-002); fault detection/retry path is allowed to take longer (each retry attempt re-runs the multi-second arm hold) since it's a recovery path, not the normal path
**Constraints**: Firmware/PWM-only fix — no flywheel/motor/gearing hardware changes (FR-006), no ESC reconfiguration via vendor tooling/cable (FR-007); no new sensors assumed available — must work with the existing battery-voltage ADC as the only indirect signal
**Scale/Scope**: Single embedded device; changes confined to `firmware/include/config.h`, `firmware/include/cmg.h`, `firmware/src/cmg.cpp`, `firmware/src/main.cpp`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature is **firmware-only** with zero backend, frontend, database, auth, or web-API surface. Most constitutional principles target the web platform and don't apply here; marked N/A rather than forced.

- [x] **Monorepo Architecture**: All changes live in `firmware/` — fits the existing structure.
- [x] **Tech Stack Immutability**: No new frameworks/libraries; uses the existing Arduino/ESP32 LEDC PWM and battery ADC APIs already in this codebase.
- [x] **Database Strategy**: N/A — no data persistence involved.
- [x] **Authentication**: N/A — no user-facing or web-API surface.
- [x] **Security-First**: N/A — no secrets/credentials involved.
- [x] **Real-time Requirements**: N/A — no WebSocket/dashboard surface for this feature.
- [x] **MQTT Integration**: N/A — not changing the MQTT publish pipeline. (Surfacing the new fault state over MQTT/dashboard is explicitly a non-goal for this feature; see Out of Scope below.)
- [x] **AI Model Serving**: N/A.
- [x] **API Standards**: N/A — no REST endpoints (see Project Structure; no `contracts/` generated for this feature).
- [x] **Development Scope**: Local/bench development only, consistent with constitution.

**Result**: ✅ PASS — no violations; inapplicable principles marked N/A rather than checked against a non-existent surface.

## Project Structure

### Documentation (this feature)

```text
specs/049-fix-esc-flywheel-stall/
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
├── include/
│   ├── config.h     # New named constants: arm pulse width, retry bound, settle/verify timing
│   └── cmg.h         # Updated cmg_init() contract docs (arm → command → verify/retry → fault)
├── src/
│   ├── cmg.cpp        # cmg_init() gains the supervisory arm/verify/retry/fault-latch loop
│   └── main.cpp       # STATE_FAULT becomes distinguishable: CMG startup fault vs IMU/calibration fault
```

**Structure Decision**: All work is in the existing `firmware/` actuation module (`cmg.cpp`/`cmg.h`) plus its config constants and the boot-fault reporting already in `main.cpp`. No new files, no new modules, no `task_scheduler.cpp` changes — the retry loop is a bounded, blocking sequence that runs to completion inside `cmg_init()` during `setup()`, before the FreeRTOS scheduler starts (matching how arming already works today), not a new ongoing background task.

## Complexity Tracking

*No constitution violations — this section is intentionally empty.*
