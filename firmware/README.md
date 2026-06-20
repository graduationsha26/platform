# TremoAI Smart Glove Firmware

**Features**: 025-imu-kalman-fusion, 030-esp32-mqtt, 031-freertos-scheduler
**MCU**: ESP32 (ESP-IDF Arduino framework, dual-core Xtensa LX6 240MHz)
**Sensor**: MPU6500 6-axis IMU (SPI; accelerometer + gyroscope, no magnetometer)
**Algorithm**: Lauszus 2-state Kalman filter for roll + pitch (MQTT telemetry only); single-axis PID (TARGET_TREMOR_AXIS) for tremor suppression — feedback is raw gyro, not Kalman-filtered
**Output**: SensorTask 100Hz, ControlTask 200Hz, MqttTask 30Hz (JSON → `tremo/sensors/{DEVICE_SERIAL}`)

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| PlatformIO Core or IDE | ≥6.x | https://platformio.org/install |
| ESP32 Arduino platform | ≥5.x | Auto-installed by PlatformIO |
| Mosquitto (MQTT broker) | any | `sudo apt install mosquitto` / `brew install mosquitto` |
| Python 3 | ≥3.10 | For Django backend (separate) |

---

## Setup

### 1. Create your `config.h`

```bash
cp firmware/include/config.h.example firmware/include/config.h
```

Edit `firmware/include/config.h` and fill in:

```c
#define DEVICE_SERIAL    "GLOVE001A"       // Must match Django admin Device record
#define WIFI_SSID        "your_network"
#define WIFI_PASSWORD    "your_password"
#define MQTT_BROKER_HOST "192.168.1.100"   // IP of machine running Mosquitto
#define MQTT_BROKER_PORT 1883

// CMG actuation — adjust GPIO pins for your wiring
#define CMG_GIMBAL_PIN   12    // GPIO12 — gimbal servo signal
#define CMG_FLYWHEEL_PIN 14    // GPIO14 — flywheel ESC signal

// PID tuning — bench-validated values (run_zizo); tune after verifying latency < 70ms
#define PID_KP  2.0f
#define PID_KI  0.0f
#define PID_KD  0.05f
```

> **Security**: `config.h` is in `.gitignore` — never commit real credentials.

### 2. Register the device in Django admin

1. Start the TremoAI backend: `python manage.py runserver`
2. Go to Django admin → Devices → Add Device
3. Set `serial_number` = value of `DEVICE_SERIAL` in `config.h`
4. Pair the device to a patient

### 3. Start MQTT broker

```bash
mosquitto -v          # Verbose mode — shows all incoming messages
```

---

## Build and Upload

```bash
# Build firmware (compile only, no upload)
pio run

# Build and upload to connected ESP32
pio run --target upload

# Open serial monitor (115200 baud)
pio device monitor
```

For verbose debug logging (60-second stats, latency tracking), enable `FIRMWARE_DEBUG` in `platformio.ini`:

```ini
build_flags =
    -DFIRMWARE_DEBUG
    -DMQTT_MAX_PACKET_SIZE=512
```

---

## FreeRTOS Task Scheduler

Feature 031 replaces the single-threaded Arduino `loop()` with three dedicated FreeRTOS tasks:

| Task        | Core | Priority | Period | Rate  | Responsibility                                  |
|-------------|------|----------|--------|-------|-------------------------------------------------|
| SensorTask  | 1    | 8        | 10ms   | 100Hz | IMU read → Kalman fusion → sensor mailbox write |
| ControlTask | 1    | 10       | 5ms    | 200Hz | PID → CMG gimbal actuation → latency log        |
| MqttTask    | 0    | 5        | 33ms   | 30Hz  | Battery read → JSON publish via MQTT            |

**Core assignment**:
- Core 1: SensorTask + ControlTask (isolated from WiFi/TCP driver jitter)
- Core 0: MqttTask + WiFi/TCP stack (co-located to minimize cross-core data transfer)

**Shared data**: Length-1 FreeRTOS queue mailbox (`g_sensor_mailbox`)
- SensorTask writes via `xQueueOverwrite` (never blocks)
- ControlTask and MqttTask read via `xQueuePeek` (non-destructive, both see latest value)
- No mutex required — eliminates priority inversion risk between ControlTask and MqttTask

**Timing**: All tasks use `vTaskDelayUntil()` — drift-free periodic scheduling (not `vTaskDelay()`).

**PID Controller**: Single instance on `TARGET_TREMOR_AXIS` (`gX` or `gY` in deg/s, see `config.h`), setpoint = 0 deg/s. Raw finite-difference derivative (no pre-filter, no deadband), fixed integral clamp (`PID_INTEGRAL_CLAMP = ±100`). Output is unclamped — normalization happens in `cmg_set_gimbal()`. Bench-validated (`run_zizo`).

