# Research: FreeRTOS Task Scheduler for Glove Control (Feature 031)

**Date**: 2026-02-19
**Branch**: `031-freertos-scheduler`

---

## Decision 1: FreeRTOS Task API — xTaskCreatePinnedToCore

**Decision**: Use `xTaskCreatePinnedToCore()` (not `xTaskCreate()`) for all three tasks.

**Rationale**: The ESP32 is a dual-core SoC. `xTaskCreate()` lets FreeRTOS schedule the task on either core unpredictably, which could place a control-critical task on Core 0 where the WiFi driver creates scheduling jitter. `xTaskCreatePinnedToCore()` guarantees deterministic core assignment:
- ControlTask and SensorTask pinned to Core 1 (isolated from WiFi)
- MqttTask pinned to Core 0 (co-located with WiFi stack to minimize cross-core mutex contention)

**API signature**:
```cpp
BaseType_t xTaskCreatePinnedToCore(
    TaskFunction_t pvTaskCode,   // task function
    const char*    pcName,       // debug name
    uint32_t       usStackDepth, // stack in bytes (not words, in Arduino ESP32)
    void*          pvParameters, // passed to task function
    UBaseType_t    uxPriority,   // 0 = lowest, configMAX_PRIORITIES-1 = highest
    TaskHandle_t*  pvCreatedTask, // output handle
    BaseType_t     xCoreID       // 0 or 1
);
```

**Alternatives considered**:
- `xTaskCreate()`: Rejected — non-deterministic core assignment undermines real-time guarantees
- Arduino `loop()` with millis() guards (current approach): Rejected — single-threaded; MQTT blocking can delay sensor reads

---

## Decision 2: FreeRTOS Priority Values

**Decision**: ControlTask=10, SensorTask=8, MqttTask=5.

**Rationale**: ESP-IDF (the underlying framework) reserves high priority values for system tasks:
- Idle tasks: priority 0
- Arduino `loop()` task (`loopTask`): priority 1
- ESP-IDF timer task: priority ~22
- WiFi/TCP stack tasks: priorities 3–23 (varies by task)

User tasks should use priorities 1–15 to avoid interfering with the WiFi driver. Our chosen values:
- 10 (ControlTask): High enough to preempt SensorTask and MqttTask, safely below WiFi driver tasks
- 8 (SensorTask): Preempts MqttTask; yields to ControlTask
- 5 (MqttTask, Core 0): Above idle; co-located with WiFi stack on Core 0 — does not compete with Core 1 tasks since FreeRTOS schedules per-core

**Key insight**: Priority comparisons only matter between tasks on the same core. Since ControlTask and SensorTask are both on Core 1, priority 10 > 8 is the relevant relationship. MqttTask on Core 0 at priority 5 never preempts Core 1 tasks regardless of its priority value.

**Alternatives considered**:
- Equal priorities: Rejected — round-robin scheduling cannot guarantee ControlTask gets CPU first when both it and SensorTask are ready simultaneously
- Priority 24 for ControlTask: Rejected — risks interfering with ESP-IDF watchdog and WiFi recovery tasks

---

## Decision 3: Periodic Timing — vTaskDelayUntil (not vTaskDelay)

**Decision**: All tasks use `vTaskDelayUntil(&xLastWakeTime, period_ticks)` for their sleep calls.

**Rationale**: `vTaskDelay(N)` sleeps for N ticks from the moment it is called. If the task body takes T ticks of computation, the actual period becomes T + N, causing cumulative drift. `vTaskDelayUntil()` sleeps until an absolute tick count, absorbing computation time transparently. This is essential for ControlTask (5ms jitter budget ±1ms) and SensorTask (10ms jitter budget ±1ms).

**Usage pattern**:
```cpp
void ControlTask(void* pvParams) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(5);  // 200Hz
    for (;;) {
        // ... task body ...
        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}
```

**ESP-IDF tick rate**: Default `CONFIG_FREERTOS_HZ = 1000` (1ms tick resolution), which is sufficient for 5ms (5 ticks), 10ms (10 ticks), and 33ms (33 ticks) periods.

**Alternatives considered**:
- `vTaskDelay()`: Rejected — causes period drift proportional to task execution time
- Hardware timer interrupt (`esp_timer_create()`): Overkill; FreeRTOS task scheduling provides sufficient timing accuracy for the ±1ms jitter budget
- `ets_delay_us()` busy-wait: Rejected — wastes CPU cycles, blocks other tasks

