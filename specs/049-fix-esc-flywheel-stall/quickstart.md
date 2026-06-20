# Quickstart: Validating the CMG Flywheel ESC Fix

No automated test harness exists for this firmware; validation is manual bench testing against the real EMAX 30A ESC + 2200KV motor + 35g aluminum flywheel hardware. These steps map directly to the Independent Test descriptions and Success Criteria in spec.md.

## Prerequisites

- Assembled glove hardware with the ESC, motor, and 35g aluminum flywheel installed.
- PlatformIO environment `esp32dev-debug` flashed (enables `FIRMWARE_DEBUG` Serial diagnostics).
- Serial monitor open at 115200 baud (per `platformio.ini`).
- Fresh/adequately charged battery — battery condition affects the voltage-sag heuristic (research.md §4); don't validate on a marginal/low battery, since that's a separate edge case (spec.md Edge Cases).

## 1. Happy-path startup reliability (User Story 1 / SC-001, SC-002, SC-003)

1. Power on the device. Watch Serial for the boot sequence log lines (arm → command → settle/verify → running).
2. Confirm: no continuous beep pattern before the flywheel starts (Phase 1 must not reproduce).
3. Confirm: the flywheel spins up and stays running — no cutout around the 1-second mark (Phase 2 must not reproduce).
4. Confirm: once running, no beeping resumes and the flywheel keeps spinning during normal operation (Phase 3 must not reproduce).
5. Confirm: time from power-on to "running" logged state is under 10 seconds (SC-002).
6. Power-cycle the device and repeat steps 1–5 at least 20 times total. All 20 must succeed with zero fault-beep occurrences (SC-001, SC-003).

## 2. Fault detection is distinguishable (User Story 2 / SC-004)

1. Deliberately induce a startup fault in a way that does not risk damaging hardware — e.g., briefly hold the flywheel shaft stationary by hand during the `COMMANDING`/`SETTLING` window so it cannot spin up, then release.
2. Confirm the Serial log reports a distinct "flywheel startup fault" message — not the same message/state used for an IMU/calibration failure.
3. Repeat the induced-fault test multiple times; confirm it's correctly identified as the CMG fault type every time (100% per SC-004).

## 3. Automatic retry and bounded fault latch (User Story 3 / SC-005)

1. Induce a single transient stall (hold the shaft briefly during one attempt, then release before the next attempt starts) and confirm the device automatically retries and reaches `RUNNING` without a power cycle.
2. Induce a persistent stall (hold the shaft stationary through all retry attempts) and confirm the device stops retrying after the bounded attempt count and enters the persistent fault state (`FAULT_LATCHED`) — it must not retry forever, and must not require pulling the battery to notice the fault (the fault should already be visible via Serial/LED).
3. Release the shaft and power-cycle once to confirm normal recovery — this is the expected way out of a latched fault, not a sign of a bug.

## Pass/fail summary

| Check | Spec reference |
|---|---|
| 20/20 power-on cycles reach stable speed, no fault cutoff | SC-001 |
| Startup completes within 10s on the happy path | SC-002 |
| Zero unexpected fault-beeping across normal cycles | SC-003 |
| Induced fault always reported as the correct, distinct fault type | SC-004 |
| Transient fault recovers automatically; persistent fault latches (not infinite retry) | SC-005 |