**CMG actuation**: Two LEDC channels at 50Hz, 16-bit resolution:
- Gimbal servo (GPIO12): PID-driven — raw output normalized (÷`CMG_TORQUE_FULL_SCALE`), slew-limited (`CMG_TORQUE_SLEW_PER_S`), then mapped directly to a pulse width (`CMG_GIMBAL_CENTER_US` ± `CMG_GIMBAL_SPAN_US`, clamped to `[CMG_GIMBAL_MIN_US, CMG_GIMBAL_MAX_US]`), updated at 200Hz
- Flywheel ESC (GPIO14): Armed at `CMG_ESC_ARM_PULSE_US` (1000µs) for `CMG_ESC_ARM_MS` (5s), then commands a constant `CMG_ESC_RUN_PULSE_US` (1080µs) — no retry, no spin-up verification

---

## Verify Operation

### Serial monitor output (expected on successful boot)

```
[BOOT] TremoAI Glove Firmware starting...
[IMU] WHO_AM_I OK (0x71)
[IMU] Magnetometer disabled (AK8963 isolated — zero latency impact)
[CALIB] Collecting 500 samples at 100Hz (~5 seconds)...
[CALIB] Done. Offsets:
[CALIB]   aX=0.0123 aY=-0.0045 aZ=-0.0621 m/s2
[CALIB]   gX=0.2341 gY=-0.1823 gZ=0.0912 deg/s
[BOOT] Battery ADC initialized.
[CMG] Flywheel armed (1000us) and running (1080us). Gimbal (ch0), Flywheel (ch1)
[BOOT] CMG initialized (GPIO12 gimbal, GPIO14 flywheel, 50Hz 16-bit, ESC armed at 1000us/5s then constant 1080us run).
[BOOT] SensorTask  started (Core 1, prio 8, 100Hz)
[BOOT] ControlTask started (Core 1, prio 10, 200Hz)
[BOOT] MqttTask    started (Core 0, prio 5, 30Hz)
[BOOT] FreeRTOS tasks started.
[BOOT] Firmware running — FreeRTOS task scheduler active (SensorTask 100Hz, ControlTask 200Hz, MqttTask 30Hz). MQTT connection handled by MqttTask on Core 0.
[MQTT] Connecting to WiFi SSID: YourNetwork
....
[MQTT] WiFi connected. IP: 192.168.1.105
[MQTT] NTP initialized.
[MQTT] Connecting to broker 192.168.1.100:1883 as GLOVE001A
[MQTT] Broker connected.
[MQTT] Publishing to topic: tremo/sensors/GLOVE001A
```

### 60-second execution statistics (FIRMWARE_DEBUG mode)

After 60 seconds, the ControlTask prints:

```
[SCHED] 60s stats: sensor=6000 control=12000 mqtt=1800
[CTRL]  Latency max=6.2ms violations=0
```

Expected values (±10%):
- `sensor ≈ 6000` (100Hz × 60s)
- `control ≈ 12000` (200Hz × 60s)
- `mqtt ≈ 1800` (30Hz × 60s)
- `violations: 0` (all sensor-to-actuation latency < 70ms)

### Test MQTT output (from another terminal)

```bash
mosquitto_sub -t "tremo/sensors/+" -v
```

Expected output (~30 messages/second):

```
tremo/sensors/GLOVE001A {"device_id":"GLOVE001A","timestamp":"2026-02-18T10:30:00.123Z","aX":0.1234,"aY":-0.0456,"aZ":0.0789,"gX":1.2345,"gY":-0.8765,"gZ":0.3456,"battery_level":87.5}
```

Count messages over 60 seconds (expect ~1800, range 1620–1980):

```bash
timeout 60 mosquitto_sub -t "tremo/sensors/+" | wc -l
```

### Verify database storage

```bash
python manage.py shell -c "
from biometrics.models import BiometricReading
import time
c1 = BiometricReading.objects.count()
time.sleep(10)
c2 = BiometricReading.objects.count()
print(f'Rate: {(c2-c1)/10:.1f} readings/s (expected ~30/s)')
"
```

### QoS 1 Delivery Verification

Run Mosquitto in verbose mode and observe that every PUBLISH is acknowledged with a PUBACK:

```bash
mosquitto -v
```

