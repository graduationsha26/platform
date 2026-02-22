# Quickstart: ESP32 WiFi + MQTT Client (Feature 030)

**Branch**: `030-esp32-mqtt`
**Date**: 2026-02-19

---

## Integration Scenario 1 (US1): Glove Powers On and Streams Data

**Goal**: Verify the glove connects to WiFi + MQTT and starts publishing at ~33 Hz with the new payload format.

### Setup

1. Configure `firmware/include/config.h` (copy from `config.h.example`):
   ```c
   #define DEVICE_SERIAL         "GLOVE001A"
   #define WIFI_SSID             "YourNetwork"
   #define WIFI_PASSWORD         "YourPassword"
   #define MQTT_BROKER_HOST      "192.168.1.100"  // IP of dev machine
   #define MQTT_BROKER_PORT      1883
   #define BATTERY_ADC_PIN       34               // GPIO34 — battery voltage divider
   #define MQTT_PUBLISH_RATE_HZ  33               // 33 Hz publish (within 30–50 Hz spec)
   ```

2. Register the device in Django admin:
   - `serial_number = GLOVE001A`, paired to a patient.

3. Start Mosquitto broker:
   ```bash
   mosquitto -v
   ```

4. Build and flash firmware:
   ```bash
   pio run --target upload
   pio device monitor   # 115200 baud
   ```

### Expected serial monitor output

```
[BOOT] TremoAI Glove Firmware starting...
[IMU] WHO_AM_I OK (0x71)
[CALIB] Collecting 500 samples at 100Hz (~5 seconds)...
[CALIB] Done.
[MQTT] Connecting to WiFi SSID: YourNetwork
....
[MQTT] WiFi connected. IP: 192.168.1.105
[MQTT] NTP initialized.
[MQTT] Connecting to broker 192.168.1.100:1883 as GLOVE001A
[MQTT] Broker connected.
[MQTT] Publishing to topic: tremo/sensors/GLOVE001A
[BOOT] Firmware running — 100Hz IMU / 33Hz MQTT active.
```

### Verify MQTT output

In another terminal:
```bash
mosquitto_sub -t "tremo/sensors/+" -v
```

Expected (~33 messages/second):
```
tremo/sensors/GLOVE001A {"device_id":"GLOVE001A","timestamp":"2026-02-18T10:30:00.123Z","aX":0.1234,"aY":-0.0456,"aZ":9.7654,"gX":12.345,"gY":-5.678,"gZ":0.123,"battery_level":87.5}
```

### Verify rate

```bash
mosquitto_sub -t "tremo/sensors/+" -C 330 | wc -l
# Should print 330 in approximately 10 seconds → 33 Hz
```

### Verify backend reception

```bash
python manage.py shell -c "
from biometrics.models import BiometricReading
import time; c1 = BiometricReading.objects.count()
time.sleep(10)
c2 = BiometricReading.objects.count()
print(f'Rate: {(c2-c1)/10:.1f} readings/s (expected ~33/s)')
"
```

---

## Integration Scenario 2 (US2): Reconnection After Network Disruption

**Goal**: Verify the glove resumes publishing within 10 seconds after broker restart.

### Test steps

1. With the glove actively publishing, observe messages arriving in `mosquitto_sub`.
2. Kill Mosquitto:
   ```bash
   pkill mosquitto
   ```
3. Observe serial monitor — should show:
   ```
   [MQTT] Connection lost — reconnecting (attempt 1)...
   ```
4. Restart Mosquitto:
   ```bash
   mosquitto -v
   ```
5. Within 10 seconds, serial monitor should show:
   ```
   [MQTT] WiFi connected.
   [MQTT] Broker connected.
   [MQTT] Publishing to topic: tremo/sensors/GLOVE001A
   ```
6. Verify `mosquitto_sub` receives messages again.

### WiFi disruption test

1. Disable the WiFi access point (or change SSID/password).
2. Serial monitor should show reconnect attempts at intervals.
3. Re-enable the access point — glove should reconnect within 10 seconds of AP availability.

---

## Integration Scenario 3 (US3): QoS 1 Delivery Verification

**Goal**: Confirm QoS 1 is active and the broker acknowledges PUBACK.

### Verify with Mosquitto verbose log

With `mosquitto -v` running, each QoS 1 publish shows a PUBACK line:
```
1708254600: New client connected from 192.168.1.105 as GLOVE001A
1708254600: PUBLISH: tremo/sensors/GLOVE001A (QoS 1, mid=1)
1708254600: Sending PUBACK to GLOVE001A (mid=1)
```

If QoS 0 were used, the log would show only the PUBLISH line with no PUBACK.

### Verify packet inspection

Use Wireshark on the MQTT port (1883):
- Filter: `mqtt.msgtype == 3` (PUBLISH)
- Verify QoS bits in PUBLISH header = `01` (QoS 1)
- Verify corresponding PUBACK packets (`mqtt.msgtype == 4`)

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `[MQTT] Broker connect failed` | Wrong broker IP or Mosquitto not running | Check `MQTT_BROKER_HOST`; run `mosquitto -v` |
| Messages arrive at old topic `devices/+/reading` | Backend not updated | Ensure `mqtt_client.py` subscribes to `tremo/sensors/+` |
| `Missing required fields: device_id` in backend log | Old firmware still publishing `serial_number` | Flash updated firmware |
| Battery shows 0% constantly | `BATTERY_ADC_PIN` not wired | Check voltage divider connection to GPIO34 |
| Publish rate shows 100 Hz instead of ~33 Hz | `MQTT_PUBLISH_RATE_HZ` macro not set | Check `config.h` and recompile |
| QoS appears as 0 in broker log | Old PubSubClient still in build cache | Clean build: `pio run -t clean && pio run` |
