# Implementation Plan: FreeRTOS Task Scheduler for Glove Control

**Branch**: `031-freertos-scheduler` | **Date**: 2026-02-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/031-freertos-scheduler/spec.md`

## Summary

Replace the current single-threaded Arduino `loop()` with three dedicated FreeRTOS tasks pinned to specific ESP32 cores: a SensorTask (100Hz, Core 1), a ControlTask (200Hz, Core 1, highest priority), and an MqttTask (30Hz, Core 0). A PID controller drives CMG torque actuation. Shared sensor data is protected by a FreeRTOS mutex. End-to-end sensor-to-actuation latency is measured and logged; target is <70ms.

## Technical Context

**Platform**: ESP32 (Xtensa LX6, dual-core 240MHz), ESP-IDF Arduino framework via PlatformIO
**Firmware Language**: C++ (Arduino/ESP-IDF)
**RTOS**: FreeRTOS (built into ESP-IDF — no additional library required)
**Existing Libraries**: `256dpi/arduino-mqtt`, `bblanchon/ArduinoJson`, `Lauszus/KalmanFilter` (from Features 025, 030)
**New Libraries**: None — FreeRTOS primitives are part of the ESP32 Arduino framework
**Performance Goals**:
  - Sensor-to-actuation end-to-end latency < 70ms (FR-001, SC-001)
  - ControlTask jitter < ±1ms (SC-002)
  - SensorTask jitter < ±1ms, 0 missed samples (SC-003)
  - MqttTask rate: 30Hz ±10% (SC-004)
**Constraints**: Local development; no Docker; firmware only (no backend changes required)
**Scale/Scope**: Single glove device; all changes are in `firmware/` directory

### FreeRTOS Architecture

```
Core 0 (WiFi/TCP stack)           Core 1 (Real-time tasks)
┌──────────────────────┐          ┌───────────────────────────────┐
│ WiFi stack (prio 23) │          │ ControlTask (prio 10, 200Hz)  │
│ TCP/IP (prio 18)     │          │   → PID → cmg_set_torque()    │
│ MqttTask (prio 5)    │          │                               │
│   → mqtt_loop()      │◄─mutex─► │ SensorTask (prio 8, 100Hz)    │
│   → publish_reading()│          │   → IMU read → Kalman update  │
└──────────────────────┘          └───────────────────────────────┘
          ▲                                     │
          │         g_latest_fused (mutex)      │
          └─────────────────────────────────────┘
```

### Task Configuration

| Task        | Core | Priority | Period  | vTaskDelayUntil tick |
|-------------|------|----------|---------|----------------------|
| ControlTask | 1    | 10       | 5ms     | pdMS_TO_TICKS(5)     |
| SensorTask  | 1    | 8        | 10ms    | pdMS_TO_TICKS(10)    |
| MqttTask    | 0    | 5        | 33ms    | pdMS_TO_TICKS(33)    |

**Priority rationale**:
- ControlTask at 10 > SensorTask at 8 > MqttTask at 5 (ESP-IDF WiFi runs at 23 on Core 0; our tasks use lower priorities that do not compete with the WiFi driver)
- Core 0 assignment for MqttTask avoids cross-core lock contention with the WiFi/TCP stack
- `vTaskDelayUntil()` (not `vTaskDelay()`) provides drift-free periodic timing

### Shared Data Pattern — Queue Mailbox

`xQueueOverwrite`/`xQueuePeek` is used instead of a mutex+global. A mutex creates priority inversion risk: if MqttTask (prio 5) holds the mutex during JSON serialization, ControlTask (prio 10) can block — violating the 70ms latency budget. A length-1 queue acts as a thread-safe mailbox with no ownership and no blocking for the writer.

```cpp
// Create once before tasks start (firmware/src/task_scheduler.cpp):
QueueHandle_t g_sensor_mailbox = xQueueCreate(1, sizeof(FusedReading));

// Writer (SensorTask — never blocks):
xQueueOverwrite(g_sensor_mailbox, &new_reading);

// Reader (ControlTask — 10ms timeout, always has fresh data):
FusedReading snapshot;
if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(10)) == pdTRUE) {
    // run PID with snapshot ...
}

// Reader (MqttTask — 100ms timeout):
FusedReading snapshot;
if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(100)) == pdTRUE) {
    publish_reading(&snapshot);
}
```

**`loop()` pattern**: Must call `vTaskDelete(NULL)` — an empty `loop()` starves the IDLE task and triggers a watchdog reset within ~5 seconds.
```cpp
void loop() { vTaskDelete(NULL); }  // frees loopTask stack (~8KB)
```

### PID Controller Design

```
Input:   FusedReading.gX (roll-rate, deg/s) and FusedReading.gY (pitch-rate, deg/s)
         ← gyro angular velocity, NOT Kalman angle (gyro captures tremor directly, no filter lag)
