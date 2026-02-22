# Data Model: FreeRTOS Task Scheduler for Glove Control

**Feature**: 031-freertos-scheduler
**Scope**: Firmware data structures only — no backend database changes

This feature introduces no new database entities. All data entities are firmware-level C structs shared between FreeRTOS tasks via a mutex-protected global.

---

## Core Data Structures

### FusedReading (extended)

**Location**: `firmware/include/mqtt_publisher.h`
**Change**: Adds `t_sensor_us` field for latency measurement

```
FusedReading
├── aX, aY, aZ       float      Calibrated accelerometer (m/s²)
├── gX, gY, gZ       float      Calibrated gyroscope (°/s)
├── roll             float      Kalman-filtered roll angle (°) — firmware-internal
├── pitch            float      Kalman-filtered pitch angle (°) — firmware-internal
├── timestamp_iso    char[32]   ISO 8601 UTC string, populated by publish_reading()
├── battery_level    float      State of charge 0.0–100.0 (%)
└── t_sensor_us      uint64_t   esp_timer_get_time() at end of Kalman update (µs)
                                Used by ControlTask to compute sensor-to-actuation latency
```

**Written by**: SensorTask via `xQueueOverwrite(g_sensor_mailbox, &reading)` (every 10ms, non-blocking)
**Read by**: ControlTask via `xQueuePeek(g_sensor_mailbox, &snapshot, 10ms)` (every 5ms); MqttTask via `xQueuePeek(...)` (every 33ms)
**Protected by**: FreeRTOS queue internal synchronization — no separate mutex needed

---

### PidController

**Location**: `firmware/include/pid_controller.h` (NEW)

```
PidController
├── Kp               float   Proportional gain (initial default: 1.0)
├── Ki               float   Integral gain (initial default: 0.01)
├── Kd               float   Derivative gain (initial default: 0.03)
├── tau              float   Derivative LPF time constant in seconds (default: 0.008 → fc≈20Hz)
├── dt               float   Control period in seconds (fixed: 0.005 for 200Hz)
├── setpoint         float   Target angular velocity in deg/s (default: 0.0)
├── integral         float   Accumulated Ki×error×dt (held when output saturated)
├── prev_error       float   Error at previous update() call
├── prev_deriv_filt  float   Previous filtered derivative value (IIR state)
├── out_min          float   Lower output clamp (default: -1.0 normalized)
└── out_max          float   Upper output clamp (default: +1.0 normalized)
```

**Input**: `FusedReading.gX` (roll-rate) and `FusedReading.gY` (pitch-rate) — gyro angular velocity in deg/s, NOT Kalman angle
**Lifecycle**: Two instances initialized once in ControlTask startup; each updated every 5ms
**Anti-windup rule**: When output hits out_min/out_max (saturated), do not update `integral` — hold last valid value
**Derivative filter**: `alpha = dt / (tau + dt)`; `d_filt = alpha × d_raw + (1-alpha) × prev_deriv_filt`

---

### TaskSchedulerConfig

**Location**: `firmware/include/task_scheduler.h` (NEW)

```
Task handles (TaskHandle_t)
├── g_sensor_task_handle    TaskHandle_t   SensorTask handle (Core 1, prio 8)
├── g_control_task_handle   TaskHandle_t   ControlTask handle (Core 1, prio 10)
└── g_mqtt_task_handle      TaskHandle_t   MqttTask handle (Core 0, prio 5)

Shared mailbox (queue-based, length 1)
└── g_sensor_mailbox        QueueHandle_t  Latest FusedReading; written by xQueueOverwrite,
                                           read by xQueuePeek (no ownership, no priority inversion)
```

---

### CmgInterface

**Location**: `firmware/include/cmg.h` (NEW)
**Note**: Two LEDC channels — gimbal servo (PID-controlled) + flywheel ESC (constant speed)

```
cmg_init()
  - LEDC channel 0 (gimbal, GPIO CMG_GIMBAL_PIN): 50Hz, 16-bit, center at 1500µs (duty 4915)
  - LEDC channel 1 (flywheel, GPIO CMG_FLYWHEEL_PIN): 50Hz, 16-bit, arm at 1000µs (duty 3277)
  - Arming sequence: hold 1000µs for 2s (ESC arming), then ramp to CMG_FLYWHEEL_DUTY

cmg_set_gimbal(float output_normalized)
  output_normalized: float, range [-1.0, +1.0]
  mapping:   output → gimbal angle [±CMG_GIMBAL_MAX_DEG (60°)]
             angle → pulse_us [833–2167 µs]
             pulse_us → duty = (pulse_us × 65536) / 20000

  Called every 5ms (200Hz) from ControlTask.
  LEDC hardware holds last duty until next update — safe to call faster than servo 50Hz period.
```

