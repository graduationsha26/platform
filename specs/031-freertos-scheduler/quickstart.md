# Quickstart: FreeRTOS Task Scheduler (Feature 031)

**Branch**: `031-freertos-scheduler`
**Prerequisites**: Feature 025 (IMU + Kalman), Feature 030 (MQTT publish) implemented and working

---

## Setup

### 1. Update config.h

Add the new Feature 031 constants to your `firmware/include/config.h`:

```c
// CMG actuation
#define CMG_PWM_PIN          27
#define CMG_PWM_CHANNEL       0
#define CMG_PWM_FREQ_HZ      50
#define CMG_PWM_RESOLUTION    8

// PID tuning (start conservative, tune after verifying latency)
#define PID_KP               2.0f
#define PID_KI               0.5f
#define PID_KD               0.05f
#define PID_OUTPUT_MIN     -100.0f
#define PID_OUTPUT_MAX      100.0f

// FreeRTOS task stack sizes
#define SENSOR_TASK_STACK   4096
#define CONTROL_TASK_STACK  4096
#define MQTT_TASK_STACK     8192
```

### 2. Build and flash

```bash
# Compile and verify (no upload)
cd firmware && pio run

# Build and flash to connected ESP32
pio run --target upload

# Open serial monitor (115200 baud)
pio device monitor
```

---

## Scenario 1: Verify 3-Task Concurrent Execution (US2)

**Goal**: Confirm all three tasks start and run at their specified rates.

**Expected serial output on boot**:

```
[BOOT] TremoAI Glove Firmware starting...
[IMU] WHO_AM_I OK (0x71)
[CALIB] Collecting 500 samples at 100Hz (~5 seconds)...
[CALIB] Done. Offsets: aX=... gX=...
[BOOT] Battery ADC initialized.
[MQTT] Connecting to WiFi SSID: YourNetwork
....
[MQTT] WiFi connected. IP: 192.168.1.105
[BOOT] CMG initialized (GPIO27, 50Hz PWM).
[BOOT] Starting FreeRTOS tasks...
[BOOT] SensorTask  started (Core 1, prio 8, 100Hz)
[BOOT] ControlTask started (Core 1, prio 10, 200Hz)
[BOOT] MqttTask    started (Core 0, prio 5, 30Hz)
[BOOT] Firmware running.
```

**After 60 seconds, check task execution counts** (printed every 60s in FIRMWARE_DEBUG mode):

```
[SCHED] 60s stats: sensor=6000 control=12000 mqtt=1800
```

Verify:
- `sensor ≈ 6000` (100Hz × 60s)
- `control ≈ 12000` (200Hz × 60s)
- `mqtt ≈ 1800` (30Hz × 60s)

---

## Scenario 2: Verify Sensor-to-Actuation Latency < 70ms (US1)

**Goal**: Confirm the ControlTask receives sensor data and issues actuation within 70ms.

Enable `FIRMWARE_DEBUG` in `platformio.ini`:

```ini
build_flags =
    -DFIRMWARE_DEBUG
    -DMQTT_MAX_PACKET_SIZE=512
```

**Expected serial output** (in FIRMWARE_DEBUG mode, every 1 second):

```
[CTRL] Latency: 6.2ms (max: 7.1ms, violations: 0)
[CTRL] Roll PID: err=1.23° out=2.46% torque=2.46
[CTRL] Pitch PID: err=-0.45° out=-0.90% torque=-0.90
```

Key fields:
- `Latency: X.Xms` — average sensor-to-actuation elapsed time
- `max: Y.Yms` — worst-case latency in the last 1s window
- `violations: N` — count of cycles where latency exceeded 70ms (must be 0)

**Pass criteria**: `violations: 0` sustained over 5 minutes (SC-001, SC-006).

---

## Scenario 3: Verify Telemetry Isolation (US2, SC-005)

**Goal**: Confirm that a slow telemetry publish does not cause sensor or control cycles to be skipped.

In `task_scheduler.cpp`, temporarily add a 100ms artificial delay in MqttTask:

```cpp
// TEST ONLY — inject delay to simulate slow network
vTaskDelay(pdMS_TO_TICKS(100));  // Add before publish_reading()
```

**Expected behavior** (serial output with FIRMWARE_DEBUG):

```
[SCHED] 60s stats: sensor=6000 control=12000 mqtt=1800
[MQTT] Slow publish: 103ms (expected ≤ 33ms) — isolated, no sensor/control impact
[CTRL] Latency: 6.4ms (max: 7.3ms, violations: 0)
```

Verify:
- Sensor and control counts remain ~6000 and ~12000 (no missed cycles)
- Latency violations remain 0
- MQTT count may be lower (~900 instead of 1800) due to the injected delay — this is acceptable

**Remove the test delay before production flash.**

---

## Scenario 4: Verify MQTT Rate at 30Hz (US3)

From another terminal on the same network:

```bash
mosquitto_sub -t "tremo/sensors/+" -v | ts '[%Y-%m-%d %H:%M:%.S]' | head -200
```

Count messages over 60 seconds:

```bash
timeout 60 mosquitto_sub -t "tremo/sensors/+" | wc -l
```

**Expected**: approximately 1800 messages (30Hz × 60s), range 1620–1980 (±10%).

---

## Scenario 5: Verify CMG Actuation Signal

Connect an oscilloscope or servo tester to GPIO27:

1. With glove flat and still (roll ≈ 0°, pitch ≈ 0°), verify PWM duty ≈ 50% (neutral, ~1.5ms pulse at 50Hz).
2. Tilt glove 10° forward (pitch ≈ 10°), verify PWM duty shifts toward maximum (PID responding to error).
3. Return glove to flat, verify PWM returns to neutral within ~200ms (PID settling).

**Expected PWM characteristics**:
- Frequency: 50Hz (20ms period)
- Neutral: ~1.5ms pulse (128/255 × 20ms)
- Full forward: ~2.0ms pulse (255/255 × 20ms)
- Full reverse: ~1.0ms pulse (0/255 × 20ms)

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Watchdog reset after ~5s | `loop()` is empty — starves IDLE task | `loop()` must call `vTaskDelete(NULL)` or `vTaskDelay(portMAX_DELAY)` |
| Tasks not starting | Stack overflow in setup() | Ensure `setup()` stack is sufficient; move task init to after all hardware setup |
| `sensor` count < 6000 | SensorTask preempted by ControlTask too long | Check ControlTask execution time with FIRMWARE_DEBUG |
| `violations > 0` | Mutex hold time too long | Reduce critical section size; never call MQTT inside mutex |
| CMG jitter / buzz | PID Kd too high | Reduce `PID_KD` in config.h; add low-pass filter on derivative |
| MqttTask hangs | MQTT library blocking publish | Ensure `mqttClient.publish()` is called with QoS 1; check FSM is in CONN_READY |
| Latency > 20ms | ControlTask priority too low | Verify `CONTROL_TASK_STACK` ≥ 4096 and prio = 10 in task_scheduler.cpp |
| `mqtt` count ≈ 0 | MqttTask not pinned to Core 0 | Verify `xTaskCreatePinnedToCore(mqttTaskFn, ..., 0)` — last arg is core |