Setpoint: 0.0 deg/s (suppress all angular velocity — any rotation in 4–8Hz band is tremor)
Output:  normalized [-1.0, +1.0] → gimbal angle [±60°] → servo pulse [833–2167 µs]
Rate:    200Hz (dt = 0.005s)
```

**PID struct fields**: `Kp`, `Ki`, `Kd`, `tau` (derivative LPF constant), `dt`, `setpoint`, `integral`, `prev_error`, `prev_deriv_filt`, `out_min`, `out_max`
**Anti-windup**: Conditional clamping — hold integral (do not update) when output is saturated
**Derivative filter**: IIR low-pass at fc≈20Hz (`alpha = dt/(tau+dt)`, tau=0.008s)

**Initial tuning targets for Parkinsonian tremor (4–8Hz oscillation)**:
- `Kp = 1.0` — start conservative, increase to oscillation margin then back off 30–40%
- `Ki = 0.01` — very small; tremor suppression is dynamic rejection, not steady-state compensation
- `Kd = 0.03` — primary damping; increase until strong tremor damping, reduce 20% if chattering
- `tau = 0.008` — derivative LPF time constant (fc ≈ 20Hz)

### CMG Actuation Interface — Two LEDC Channels, 16-bit

A CMG has two motor subsystems, both driven by ESP32 LEDC PWM at 50Hz, 16-bit resolution:

| Channel | Motor | GPIO | Pulse Range | Control |
|---------|-------|------|-------------|---------|
| LEDC_CHANNEL_0 | Gimbal servo | GPIO18 | 833–2167 µs (±60°) | PID output (every 5ms) |
| LEDC_CHANNEL_1 | Flywheel ESC | GPIO19 | 1000–2000 µs | Constant speed (set once at startup) |

**Duty formula**: `duty = (pulse_us × 65536) / 20000`
**Output mapping**: PID [-1.0,+1.0] → gimbal [±60°] → pulse [833–2167µs] → 16-bit duty [2730–7104]
**Flywheel**: Arms at 1000µs (duty 3277); runs at ~1600µs constant (duty ~5243) after ESC arming delay

### Latency Measurement

```cpp
// In SensorTask: record timestamp after Kalman update
uint64_t t_sensor_us = esp_timer_get_time();  // microseconds since boot

// In ControlTask: measure elapsed time after cmg_set_torque()
uint64_t t_actuate_us = esp_timer_get_time();
int64_t latency_us = t_actuate_us - snapshot.t_sensor_us;
// Log if FIRMWARE_DEBUG enabled; assert < 70000 (70ms)
```

The `FusedReading` struct gains a `uint64_t t_sensor_us` field to carry the timestamp from SensorTask to ControlTask.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature is firmware-only (ESP32 C++ in `firmware/`). The TremoAI constitution governs the web platform (`backend/` + `frontend/`). Constitution items are evaluated for applicability:

- [X] **Monorepo Architecture**: All firmware code resides in `firmware/` within the monorepo — ✅
- [X] **Tech Stack Immutability**: FreeRTOS is part of the ESP32 Arduino framework (not an additional library); no new external libraries added — ✅
- [X] **Database Strategy**: No database involvement — N/A ✅
- [X] **Authentication**: No authentication involvement — N/A ✅
- [X] **Security-First**: `config.h` remains gitignored; CMG pin and PID constants go in `config.h.example` — ✅
- [X] **Real-time Requirements**: No backend WebSocket changes — N/A ✅
- [X] **MQTT Integration**: MqttTask continues to use the Feature 030 MQTT publish pipeline — ✅
- [X] **AI Model Serving**: No model serving — N/A ✅
- [X] **API Standards**: No REST endpoints — N/A ✅
- [X] **Development Scope**: Local firmware development only — ✅

**Result**: ✅ PASS — No constitution violations. Firmware features are an established part of the project (Features 025, 030 precedent).

## Project Structure

### Documentation (this feature)

```text
specs/031-freertos-scheduler/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (firmware only)

```text
firmware/
├── include/
│   ├── config.h.example        MODIFIED — add CMG_PWM_PIN, PID tuning constants, task stack sizes
│   ├── cmg.h                   NEW — CMG actuation interface (cmg_init, cmg_set_torque)
│   ├── pid_controller.h        NEW — PID controller struct + API
│   ├── task_scheduler.h        NEW — FreeRTOS task handles, shared mutex, g_latest_fused declaration
│   └── mqtt_publisher.h        MODIFIED — add t_sensor_us field to FusedReading struct
├── src/
│   ├── cmg.cpp                 NEW — LEDC PWM implementation
│   ├── pid_controller.cpp      NEW — PID update function with anti-windup
│   ├── task_scheduler.cpp      NEW — SensorTask, ControlTask, MqttTask function bodies
│   └── main.cpp                MODIFIED — setup() creates 3 FreeRTOS tasks, loop() emptied
└── platformio.ini              UNCHANGED — no new libraries required
```

**No backend, frontend, or database changes required.**