---

## Decision 4: Inter-Task Data Sharing — xQueueOverwrite/xQueuePeek Mailbox

**Decision**: Use a `QueueHandle_t g_sensor_mailbox` of length 1 with `xQueueOverwrite()` (writer) and `xQueuePeek()` (readers). Do NOT use a mutex-protected global struct.

**Rationale**:
- **`volatile` alone is incorrect**: On the ESP32's dual-core LX6, `volatile` prevents compiler optimization but provides no memory ordering guarantees. A reader on Core 0 can observe partial writes (bytes from the old and new struct values simultaneously). This is observable behavior, not theoretical.
- **Mutex + global struct has priority inversion risk**: If MqttTask (priority 5) holds the mutex during JSON serialization and ControlTask (priority 10) tries to read sensor data, ControlTask blocks. FreeRTOS priority inheritance mitigates but does not eliminate this. Any time ControlTask is blocked by MqttTask, the 70ms latency budget is at risk.
- **xQueueOverwrite + xQueuePeek**: A queue of length 1 acts as a thread-safe single-slot register ("mailbox"). `xQueueOverwrite()` never blocks and replaces the item atomically. `xQueuePeek()` reads without consuming, so both readers always see the latest value. No ownership semantics means no priority inversion is possible.

**Chosen pattern**:
```cpp
// Create once in setup() or before tasks start:
QueueHandle_t g_sensor_mailbox = xQueueCreate(1, sizeof(FusedReading));

// Writer (SensorTask, never blocks):
xQueueOverwrite(g_sensor_mailbox, &new_reading);

// Reader (ControlTask, 10ms timeout — should always have data within 10ms):
FusedReading snapshot;
if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(10)) == pdTRUE) {
    // use snapshot ...
}

// Reader (MqttTask, 100ms timeout):
FusedReading snapshot;
if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(100)) == pdTRUE) {
    publish_reading(&snapshot);
}
```

**Latency timestamp**: `FusedReading.t_sensor_us` is written by SensorTask before `xQueueOverwrite()`, then read from the peek snapshot by ControlTask — no additional synchronization needed.

**Alternatives rejected**:
- Mutex + global struct: Priority inversion risk on ControlTask (Core 1); blocking possible
- `volatile` global: Insufficient for dual-core — no memory ordering guarantees on LX6

---

## Decision 5: Replacing Arduino loop() with FreeRTOS Tasks

**Decision**: `loop()` calls `vTaskDelete(NULL)` to permanently delete `loopTask`. All periodic work moves to FreeRTOS tasks created in `setup()`.

**Critical watchdog issue**: In the ESP32 Arduino framework, `setup()` and `loop()` run inside a FreeRTOS task called `loopTask` (priority 1, Core 1). If `loop()` is left **empty** or returns immediately in a tight spin, `loopTask` never yields and the IDLE task (priority 0) never gets CPU time. Within ~5 seconds the FreeRTOS watchdog fires and resets the device with:
```
Task watchdog got triggered. Tasks not feeding watchdog: IDLE (CPU 1)
```

**Chosen pattern — `vTaskDelete(NULL)`** (cleanest):
```cpp
void setup() {
    // ... hardware init (serial, IMU, calibration, battery, MQTT) ...
    scheduler_start();  // creates all 3 tasks via xTaskCreatePinnedToCore
}

void loop() {
    vTaskDelete(NULL);  // delete loopTask permanently; frees its ~8KB stack
                        // IDLE task recovers and watchdog is satisfied
}
```

**Alternative — `vTaskDelay(portMAX_DELAY)`** (acceptable, slightly wasteful):
```cpp
void loop() {
    vTaskDelay(portMAX_DELAY);  // suspend forever; IDLE task runs; loopTask stack kept
}
```

Both are safe. `vTaskDelete(NULL)` is preferred because it reclaims `loopTask`'s ~8KB stack allocation.

**Additional pitfall**: Every FreeRTOS task function that returns without calling `vTaskDelete(NULL)` causes undefined behavior (likely crash). All three task bodies must loop forever (`for(;;)`) and only exit via `vTaskDelete(NULL)`.

