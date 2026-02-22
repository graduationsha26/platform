# Tasks: FreeRTOS Task Scheduler for Glove Control (Feature 031)

**Input**: Design documents from `/specs/031-freertos-scheduler/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story. US1 (control loop) is the MVP — once SensorTask and ControlTask run at 200Hz/100Hz, tremor suppression is live. US2 adds diagnostic counters to prove concurrent isolation. US3 adds the MqttTask. All tasks target `firmware/` only — no backend or frontend changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- Paths: `firmware/` (ESP32 C++/Arduino)

---

## Phase 1: Setup (Configuration)

**Purpose**: Add all Feature 031 config constants. Must be complete before any headers can reference them.

- [X] T001 Update `firmware/include/config.h.example` — add Feature 031 to file header comment; add `// ─── CMG Actuation ────────────────────────────────────────────────────────────` section with: `CMG_GIMBAL_PIN 18` (GPIO18 — gimbal servo), `CMG_GIMBAL_CHANNEL 0` (LEDC channel 0), `CMG_FLYWHEEL_PIN 19` (GPIO19 — flywheel ESC), `CMG_FLYWHEEL_CHANNEL 1` (LEDC channel 1), `CMG_PWM_FREQ_HZ 50`, `CMG_PWM_RESOLUTION 16` (16-bit duty, 0–65535), `CMG_GIMBAL_MAX_DEG 60.0f` (±60° gimbal range), `CMG_FLYWHEEL_DUTY 5243` (~1600µs constant throttle — tune per ESC); add `// ─── PID Controller Tuning ────────────────────────────────────────────────────` section with inline comments explaining gyro-velocity feedback: `PID_KP 1.0f`, `PID_KI 0.01f`, `PID_KD 0.03f`, `PID_TAU 0.008f` (derivative LPF, fc≈20Hz), `PID_OUTPUT_MIN -1.0f`, `PID_OUTPUT_MAX 1.0f`; add `// ─── FreeRTOS Task Stack Sizes ────────────────────────────────────────────────` section: `SENSOR_TASK_STACK 6144`, `CONTROL_TASK_STACK 4096`, `MQTT_TASK_STACK 8192`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Headers and implementations for CMG, PID, and FreeRTOS task framework that ALL user stories depend on. T002–T004 touch different files and can run in parallel. T005 depends on T002; T006 depends on T003; T007 is independent.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [X] T002 [P] Create `firmware/include/cmg.h` — `#pragma once`; Feature 031 header comment; declare `void cmg_init()` (doc: initialises LEDC channels for gimbal servo and flywheel ESC; arms flywheel ESC with 1000µs pulse then ramps to `CMG_FLYWHEEL_DUTY`; call once in `setup()` before `scheduler_start()`); declare `void cmg_set_gimbal(float output_normalized)` (doc: `output_normalized` range [-1.0, +1.0]; maps to gimbal angle [±CMG_GIMBAL_MAX_DEG]; generates 16-bit LEDC duty; call from ControlTask at 200Hz)
- [X] T003 [P] Create `firmware/include/pid_controller.h` — `#pragma once`; Feature 031 header comment; define `PidController` struct with fields: `float Kp, Ki, Kd` (gains), `float tau` (derivative LPF time constant in seconds), `float dt` (fixed control period in seconds), `float setpoint` (target angular velocity, default 0.0), `float integral` (accumulated integral term), `float prev_error` (error at t-1), `float prev_deriv_filt` (IIR state for filtered derivative), `float out_min, out_max` (output clamp limits); declare `void pid_init(PidController* pid, float Kp, float Ki, float Kd, float tau, float dt, float out_min, float out_max)` (zeros all state fields, sets gain parameters); declare `float pid_update(PidController* pid, float measurement)` (returns clamped output in [out_min, out_max])
- [X] T004 [P] Create `firmware/include/task_scheduler.h` — `#pragma once`; Feature 031 header comment; `#include "freertos/FreeRTOS.h"`, `#include "freertos/task.h"`, `#include "freertos/queue.h"`, `#include "imu.h"` (for CalibrationOffsets); declare `extern QueueHandle_t g_sensor_mailbox` (length-1 queue for FusedReading; written by SensorTask via xQueueOverwrite; read by ControlTask and MqttTask via xQueuePeek); declare `void scheduler_start(CalibrationOffsets* offsets)` (doc: creates g_sensor_mailbox, seeds Kalman filters from offsets, creates SensorTask/ControlTask/MqttTask via xTaskCreatePinnedToCore; call once from setup() after calibration and cmg_init())
- [X] T005 Create `firmware/src/cmg.cpp` — `#include "cmg.h"`, `#include "config.h"`, `#include <Arduino.h>`; implement `cmg_init()`: call `ledcSetup(CMG_GIMBAL_CHANNEL, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION)`, `ledcAttachPin(CMG_GIMBAL_PIN, CMG_GIMBAL_CHANNEL)`, `ledcWrite(CMG_GIMBAL_CHANNEL, (1500UL * 65536UL) / 20000UL)` (center, 1500µs), then `ledcSetup(CMG_FLYWHEEL_CHANNEL, CMG_PWM_FREQ_HZ, CMG_PWM_RESOLUTION)`, `ledcAttachPin(CMG_FLYWHEEL_PIN, CMG_FLYWHEEL_CHANNEL)`, `ledcWrite(CMG_FLYWHEEL_CHANNEL, (1000UL * 65536UL) / 20000UL)` (arm ESC at 1000µs), `delay(2000)` (ESC arming delay), `ledcWrite(CMG_FLYWHEEL_CHANNEL, CMG_FLYWHEEL_DUTY)` (run at constant throttle), log `[CMG] Initialized.`; implement `cmg_set_gimbal(float output_normalized)`: clamp to [-1.0f, 1.0f], compute `angle_deg = output_normalized * CMG_GIMBAL_MAX_DEG`, `pulse_us = (uint32_t)(1500.0f + angle_deg * (1000.0f / CMG_GIMBAL_MAX_DEG))`, clamp pulse_us to [833, 2167], `duty = (pulse_us * 65536UL) / 20000UL`, `ledcWrite(CMG_GIMBAL_CHANNEL, duty)` (depends on T002, T001)
- [X] T006 Create `firmware/src/pid_controller.cpp` — `#include "pid_controller.h"`, `#include <string.h>`; implement `pid_init()`: `memset(pid, 0, sizeof(*pid))`, set `pid->Kp=Kp, Ki=Ki, Kd=Kd, tau=tau, dt=dt, out_min=out_min, out_max=out_max, setpoint=0.0f`; implement `pid_update(PidController* pid, float measurement)`: compute `error = pid->setpoint - measurement`, `d_raw = (error - pid->prev_error) / pid->dt`, `alpha = pid->dt / (pid->tau + pid->dt)`, `d_filt = alpha * d_raw + (1.0f - alpha) * pid->prev_deriv_filt`, `integral_new = pid->integral + pid->Ki * error * pid->dt`, `output = pid->Kp * error + integral_new + pid->Kd * d_filt`, apply conditional anti-windup: if `output > pid->out_max` set `output = pid->out_max` (do NOT update pid->integral); else if `output < pid->out_min` set `output = pid->out_min` (do NOT update pid->integral); else `pid->integral = integral_new`, update `pid->prev_error = error`, `pid->prev_deriv_filt = d_filt`, `return output` (depends on T003)
- [X] T007 [P] Update `firmware/include/mqtt_publisher.h` — add `uint64_t t_sensor_us` field to `FusedReading` struct after `battery_level`; add inline comment `// esp_timer_get_time() at end of Kalman update (µs since boot); used by ControlTask for sensor-to-actuation latency measurement`; update struct doc comment to note the new field; add Feature 031 to file header comment

