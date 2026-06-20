# Data Model: Fix CMG Flywheel Startup Stall Using a Validated Brushless-Motor Sequence

This feature has no database entities. "Data model" here means the in-memory **Flywheel Startup Sequence** state machine that `cmg_init()` runs through once per boot (see spec.md's Key Entities section), updated from `049-fix-esc-flywheel-stall`'s version to reflect the corrected sequence and PWM-generation pathway (research.md).

## State Machine

| State | Description | Entered From | Exits To |
|---|---|---|---|
| `ARMING` | Flywheel `Servo` object holds the arm pulse (`CMG_ESC_ARM_PULSE_US`, now 1000µs) for `CMG_ESC_ARM_MS`, confirming "disarmed/idle" to the ESC and clearing any pre-start beep (Phase 1). | Boot (start of `cmg_init()`); also re-entered on retry | `COMMANDING` |
| `COMMANDING` | Flywheel `Servo` object is driven directly to the (now lowered) `CMG_FLYWHEEL_IDLE_US` running pulse — a small step above the arm pulse, matching the validated reference sequence. No software ramp, and no second/larger jump afterward. | `ARMING` | `SETTLING` |
| `SETTLING` | Fixed wait window after the running-pulse command; a best-effort battery-voltage-sag sample is taken to inform (not strictly gate) the next decision. | `COMMANDING` | `RUNNING` (assume success) or `RETRYING` |
| `RUNNING` | Startup sequence considered complete; `cmg_init()` returns normally and boot proceeds to `scheduler_start()`. | `SETTLING` | *(terminal for this sequence — flywheel pulse is not touched again during normal operation)* |
| `RETRYING` | Attempt counter incremented; if below the bound, transitions back to `ARMING` for another full attempt. | `SETTLING` | `ARMING` (if attempts remain) or `FAULT_LATCHED` (if exhausted) |
| `FAULT_LATCHED` | All attempts exhausted. A distinguishable persistent fault is reported (Serial message + `FAULT_LED_PIN` pattern distinct from the existing IMU/calibration fault) and `setup()` halts the same way it already does for IMU/calibration failures. | `RETRYING` | *(terminal — requires operator-visible fault, not a silent hang; satisfies FR-004/FR-009)* |

## Fields

| Field | Type | Notes |
|---|---|---|
| `attempt_count` | integer, starts at 0 | Incremented each time `RETRYING` is entered; compared against the bounded max (`CMG_ESC_MAX_ATTEMPTS`, carried over from `049`). |
| `arm_pulse_us` | constant (`CMG_ESC_ARM_PULSE_US`) | Microsecond pulse width held during `ARMING` — now 1000µs (research.md §2), matching the validated reference exactly. |
| `running_pulse_us` | constant (`CMG_FLYWHEEL_IDLE_US`) | Microsecond pulse width commanded during `COMMANDING` — lowered to a small step above the arm pulse (research.md §3); bench-tunable if found insufficient for required counter-torque. |
| `settle_window_ms` | constant (`CMG_ESC_SETTLE_MS`) | Time spent in `SETTLING` before deciding; carried over from `049`, re-validated against the new (smaller) expected voltage sag. |
| `voltage_baseline_mv` / `voltage_post_mv` | transient, read during `SETTLING` | Best-effort heuristic samples via the existing battery ADC; compared against `CMG_ESC_VOLTAGE_SAG_MV`, which must be re-tuned for the new, smaller running-pulse step (research.md §4). |

## Validated Reference Sequence (new entity, per spec.md Key Entities)

| Field | Value | Source |
|---|---|---|
| PWM generation pathway | `ESP32Servo` library `Servo` class (`attach()` / `writeMicroseconds()`) | `run_zizo.cpp` |
| `attach()` pulse range | 1000–2000µs | `run_zizo.cpp brushlessMotor.attach(BRUSHLESS_PIN, 1000, 2000)` |
| Arm pulse | 1000µs | `run_zizo.cpp brushlessMotor.writeMicroseconds(1000)` |
| Arm hold duration | 5000ms | `run_zizo.cpp delay(5000)` |
| Running pulse | 1080µs (small step above arm) | `run_zizo.cpp brushlessMotor.writeMicroseconds(1080)` |
| Out of scope from this reference | Single-axis raw-gyro PID stabilizer-servo loop (no sensor fusion, no task scheduling) | `run_zizo.cpp loop()` — explicitly NOT ported (FR-011) |

This entity exists purely as a documentation anchor — it is not represented in runtime state, only in `research.md` decisions and the corrected constants in `config.h`.

## Notes on scope

- This state machine runs entirely inside `cmg_init()`, called once from `setup()` before `scheduler_start()` — it is not a new FreeRTOS task and does not run during normal operation. A stall occurring *after* `RUNNING` is reached (the Edge Case noted in spec.md) is not covered by this state machine, same as `049`.
- `FAULT_LATCHED` reuses the existing `STATE_FAULT` halt behavior in `main.cpp` (blink `FAULT_LED_PIN` forever) rather than introducing a new halt mechanism — only the Serial message (and blink cadence) differs so it's distinguishable from an IMU/calibration fault, per FR-004.
- The gimbal servo's actuation primitive (`cmg_set_gimbal()`) also moves to the `ESP32Servo` library (research.md §1) but has no state machine of its own — it remains a stateless per-call pulse write driven by the unchanged production PID/sensor-fusion/task-scheduler pipeline (FR-011), outside this feature's state machine.