**Alternatives rejected**:
- Keep `loop()` as the SensorTask body: `loop()` timing is less deterministic than `vTaskDelayUntil()` inside a dedicated task
- Empty `loop()` body: Causes watchdog reset within ~5 seconds

---

## Decision 6: Latency Measurement — esp_timer_get_time()

**Decision**: Use `esp_timer_get_time()` (returns `int64_t` microseconds since boot) for sensor-to-actuation latency measurement.

**Rationale**:
- `millis()` has 1ms resolution — insufficient to detect jitter at 5ms period
- `micros()` is suitable but internally calls `esp_timer_get_time()` / 1000 in recent ESP-IDF, adding indirection
- `esp_timer_get_time()` is the lowest-overhead, highest-resolution timer available on ESP32 (64-bit µs counter, no overflow risk for practical uptime)
- Directly available from `esp_timer.h` (included in ESP-IDF Arduino)

**Usage**: Record timestamp in SensorTask after Kalman update; carry it in `FusedReading.t_sensor_us`; compute delta in ControlTask after `cmg_set_torque()`.

---

## Decision 7: CMG Actuation via LEDC PWM — Two Channels, 16-bit Resolution

**Decision**: Two LEDC channels at 50Hz, 16-bit resolution — LEDC_CHANNEL_0 for gimbal servo (GPIO18), LEDC_CHANNEL_1 for flywheel ESC (GPIO19).

**Rationale**:
- **16-bit (65536 counts at 50Hz)** gives ~0.3µs resolution per count at 50Hz, enabling fine servo position control. 8-bit (256 counts) gives only ~78µs steps — too coarse for precise gimbal angle at ±60° range.
- **Two separate channels** are needed: flywheel ESC arms at 1000µs and runs at constant throttle; gimbal servo is updated by PID at 200Hz.
- **LEDC_LOW_SPEED_MODE**: Software-updated; correct for 50Hz. `LEDC_HIGH_SPEED_MODE` is for hardware-interrupt-driven updates (e.g., BLDC commutation) — not needed here.
- **GPIO18 (gimbal), GPIO19 (flywheel)**: Both are ADC2 pins, but `ledcWrite()` is unaffected by ADC2/WiFi conflict (only `analogRead()` is affected). GPIO27 is also valid; GPIO18/19 are chosen for physical proximity on typical ESP32 dev boards.

**Duty formula**: `duty = (pulse_us × 65536) / 20000`

| Signal | Pulse | Duty (16-bit) |
|--------|-------|---------------|
| Gimbal center (0°) | 1500µs | 4915 |
| Gimbal +60° | 2167µs | 7104 |
| Gimbal -60° | 833µs | 2730 |
| Flywheel arm | 1000µs | 3277 |
| Flywheel run | ~1600µs | ~5243 (tune per ESC) |

**LEDC initialization** (ESP-IDF style, compatible with Arduino ESP32):
```cpp
ledcSetup(GIMBAL_CHANNEL, 50, 16);   // 50Hz, 16-bit
ledcAttachPin(CMG_GIMBAL_PIN, GIMBAL_CHANNEL);
ledcWrite(GIMBAL_CHANNEL, 4915);     // center (1500µs)

ledcSetup(FLYWHEEL_CHANNEL, 50, 16);
ledcAttachPin(CMG_FLYWHEEL_PIN, FLYWHEEL_CHANNEL);
ledcWrite(FLYWHEEL_CHANNEL, 3277);   // arm ESC (1000µs)
```

**Alternatives considered**:
- 8-bit resolution: Rejected — only 256 steps across 20ms period; insufficient gimbal precision
- MCPWM peripheral: Overkill for hobby servo; would be appropriate if upgrading to brushless gimbal motor with FOC
- Single PWM channel: Rejected — flywheel ESC and gimbal servo have independent duty cycle requirements

---

## Decision 8: PID Design for Tremor Suppression

**Decision**: Two independent PID instances (roll-rate, pitch-rate); feedback is gyro angular velocity (not Kalman angle); setpoint = 0 deg/s; IIR derivative filter at ~20Hz cutoff; conditional integral clamping anti-windup.