**Checkpoint**: Foundational phase complete. CMG and PID implementations exist. FusedReading carries latency timestamp. Task scheduler interface declared.

---

## Phase 3: User Story 1 — Responsive Tremor Suppression (Priority: P1) 🎯 MVP

**Goal**: Glove detects tremor via gyro at 100Hz, runs PID control at 200Hz, issues CMG gimbal command within 70ms of each sensor reading.

**Independent Test**: Flash firmware; enable FIRMWARE_DEBUG; observe serial showing `[BOOT] SensorTask started (Core 1, prio 8, 100Hz)` and `[BOOT] ControlTask started (Core 1, prio 10, 200Hz)`; tilt glove and verify oscilloscope on GPIO18 shows PWM duty changing; verify serial shows `[CTRL] Latency: Xms violations: 0` over a 5-minute run.

- [X] T008 [US1] Create `firmware/src/task_scheduler.cpp` with SensorTask — Feature 031 header comment; `#include` all headers: `task_scheduler.h`, `config.h`, `imu.h`, `kalman.h`, `mqtt_publisher.h`, `battery_reader.h`, `cmg.h`, `pid_controller.h`, `esp_timer.h`, `<Arduino.h>`; define `QueueHandle_t g_sensor_mailbox = NULL`; declare `static TaskHandle_t s_sensor_handle, s_control_handle, s_mqtt_handle`; declare `static KalmanFilter s_roll_kf, s_pitch_kf`; implement `sensorTaskFn(void* pv)`: cast pv to `CalibrationOffsets*`; declare `static RawSample raw`, `static CalibratedSample calib`, `static FusedReading fr`; declare `TickType_t xLastWakeTime = xTaskGetTickCount()`; `for(;;)`: call `read_raw_sample(&raw)` (skip cycle on false), `apply_calibration(&raw, offsets, &calib)`, compute `roll_accel_deg = accel_roll(calib.aY, calib.aZ)` and `pitch_accel_deg = accel_pitch(calib.aX, calib.aY, calib.aZ)`, call `kalman_update(&s_roll_kf, roll_accel_deg, calib.gX, calib.dt, calib.aX, calib.aY, calib.aZ)` → `fr.roll` and similarly for pitch, populate `fr.aX/aY/aZ/gX/gY/gZ` from calib, set `fr.t_sensor_us = esp_timer_get_time()`, call `xQueueOverwrite(g_sensor_mailbox, &fr)`, call `vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(IMU_SAMPLE_PERIOD_MS))`; implement `scheduler_start(CalibrationOffsets* offsets)`: `g_sensor_mailbox = xQueueCreate(1, sizeof(FusedReading))`, `configASSERT(g_sensor_mailbox != NULL)`, seed `kalman_init(&s_roll_kf, offsets->gX_bias)` and `kalman_init(&s_pitch_kf, offsets->gY_bias)`, call `xTaskCreatePinnedToCore(sensorTaskFn, "SensorTask", SENSOR_TASK_STACK, offsets, 8, &s_sensor_handle, 1)`, log `[BOOT] SensorTask started (Core 1, prio 8, 100Hz)` (depends on T004, T005, T006, T007)
- [X] T009 [US1] Add ControlTask to `firmware/src/task_scheduler.cpp` and extend `scheduler_start()` — implement `controlTaskFn(void*)`: declare `static FusedReading snapshot`; declare `PidController pid_roll` and `PidController pid_pitch`; call `pid_init(&pid_roll, PID_KP, PID_KI, PID_KD, PID_TAU, 0.005f, PID_OUTPUT_MIN, PID_OUTPUT_MAX)` and same for `pid_pitch`; declare `TickType_t xLastWakeTime = xTaskGetTickCount()`; `for(;;)`: call `xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(10))`; compute `roll_out = pid_update(&pid_roll, snapshot.gX)` (gyro angular velocity feedback, setpoint=0); compute `pitch_out = pid_update(&pid_pitch, snapshot.gY)`; combined `torque = constrain((roll_out + pitch_out) * 0.5f, -1.0f, 1.0f)`; call `cmg_set_gimbal(torque)`; compute `int64_t latency_us = esp_timer_get_time() - snapshot.t_sensor_us`; if `latency_us > 70000` call `Serial.printf("[CTRL] WARNING latency=%lldus exceeds 70ms budget\n", latency_us)`; call `vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(5))`; in `scheduler_start()` after SensorTask creation: call `xTaskCreatePinnedToCore(controlTaskFn, "ControlTask", CONTROL_TASK_STACK, NULL, 10, &s_control_handle, 1)`, log `[BOOT] ControlTask started (Core 1, prio 10, 200Hz)` (depends on T008)
- [X] T010 [US1] Update `firmware/src/main.cpp` — add Feature 031 to file header comment and pipeline description; add `#include "task_scheduler.h"` and `#include "cmg.h"`; in `setup()`: after `battery_init()` / `[BOOT] Battery ADC initialized.` log, add `cmg_init()` and log `[BOOT] CMG initialized (GPIO18 gimbal, GPIO19 flywheel, 50Hz 16-bit).`; remove `mqtt_connect()` call and its failure warning (MQTT connect moves to MqttTask in T013); after `kalman_init()` calls, replace the two `kalman_init()` calls with `scheduler_start(&g_offsets)` (Kalman init now happens inside scheduler_start) and log `[BOOT] FreeRTOS tasks started.`; remove `g_roll_kf`, `g_pitch_kf`, `g_raw`, `g_calib`, `g_fused` global declarations (moved to task_scheduler.cpp); update `loop()` body: remove the entire 100Hz millis() scheduler, IMU read, Kalman update, MQTT publish, and mqtt_loop() code; replace with `vTaskDelete(NULL)` and a comment `// loopTask deleted — all work runs in FreeRTOS tasks; vTaskDelete prevents watchdog starvation of IDLE task`; update `[BOOT] Firmware running` log to say `[BOOT] Firmware running — FreeRTOS task scheduler active (SensorTask 100Hz, ControlTask 200Hz, MqttTask 30Hz).` (depends on T008, T009)

