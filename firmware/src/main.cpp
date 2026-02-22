/**
 * main.cpp — TremoAI Smart Glove Firmware Entry Point
 *
 * Feature: 025-imu-kalman-fusion
 * Feature: 030-esp32-mqtt (battery_level, MQTT publish pipeline)
 * Feature: 031-freertos-scheduler (FreeRTOS task scheduler, PID tremor control, CMG actuation)
 *
 * Pipeline: MPU9250 init → calibration → battery init → CMG init → FreeRTOS task scheduler
 *   SensorTask  (Core 1, 100Hz): IMU read → Kalman fusion → sensor mailbox
 *   ControlTask (Core 1, 200Hz): mailbox → PID → CMG actuation (target: <70ms latency)
 *   MqttTask    (Core 0,  30Hz): mailbox → battery → MQTT JSON publish
 *
 * Boot sequence:
 *   1. Serial init
 *   2. IMU init (I2C, WHO_AM_I, register config, magnetometer disabled)
 *   3. Startup calibration (500 samples, bias computation)
 *   4. Battery ADC init
 *   5. CMG init (gimbal servo + flywheel ESC arming, ~2s)
 *   6. scheduler_start(): creates mailbox, seeds Kalman, starts 3 FreeRTOS tasks
 *   7. loop() calls vTaskDelete(NULL) — frees loopTask stack, prevents watchdog starvation
 */

#include <Arduino.h>
#include "config.h"
#include "imu.h"
#include "mqtt_publisher.h"
#include "battery_reader.h"
#include "task_scheduler.h"
#include "cmg.h"

// ─── Firmware State ───────────────────────────────────────────────────────────
enum FIRMWARE_STATE {
    STATE_INIT,
    STATE_CALIBRATING,
    STATE_RUNNING,
    STATE_FAULT
};

static FIRMWARE_STATE state = STATE_INIT;

// ─── Global Data Buffers ──────────────────────────────────────────────────────
// g_offsets: computed by calibrate_imu(), passed to scheduler_start() for use by SensorTask.
// Declared static so its address remains valid for the device lifetime.
static CalibrationOffsets g_offsets;

// ─── setup() ─────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(200);  // Allow serial to stabilize
    Serial.println("[BOOT] TremoAI Glove Firmware starting...");

    // --- IMU Initialization ---
    state = STATE_INIT;
    if (!imu_init()) {
        Serial.println("[FAULT] IMU initialization failed. Halting.");
        state = STATE_FAULT;
    }

    // --- Startup Calibration ---
    if (state != STATE_FAULT) {
        state = STATE_CALIBRATING;
        Serial.println("[CALIB] Starting startup calibration — keep glove flat and still...");
        if (!calibrate_imu(&g_offsets)) {
            Serial.println("[FAULT] Calibration failed (motion detected or IMU error). Halting.");
            state = STATE_FAULT;
        }
    }

    // --- FAULT halt: blink LED, block forever ---
    if (state == STATE_FAULT) {
        if (FAULT_LED_PIN >= 0) {
            pinMode(FAULT_LED_PIN, OUTPUT);
        }
        while (true) {
            if (FAULT_LED_PIN >= 0) {
                digitalWrite(FAULT_LED_PIN, HIGH);
                delay(250);
                digitalWrite(FAULT_LED_PIN, LOW);
                delay(250);
            } else {
                delay(1000);
            }
        }
    }

    // --- Battery ADC init ---
    battery_init();
    Serial.println("[BOOT] Battery ADC initialized.");

    // --- CMG init (gimbal servo + flywheel ESC arming) ---
    // Note: cmg_init() includes a 2-second ESC arming delay — this is normal.
    cmg_init();
    Serial.println("[BOOT] CMG initialized (GPIO18 gimbal, GPIO19 flywheel, 50Hz 16-bit).");

    // --- Start FreeRTOS task scheduler ---
    // Creates sensor mailbox, seeds Kalman filters from g_offsets, creates all 3 tasks.
    // MQTT connection is handled by MqttTask at startup (not here) — avoids blocking setup().
    scheduler_start(&g_offsets);
    Serial.println("[BOOT] FreeRTOS tasks started.");

    state = STATE_RUNNING;
    Serial.println("[BOOT] Firmware running — FreeRTOS task scheduler active "
                   "(SensorTask 100Hz, ControlTask 200Hz, MqttTask 30Hz). "
                   "MQTT connection handled by MqttTask on Core 0.");
}

// ─── loop() ──────────────────────────────────────────────────────────────────
void loop() {
    // CRITICAL: Do NOT leave loop() empty or with a tight spin.
    // An empty loop() starves the FreeRTOS IDLE task → watchdog reset in ~5 seconds:
    //   "Task watchdog got triggered. Tasks not feeding watchdog: IDLE (CPU 1)"
    //
    // vTaskDelete(NULL) permanently removes loopTask, freeing its ~8KB stack.
    // The IDLE task resumes and the watchdog is satisfied.
    // All periodic work runs in the three FreeRTOS tasks created by scheduler_start().
    vTaskDelete(NULL);
}
