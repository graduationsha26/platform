/**
 * firmware.ino - Arduino IDE compatibility stub (DO NOT EDIT)
 *
 * The actual firmware entry point is src/main.cpp.
 * This file exists only so that Arduino IDE can open the sketch directory.
 * PlatformIO IDE (VS Code) does NOT use this file — it uses src/main.cpp directly.
 *
 * ── Primary workflow: VS Code + PlatformIO IDE extension ─────────────────────
 *
 *   1. Open the firmware/ folder in VS Code
 *      File > Open Folder... > select .../Platform/firmware/
 *
 *   2. Configure credentials before first build
 *      Edit firmware/include/config.h and fill in:
 *        DEVICE_SERIAL  — must match the device registered in Django admin
 *        WIFI_SSID / WIFI_PASSWORD
 *        MQTT_BROKER_HOST — LAN IP of the PC running Mosquitto
 *
 *   3. Connect the ESP32 via USB, then:
 *      Build:          Ctrl+Alt+B
 *      Upload:         Ctrl+Alt+U
 *      Serial monitor: Ctrl+Alt+S  (115200 baud, timestamps + exception decoder)
 *
 *   4. To enable 60-second task statistics, switch to the debug environment:
 *      Click the environment name in the VS Code status bar > esp32dev-debug
 *
 * ── PlatformIO CLI (optional) ────────────────────────────────────────────────
 *   pio run                   # build
 *   pio run --target upload   # build + upload
 *   pio device monitor        # serial monitor
 *   pio run -e esp32dev-debug # build debug env
 */