**Checkpoint**: US1 complete. Flash firmware, verify `[CTRL] WARNING` never appears over 5 minutes, tilt test shows gimbal PWM responding.

---

## Phase 4: User Story 2 — Concurrent, Non-Blocking Operation (Priority: P2)

**Goal**: Verify that all three tasks run at their specified rates simultaneously without any task starvation. Diagnostic counters and latency tracking allow independent validation.

**Independent Test**: Enable FIRMWARE_DEBUG; let glove run for 60 seconds; verify serial shows `[SCHED] 60s stats: sensor=6000 control=12000 mqtt=1800` (±10%); introduce deliberate 100ms delay in MqttTask (see quickstart.md Scenario 3) and verify sensor/control counts remain unchanged with 0 latency violations.

- [X] T011 [US2] Add execution counters, latency tracking, and 60-second diagnostic log to `firmware/src/task_scheduler.cpp` — add `static uint32_t s_sensor_count = 0`, `static uint32_t s_control_count = 0`, `static uint32_t s_mqtt_count = 0` at file scope; in `sensorTaskFn` loop, add `s_sensor_count++` after `xQueueOverwrite`; in `controlTaskFn` loop, add `s_control_count++` after `cmg_set_gimbal()`; add `static int64_t s_latency_max_us = 0` and `static uint32_t s_violation_count = 0` at file scope; in `controlTaskFn` after computing `latency_us`: update `if (latency_us > s_latency_max_us) s_latency_max_us = latency_us`; if `latency_us > 70000` also increment `s_violation_count`; add 60-second diagnostic block at the top of `controlTaskFn` loop: `static uint32_t s_diag_last_ms = 0; uint32_t now_ms = millis();` if `(now_ms - s_diag_last_ms) >= 60000`: print `[SCHED] 60s stats: sensor=%lu control=%lu mqtt=%lu`, print `[CTRL] Latency max=%.1fms violations=%lu`, reset counts and `s_latency_max_us`, update `s_diag_last_ms = now_ms`; wrap all diagnostic output in `#ifdef FIRMWARE_DEBUG` (depends on T009)