Every `PUBLISH (q1)` from the glove must have a corresponding `Sending PUBACK` entry.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Watchdog reset after ~5s | `loop()` is empty or tight-spinning — starves IDLE task | `loop()` must call `vTaskDelete(NULL)` (never leave empty) |
| `WHO_AM_I=0xFF` | I2C wiring issue | Check SDA→GPIO21, SCL→GPIO22, pull-ups (4.7kΩ) |
| `WHO_AM_I=0x70` | MPU6500 variant | Change `MPU_WHO_AM_I_VAL` to `0x70` in `imu.h` |
| CALIB MOTION DETECTED | Glove moved during startup | Power-cycle with glove flat and still |
| `WiFi connect timeout` | Wrong SSID/password or 5GHz network | Check credentials; ESP32 is 2.4GHz only |
| `Broker connect failed` | Wrong IP or broker not running | Verify Mosquitto is running; check MQTT_BROKER_HOST |
| No records in Django DB | Device serial not registered | Add device in Django admin matching DEVICE_SERIAL |
| `battery_level: 0` in all messages | `battery_init()` not called or wrong pin | Verify `BATTERY_ADC_PIN=34` (ADC1) in `config.h` |
| `QoS shows 0 in broker log` | Wrong MQTT library | Ensure `256dpi/arduino-mqtt @ ^2.5.0` in `platformio.ini` |
| Kalman output drifts | R_measure too low | Increase `KF_R_MEASURE` to 0.05–0.10 in `config.h` |
| `violations > 0` in 60s stats | ControlTask blocked too long | Reduce MQTT task priority or critical section size |
| CMG jitter / buzz | PID Kd too high, or slew rate too fast | Reduce `PID_KD` in `config.h`, or lower `CMG_TORQUE_SLEW_PER_S` |
| `sensor` count < 6000 in 60s | SensorTask starved | Verify ControlTask execution time; check SENSOR_TASK_STACK ≥ 6144 |
| `mqtt` count ≈ 0 | MqttTask not on Core 0 | Verify `xTaskCreatePinnedToCore(mqttTaskFn, ..., 0)` in task_scheduler.cpp |
| Latency > 20ms | ControlTask priority wrong | Verify ControlTask prio=10 and CONTROL_TASK_STACK ≥ 4096 |

---

## Kalman Filter Tuning

Default values in `config.h.example` work for most setups. If you need to adjust:

| Parameter | Default | Effect of Increase |
|---|---|---|
| `KF_Q_ANGLE` | 0.001 | Filter reacts faster to real motion |
| `KF_Q_BIAS` | 0.003 | Bias estimate updates faster (temperature changes) |
| `KF_R_MEASURE` | 0.03 | Trust gyro more; reduce accel noise sensitivity |
| `KF_R_MEASURE_DYNAMIC` | 0.09 | More gyro trust during active tremor (3× static) |

See `specs/025-imu-kalman-fusion/research.md` for full tuning rationale.

---

## PID Tuning (Feature 031)

Default values are bench-validated (`run_zizo`). Tune in order:

| Parameter | Default | Tuning Guidance |
|---|---|---|
| `PID_KP` | 2.0 | Increase until oscillation margin, then reduce 30–40% |
| `PID_KI` | 0.0 | Disabled by default — only enable if persistent DC drift observed |
| `PID_KD` | 0.05 | Increase until strong damping; reduce if chattering |
| `PID_INTEGRAL_CLAMP` | 100.0 | Anti-windup bound on accumulated integral — leave unchanged |
| `CMG_TORQUE_SLEW_PER_S` | 40.0 | Max torque change per second — lower if gimbal motion is too abrupt |

See `specs/031-freertos-scheduler/research.md` Decision 8 for tremor suppression PID rationale.

---

## Integration Architecture

```
MPU6500 ──SPI──► imu.cpp
                     │ RawSample (100Hz)
                     ▼
             apply_calibration()
                     │ CalibratedSample
                     ▼
             kalman_update() × 2          ← SensorTask (Core 1, prio 8)
                     │ roll, pitch, gX, gY, t_sensor_us
                     ▼
          g_sensor_mailbox (QueueHandle_t, length 1)
          ┌──────────────────────────┐
          │ xQueueOverwrite (write)  │
          │ xQueuePeek × 2 (read)   │
          └──────────────────────────┘
                  │                │
                  ▼ (5ms)          ▼ (33ms)
         ControlTask             MqttTask
         (Core 1, prio 10)       (Core 0, prio 5)
         pid_update()             read_battery()
         (TARGET_TREMOR_AXIS)    publish_reading()
         cmg_set_gimbal()             │
         latency check                ▼
                               MQTT broker (Mosquitto)
                                      │
                                      ▼
                           backend/realtime/mqtt_client.py
                                      │
                                      ▼
                              BiometricReading (PostgreSQL)
```

Note: `kalman_update()` (roll/pitch) feeds only the MQTT telemetry payload — the
PID control loop reads raw gyro (`gX`/`gY`) directly, not the Kalman-filtered angle.