**Feedback signal — gyro angular velocity, not Kalman angle**:
Parkinsonian tremor is a rhythmic oscillation at 4–8Hz. The gyroscope directly measures the rate of that oscillation — this is the signal to suppress. The Kalman-filtered angle has 5–10ms of integrated lag and is more useful for slow postural reference. For real-time tremor rejection, the gyro (gX for roll-rate, gY for pitch-rate) is the correct and scientifically validated feedback signal (confirmed by ELENA project, Gallego et al., and the anti-tremor glove literature).

**Setpoint = 0 deg/s**: Any non-zero angular velocity in the 4–8Hz band is pathological tremor. The PID drives that velocity toward zero. The hand should not be rotating in steady posture.

**Derivative IIR low-pass filter**: Raw derivative amplifies sensor noise above 30Hz (MPU9250 gyro noise is broadband). A first-order IIR filter at fc ≈ 20Hz (tau ≈ 0.008s) passes tremor-band dynamics without phase lag while strongly rejecting high-frequency noise.
```
d_raw  = (error - prev_error) / dt
alpha  = dt / (tau + dt)            // at tau=0.008, dt=0.005: alpha≈0.385
d_filt = alpha × d_raw + (1-alpha) × prev_deriv_filt
```

**Anti-windup — conditional clamping**: When PID output hits ±1.0 (saturated), do not update the integral accumulator. Hold the last valid integral value. Resume accumulation only when output returns within bounds.

**Initial tuning ranges for Parkinsonian tremor (4–8Hz)**:

| Gain | Starting Range | Notes |
|------|---------------|-------|
| Kp | 0.5 – 2.0 | Primary tremor response; start at 1.0, increase to oscillation margin then back off 30–40% |
| Ki | 0.0 – 0.05 | Very small; tremor suppression is dynamic, not steady-state; only add if persistent DC drift observed |
| Kd | 0.01 – 0.08 | Primary damping; increase until strong damping, reduce 20% if chattering |
| tau | 0.008 s | Derivative LPF time constant (fc ≈ 20Hz) |

**CMG dual-motor structure**: A CMG has two distinct motors — both driven by ESP32 PWM:
- **Flywheel motor (ESC + BLDC)**: Runs at constant high speed (set once at startup). PID does NOT control flywheel speed. Commands via 50Hz ESC PWM (1000–2000µs pulse).
- **Gimbal servo (RC servo)**: PID output commands gimbal angle. Gyroscopic precession of the spinning flywheel produces the suppression torque. Commands via 50Hz servo PWM (500–2500µs pulse).

**Output mapping chain**:
```
PID output [-1.0, +1.0] → gimbal angle [±60°] → pulse [833–2167 µs] → 16-bit LEDC duty
duty = (pulse_us × 65536) / 20000
```
Gimbal limited to ±60° (not ±90°) to avoid gimbal lock singularity.

**Alternatives considered**:
- Kalman angle as feedback: Rejected — 5–10ms filter lag degrades derivative at 200Hz; gyro is more direct
- Single SISO PID (roll only): Rejected — pitch tremor is equally significant
- State-space / model-based control: Deferred to future work; PID is tunable without a full CMG mechanical model
- Ki = 0.5: Rejected per research — tremor suppression is a dynamic rejection problem, not steady-state; high Ki causes windup during tremor bursts

---

## Summary: Key Technical Choices

| Area | Choice | Rationale |
|------|--------|-----------|
| Task API | `xTaskCreatePinnedToCore()` | Deterministic core assignment |
| Priorities | Control=10, Sensor=8, MQTT=5 | Hierarchy without WiFi interference |
| Core assignment | Control+Sensor → Core 1, MQTT → Core 0 | WiFi isolation |
| Periodic timing | `vTaskDelayUntil()` | Drift-free period |
| Shared data | `xQueueOverwrite`/`xQueuePeek` mailbox | No priority inversion risk; thread-safe on dual-core |
| `loop()` | `vTaskDelete(NULL)` | Frees stack, prevents watchdog reset (empty loop() crashes!) |
| Latency measurement | `esp_timer_get_time()` (µs) | Highest available resolution |
| CMG actuation | LEDC PWM, 2 channels (GPIO18 gimbal, GPIO19 flywheel), 50Hz, 16-bit | Servo precision + ESC arming |
| PID design | Dual SISO on gyro velocity (gX, gY), setpoint=0 deg/s, IIR deriv filter | Gyro feedback avoids Kalman lag; proven for tremor |