**Checkpoint**: US2 complete. 60s stats confirm ~6000/12000/1800 and latency violations=0.

---

## Phase 5: User Story 3 — Predictable Telemetry Rate (Priority: P3)

**Goal**: MQTT publish at 30Hz on Core 0 without disrupting SensorTask or ControlTask on Core 1. MQTT connection handled by MqttTask (not setup()), so MQTT failure never blocks the control loop.

**Independent Test**: Run `mosquitto_sub -t "tremo/sensors/+" -v | wc -l` for 60 seconds; expect ~1800 messages (1620–1980). Verify 60s stats still show sensor≈6000, control≈12000. See quickstart.md Scenario 4.

- [X] T012 [US3] Add MqttTask to `firmware/src/task_scheduler.cpp` and extend `scheduler_start()` — implement `mqttTaskFn(void*)`: call `mqtt_connect()` before the loop (non-fatal: log warning on false, FSM handles reconnect); declare `static FusedReading snapshot`; declare `TickType_t xLastWakeTime = xTaskGetTickCount()`; `for(;;)`: call `mqtt_loop()` (FSM keepalive — must run every tick for PUBACK processing); call `xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(100))`; populate `snapshot.battery_level = read_battery()`; call `publish_reading(&snapshot)`; `s_mqtt_count++`; call `vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(1000UL / MQTT_PUBLISH_RATE_HZ))`; in `scheduler_start()` after ControlTask creation: call `xTaskCreatePinnedToCore(mqttTaskFn, "MqttTask", MQTT_TASK_STACK, NULL, 5, &s_mqtt_handle, 0)`, log `[BOOT] MqttTask started (Core 0, prio 5, 30Hz)` (depends on T011)
- [X] T013 [US3] Remove MQTT init from `firmware/src/main.cpp` — in `setup()`: remove the `if (!mqtt_connect())` call and its `[WARN] MQTT connect failed` warning log (mqtt_connect is now called at MqttTask startup in mqttTaskFn); update the `[BOOT] Firmware running` log to explicitly note `MQTT connection handled by MqttTask on Core 0`; remove any remaining reference to `mqtt_connect()` from main.cpp (depends on T012, T010)

