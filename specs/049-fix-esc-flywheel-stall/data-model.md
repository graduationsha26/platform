# Data Model: Fix CMG Flywheel ESC Arming and Stall Failure

This feature has no database entities. "Data model" here means the in-memory **Flywheel Startup Sequence** state machine that `cmg_init()` runs through once per boot (see spec.md's Key Entities section for the conceptual definitions this formalizes).

## State Machine

| State | Description | Entered From | Exits To |
|---|---|---|---|
| `ARMING` | Flywheel channel holds the low arm pulse for `CMG_ESC_ARM_MS`, confirming "disarmed/idle" to the ESC and clearing any pre-start beep (Phase 1). | Boot (start of `cmg_init()`); also re-entered on retry | `COMMANDING` |
| `COMMANDING` | Flywheel channel is driven directly to `CMG_FLYWHEEL_DUTY` (target operating throttle) — no software ramp. | `ARMING` | `SETTLING` |
| `SETTLING` | Fixed wait window after the target command; a best-effort battery-voltage sag sample is taken to inform (not strictly gate) the next decision. | `COMMANDING` | `RUNNING` (assume success) or `RETRYING` |
| `RUNNING` | Startup sequence considered complete; `cmg_init()` returns normally and boot proceeds to `scheduler_start()`. | `SETTLING` | *(terminal for this sequence — flywheel duty is not touched again during normal operation)* |
| `RETRYING` | Attempt counter incremented; if below the bound, transitions back to `ARMING` for another full attempt. | `SETTLING` | `ARMING` (if attempts remain) or `FAULT_LATCHED` (if exhausted) |
| `FAULT_LATCHED` | All attempts exhausted. A distinguishable persistent fault is reported (Serial message + `FAULT_LED_PIN` pattern distinct from the existing IMU/calibration fault) and `setup()` halts the same way it already does for IMU/calibration failures. | `RETRYING` | *(terminal — requires operator-visible fault, not a silent hang; satisfies FR-004/FR-009)* |

## Fields

| Field | Type | Notes |
|---|---|---|
| `attempt_count` | integer, starts at 0 | Incremented each time `RETRYING` is entered; compared against the bounded max (research.md §5: 3 total attempts). |
| `arm_pulse_us` | constant (`CMG_ESC_ARM_PULSE_US`) | Microsecond pulse width held during `ARMING` (research.md §2: 900µs). |
| `target_duty` | constant (`CMG_FLYWHEEL_DUTY`, already derived from `CMG_FLYWHEEL_IDLE_US`) | LEDC duty commanded during `COMMANDING`; unchanged by this feature. |
| `settle_window_ms` | constant | Time spent in `SETTLING` before deciding (research.md §5: ~1–2s). |
| `voltage_baseline_mv` / `voltage_post_mv` | transient, read during `SETTLING` | Best-effort heuristic samples via the existing battery ADC; informs but does not solely gate the retry decision (research.md §4). |

## Notes on scope

- This state machine runs entirely inside `cmg_init()`, called once from `setup()` before `scheduler_start()` — it is not a new FreeRTOS task and does not run during normal operation. A stall occurring *after* `RUNNING` is reached (the Edge Case noted in spec.md) is not covered by this state machine; see research.md §4's "Alternatives considered" for why continuous runtime monitoring is explicitly deferred.
- `FAULT_LATCHED` reuses the existing `STATE_FAULT` halt behavior in `main.cpp` (blink `FAULT_LED_PIN` forever) rather than introducing a new halt mechanism — only the Serial message (and, if feasible, blink cadence) differs so it's distinguishable from an IMU/calibration fault, per FR-004.