---

## Data Flow Diagram

```
SensorTask (100Hz, Core 1)
   │
   ├─ read_raw_sample()         → RawSample
   ├─ apply_calibration()       → CalibratedSample
   ├─ kalman_update() × 2      → roll, pitch
   ├─ esp_timer_get_time()      → t_sensor_us
   └─ xQueueOverwrite(g_sensor_mailbox, &reading)  // never blocks
                │
                ▼ (queue mailbox — thread-safe, no priority inversion)
   ┌────────────────────────────────────────────┐
   │      g_sensor_mailbox (QueueHandle_t)      │
   │      length=1, sizeof(FusedReading)        │
   └────────────────────────────────────────────┘
         │                          │
         ▼ (every 5ms)              ▼ (every 33ms)
  ControlTask (200Hz, Core 1)   MqttTask (30Hz, Core 0)
   ├─ xQueuePeek(mailbox, &s)   ├─ xQueuePeek(mailbox, &s)
   ├─ pid_update(&pid_roll,       ├─ read_battery()
   │    snapshot.roll, 0.005f)   └─ publish_reading(&snapshot)
   ├─ pid_update(&pid_pitch,
   │    snapshot.pitch, 0.005f)
   ├─ torque = combine(roll_out, pitch_out)
   ├─ cmg_set_torque(torque)
   └─ latency_us = now - snapshot.t_sensor_us
      (log if > 70000 µs)
```

---

## Config Constants (config.h.example additions)

```c
// ─── CMG Actuation ────────────────────────────────────────────────────────────
// Two LEDC channels: gimbal servo (PID-driven) + flywheel ESC (constant speed)
#define CMG_GIMBAL_PIN        18      // GPIO18 — gimbal servo signal
#define CMG_GIMBAL_CHANNEL     0      // LEDC channel 0
#define CMG_FLYWHEEL_PIN      19      // GPIO19 — flywheel ESC signal
#define CMG_FLYWHEEL_CHANNEL   1      // LEDC channel 1
#define CMG_PWM_FREQ_HZ       50      // 50Hz (servo/ESC standard)
#define CMG_PWM_RESOLUTION    16      // 16-bit duty (0–65535); duty = pulse_us × 65536 / 20000
#define CMG_GIMBAL_MAX_DEG  60.0f     // ±60° gimbal range (avoid gimbal lock at ±90°)
#define CMG_FLYWHEEL_DUTY   5243      // ~1600µs constant flywheel throttle (tune per ESC)

// ─── PID Controller Tuning ────────────────────────────────────────────────────
// Feedback: gyro angular velocity (gX for roll-rate, gY for pitch-rate), setpoint = 0 deg/s
// Tuning targets for Parkinsonian tremor (4–8Hz oscillation):
#define PID_KP               1.0f    // Proportional gain — start here, increase to oscillation limit then -30%
#define PID_KI               0.01f   // Integral gain — very small; increase only if DC drift observed
#define PID_KD               0.03f   // Derivative gain — primary damping term
#define PID_TAU              0.008f  // Derivative LPF time constant (fc ≈ 20Hz)
#define PID_OUTPUT_MIN      -1.0f    // Normalized output min (maps to -60° gimbal)
#define PID_OUTPUT_MAX       1.0f    // Normalized output max (maps to +60° gimbal)

// ─── FreeRTOS Task Stack Sizes ────────────────────────────────────────────────
#define SENSOR_TASK_STACK   6144     // bytes — IMU read + Kalman filter + I2C driver call depth
#define CONTROL_TASK_STACK  4096     // bytes — PID computation + CMG LEDC write
#define MQTT_TASK_STACK     8192     // bytes — JSON serialization + MQTT library
```

---

## Validation Rules

| Field | Constraint | Enforcement |
|-------|------------|-------------|
| `output_normalized` to `cmg_set_gimbal()` | Must be [-1.0, +1.0] | `constrain()` in cmg.cpp before angle conversion |
| `PID_KP`, `PID_KD` | Must be > 0.0 | Config comment; `PID_KI` may be 0.0 (valid) |
| `CMG_GIMBAL_PIN`, `CMG_FLYWHEEL_PIN` | ADC2 pins OK for `ledcWrite()` | Only `analogRead()` conflicts with WiFi; LEDC is safe |
| FreeRTOS task stack | Must be ≥ 2048 bytes | Static assert in task_scheduler.cpp |
| Latency `latency_us` | Target < 70,000 µs | Log WARNING if exceeded (not a halt condition) |