**Checkpoint**: US3 complete. mosquitto_sub confirms ~30Hz; MqttTask starts after SensorTask and ControlTask; MQTT failure/timeout does not affect 60s sensor/control counts.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate build health and update documentation. T014 and T015 can run in parallel.

- [X] T014 [P] Update `firmware/README.md` — add `031-freertos-scheduler` to the Features line; update Output line to note `SensorTask 100Hz, ControlTask 200Hz, MqttTask 30Hz`; add new `## FreeRTOS Task Scheduler` section describing the 3-task architecture, core assignments, priorities, and `vTaskDelayUntil()` timing; update Integration Architecture diagram to show the three tasks and the queue mailbox; add expected serial boot output showing all 3 task start messages; update Verify Operation section with expected 60s stats output (`[SCHED] 60s stats: sensor=6000 control=12000 mqtt=1800`) and latency log; add troubleshooting row for watchdog reset (`loop()` must call `vTaskDelete(NULL)`)
- [ ] T015 [P] Validate firmware build — run `pio run` [BLOCKED: PlatformIO not installed on this machine; run manually after `pip install platformio`] (compile only, no upload) from the `firmware/` directory and confirm zero compilation errors with all new and modified files (cmg.h/cpp, pid_controller.h/cpp, task_scheduler.h/cpp, modified main.cpp and mqtt_publisher.h); fix any compilation errors before proceeding; if `ADC_11db` fails, try `ADC_ATTEN_DB_11`
- [ ] T016 Run quickstart end-to-end validation [DEFERRED: requires physical ESP32 hardware + CMG assembly] — follow `specs/031-freertos-scheduler/quickstart.md`: Scenario 1 (verify 3-task boot and 60s counts), Scenario 2 (verify latency < 70ms over 5 minutes), Scenario 3 (inject 100ms MQTT delay, verify sensor/control counts unchanged), Scenario 4 (mosquitto_sub counts ~1800 in 60s); document any deviations from expected behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 starts immediately
- **Foundational (Phase 2)**: Depends on T001 — T002, T003, T004, T007 can run in parallel; T005 after T002; T006 after T003
- **US1 (Phase 3)**: Depends on full Phase 2 — T008 after T002–T007; T009 after T008; T010 after T009
- **US2 (Phase 4)**: Depends on T009 (same file) — T011 after T009
- **US3 (Phase 5)**: Depends on T011 — T012 after T011; T013 after T012 and T010
- **Polish (Phase 6)**: T014, T015 can run in parallel after T013; T016 after T014 and T015

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 completion — delivers core control loop
- **US2 (P2)**: Depends on T009 from US1 (extends same file with counters) — adds diagnostic observability
- **US3 (P3)**: Depends on T011 from US2 (adds mqtt_count to 60s stats) — adds telemetry task

### Within Phase 3 (US1)

```
T002, T003, T004, T007 (parallel)
         │
    T005 (after T002)    T006 (after T003)
         │                    │
         └────────────────────┘
                    │
                  T008
                    │
                  T009
                    │
                  T010
```

### Parallel Opportunities

- **Phase 2**: T002 ∥ T003 ∥ T004 ∥ T007 (all different files)
- **Phase 3**: T014 ∥ T015 (README vs pio run — different concerns)

---

## Parallel Example: Phase 2 (Foundational Headers)

```bash
# Step 1 — all headers in parallel:
Task: "Create firmware/include/cmg.h (T002)"
Task: "Create firmware/include/pid_controller.h (T003)"
Task: "Create firmware/include/task_scheduler.h (T004)"
Task: "Update firmware/include/mqtt_publisher.h (T007)"

# Step 2 — implementations (after their respective headers):
Task: "Create firmware/src/cmg.cpp (T005)"   # after T002
Task: "Create firmware/src/pid_controller.cpp (T006)"  # after T003

# Step 3 — task_scheduler.cpp (after all foundational complete):
Task: "Create firmware/src/task_scheduler.cpp with SensorTask (T008)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational — CMG, PID, FreeRTOS headers (T002–T007)
3. Complete Phase 3: User Story 1 — SensorTask + ControlTask + main.cpp (T008–T010)
4. **STOP and VALIDATE**: Flash firmware, verify ControlTask runs at 200Hz, oscilloscope confirms gimbal PWM responds to tilt, latency log shows 0 violations over 5 minutes
5. Demo: Tremor suppression loop is live

### Incremental Delivery

1. Setup + Foundational → Framework ready (T001–T007)
2. US1 complete → MVP control loop (T008–T010) — **demo-ready**
3. US2 complete → Diagnostic observability (T011) — parallel isolation proven
4. US3 complete → Telemetry streaming (T012–T013) — full system operational
5. Polish → Full validation (T014–T016)

---

## Notes

- [P] = different files, no blocking dependencies — safe to parallelize
- `firmware/src/task_scheduler.cpp` is modified by T008 (SensorTask), T009 (ControlTask), T011 (counters), T012 (MqttTask) — these MUST run sequentially
- `firmware/src/main.cpp` is modified by T010 (task creation) and T013 (remove MQTT init) — T010 before T013
- PID feedback is gyro angular velocity (`gX`/`gY`), NOT Kalman angle — confirmed by research; setpoint = 0 deg/s
- `vTaskDelete(NULL)` in `loop()` is mandatory — empty `loop()` starves the IDLE task and causes a watchdog reset within ~5 seconds
- `ledcSetup()` / `ledcAttachPin()` / `ledcWrite()` use 16-bit resolution (CMG_PWM_RESOLUTION=16) — do NOT use 8-bit
- `config.h` (gitignored) must be updated by the developer after T001 updates `config.h.example`
- Flywheel ESC arming sequence in `cmg_init()` requires a 2-second delay — this is normal; `cmg_init()` is called in `setup()` before `scheduler_start()`
