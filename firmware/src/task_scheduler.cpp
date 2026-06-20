/**
 * task_scheduler.cpp — FreeRTOS Task Bodies and Scheduler Startup
 *
 * Feature: 031-freertos-scheduler
 *
 * Implements three FreeRTOS tasks that replace the single-threaded Arduino loop():
 *
 *   SensorTask  (Core 1, prio 8,  100Hz):
 *     Reads IMU → applies calibration → runs Kalman filter → writes FusedReading to mailbox.
 *     Records t_sensor_us timestamp for end-to-end latency measurement.
 *
 *   ControlTask (Core 1, prio 10, 200Hz):
 *     Reads latest FusedReading from mailbox → runs single-axis PID (TARGET_TREMOR_AXIS) →
 *     issues cmg_set_gimbal() → measures sensor-to-actuation latency.
 *     Logs 60-second execution statistics (FIRMWARE_DEBUG mode).
 *
 *   MqttTask (Core 0, prio 5, 30Hz):
 *     Reads latest FusedReading from mailbox → reads battery → publishes JSON via MQTT.
 *     Calls mqtt_connect() once at startup; mqtt_loop() maintains keepalive.
 *
 * Shared data: g_sensor_mailbox — length-1 FreeRTOS queue (xQueueOverwrite / xQueuePeek).
 *   No mutex — eliminates priority inversion between ControlTask and MqttTask.
 *
 * Latency target: sensor-to-actuation < 70,000 µs (70ms). Warnings logged if exceeded.
 */

#include "task_scheduler.h"
#include "config.h"
#include "edge_config.h"   // 052: committed edge-AI constants (CLASSIFY_*, EDGE_*, GATE_*)
#include "imu.h"
#include "kalman.h"
#include "mqtt_publisher.h"
#include "battery_reader.h"
#include "cmg.h"
#include "pid_controller.h"
#include "edge_features.h"        // 052-edge-ai-inference
#include "classifier.h"
#include "suppression_gate.h"
#include "esp_timer.h"
#include <Arduino.h>

// ─── Shared Mailbox ───────────────────────────────────────────────────────────

QueueHandle_t g_sensor_mailbox = NULL;

// 052: continuous 100Hz 6-axis stream (SensorTask -> ClassificationTask) for the band-pass
// filter, which must see EVERY sample (the mailbox only holds the latest).
QueueHandle_t g_imu_stream = NULL;

// ─── Task Handles ─────────────────────────────────────────────────────────────

static TaskHandle_t s_sensor_handle   = NULL;
TaskHandle_t        s_control_handle  = NULL;   // module-visible — notified directly by SensorTask
static TaskHandle_t s_mqtt_handle     = NULL;
static TaskHandle_t s_classify_handle = NULL;   // 052: ClassificationTask (Core 0)

// ─── 052: latest on-device prediction (written by ClassificationTask Core 0, ──
//     read by MqttTask Core 0). 32-bit volatiles — atomic single load/store on Xtensa.
static volatile int8_t g_pred_class      = -1;
static volatile float  g_pred_proba[3]   = {0.0f, 0.0f, 0.0f};
static volatile bool   g_pred_valid      = false;
static uint32_t        s_classify_count  = 0;

// ─── Kalman Filter Instances (written by scheduler_start, used by SensorTask) ─

static KalmanFilter s_roll_kf;
static KalmanFilter s_pitch_kf;

// ─── Diagnostic Counters (US2 — concurrent execution validation) ──────────────

static uint32_t s_sensor_count  = 0;
static uint32_t s_control_count = 0;
static uint32_t s_mqtt_count    = 0;
static int64_t  s_latency_max_us = 0;
static uint32_t s_violation_count = 0;

// ─── SensorTask (Core 1, prio 8, 100Hz) ──────────────────────────────────────

static void sensorTaskFn(void* pv) {
    CalibrationOffsets* offsets = (CalibrationOffsets*)pv;

    static RawSample      raw;
    static CalibratedSample calib;
    static FusedReading   fr;

    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(IMU_SAMPLE_PERIOD_MS);  // 10ms = 100Hz

    for (;;) {
        // Read raw 6-axis sample from IMU
        if (!read_raw_sample(&raw)) {
            // Skip this cycle on I2C error; vTaskDelayUntil still maintains timing
            vTaskDelayUntil(&xLastWakeTime, xPeriod);
            continue;
        }

        // Apply calibration offsets and compute dt
        apply_calibration(&raw, offsets, &calib);

        // Compute accelerometer-derived reference angles for Kalman correction step
        float roll_accel_deg  = accel_roll(calib.aY, calib.aZ);
        float pitch_accel_deg = accel_pitch(calib.aX, calib.aY, calib.aZ);

        // Run Kalman predict+update for roll and pitch
        fr.roll  = kalman_update(&s_roll_kf,  roll_accel_deg,  calib.gX,
                                 calib.dt, calib.aX, calib.aY, calib.aZ);
        fr.pitch = kalman_update(&s_pitch_kf, pitch_accel_deg, calib.gY,
                                 calib.dt, calib.aX, calib.aY, calib.aZ);

        // Populate calibrated sensor values (included in MQTT payload)
        fr.aX = calib.aX;
        fr.aY = calib.aY;
        fr.aZ = calib.aZ;
        fr.gX = calib.gX;
        fr.gY = calib.gY;
        fr.gZ = calib.gZ;

        // Record timestamp at end of Kalman update for latency measurement
        // ControlTask computes: latency_us = esp_timer_get_time() - fr.t_sensor_us
        fr.t_sensor_us = (uint64_t)esp_timer_get_time();

        // Write to mailbox — never blocks; always delivers latest reading
        xQueueOverwrite(g_sensor_mailbox, &fr);
        if (s_control_handle) xTaskNotifyGive(s_control_handle);   // wake ControlTask immediately — new sample ready

        // 052: stream the calibrated 6-axis sample to the classifier (non-blocking; axis order
        // aX,aY,aZ,gX,gY,gZ matches SIGNAL_COLS). Dropped only if the queue is full (shouldn't
        // happen: ClassificationTask drains ~10 samples per 100ms cycle, queue holds 32).
        if (g_imu_stream) {
            float s6[6] = { calib.aX, calib.aY, calib.aZ, calib.gX, calib.gY, calib.gZ };
            xQueueSend(g_imu_stream, s6, 0);
        }

        s_sensor_count++;

        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── ControlTask (Core 1, prio 10, 200Hz) ────────────────────────────────────

static void controlTaskFn(void* pv) {
    (void)pv;

    static FusedReading snapshot;

    // Single PID instance — feeds only TARGET_TREMOR_AXIS to the gimbal (eliminates cross-talk)
    PidController pid_axis;
    pid_init(&pid_axis, PID_KP, PID_KI, PID_KD, CONTROL_LOOP_DT_S);

    for (;;) {
        // ── 60-second diagnostic log (FIRMWARE_DEBUG mode only) ──────────────
#ifdef FIRMWARE_DEBUG
        static uint32_t s_diag_last_ms = 0;
        uint32_t now_ms = millis();
        if ((now_ms - s_diag_last_ms) >= 60000UL) {
            Serial.printf("[SCHED] 60s stats: sensor=%lu control=%lu mqtt=%lu\n",
                          s_sensor_count, s_control_count, s_mqtt_count);
            Serial.printf("[CTRL]  Latency max=%.1fms violations=%lu\n",
                          (float)s_latency_max_us / 1000.0f, s_violation_count);
            Serial.printf("[CTRL]  Stack HWM: %u words\n", uxTaskGetStackHighWaterMark(NULL));
            // Reset window counters
            s_sensor_count   = 0;
            s_control_count  = 0;
            s_mqtt_count     = 0;
            s_latency_max_us = 0;
            s_violation_count = 0;
            s_diag_last_ms = now_ms;
        }
#endif

        // ── Read latest sensor data from mailbox ──────────────────────────────
        // 1ms timeout — by the time we're woken, SensorTask has already written the sample
        if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(1)) != pdTRUE) {
            // No data yet (very early boot, before SensorTask's first sample) — retry shortly
            continue;
        }

        // ── PID control — gyro angular velocity feedback, setpoint = 0 deg/s ─
        // Suppress tremor (4–8Hz oscillation) by driving angular velocity toward zero
        float measurement = (TARGET_TREMOR_AXIS == AXIS_GX) ? snapshot.gX : snapshot.gY;
        float pid_output = pid_update(&pid_axis, measurement);

        // ── 052: gate suppression on the on-device class (smoothed authority [0,1]) ──
        // The PID law is unchanged; the classifier decides WHETHER / how strongly to engage.
        // Authority ramps 0->1 only on sustained Tremor and 1->0 on sustained non-Tremor, so
        // actuators never chatter. authority==0 -> pid_output*0 -> gimbal returns to neutral.
        pid_output *= edge::gate_authority();

        // ── Issue CMG actuation ───────────────────────────────────────────────
        cmg_set_gimbal(pid_output);

        s_control_count++;

        // ── Sensor-to-actuation latency measurement ───────────────────────────
        int64_t latency_us = esp_timer_get_time() - (int64_t)snapshot.t_sensor_us;
        if (latency_us > s_latency_max_us) {
            s_latency_max_us = latency_us;
        }
        if (latency_us > 70000) {
            s_violation_count++;
            Serial.printf("[CTRL] WARNING latency=%lldus exceeds 70ms budget\n", latency_us);
        }

        // Block until SensorTask notifies (new sample written) or 6ms safety timeout
        // (covers a missed/early notification so the task can never stall indefinitely)
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(6));
    }
}

// ─── MqttTask (Core 0, prio 5, 30Hz) ─────────────────────────────────────────

static void mqttTaskFn(void* pv) {
    (void)pv;

    // Connect at task startup — non-fatal; mqtt_loop() handles reconnect
    if (!mqtt_connect()) {
        Serial.println("[MQTT] Initial connect failed — will retry via mqtt_loop.");
    }

    static FusedReading snapshot;

    TickType_t xLastWakeTime = xTaskGetTickCount();
    // 33ms period ≈ 30Hz publish rate (matches MQTT_PUBLISH_RATE_HZ target in config.h)
    const TickType_t xPeriod = pdMS_TO_TICKS(33);

    for (;;) {
        // MQTT FSM keepalive — must run every loop iteration for PUBACK processing
        mqtt_loop();

        // Read latest sensor data from mailbox (40ms timeout — bounds the delay to the next
        // mqtt_loop() keepalive call; was 100ms, which could starve keepalive for 3 periods)
        if (xQueuePeek(g_sensor_mailbox, &snapshot, pdMS_TO_TICKS(40)) == pdTRUE) {
            // Populate battery level on local snapshot copy before publishing
            snapshot.battery_level = read_battery();
            // 052: attach the latest on-device classifier output to the telemetry payload
            snapshot.pred_valid = g_pred_valid;
            snapshot.pred_class = g_pred_valid ? g_pred_class : -1;
            snapshot.pred_proba[0] = g_pred_proba[0];
            snapshot.pred_proba[1] = g_pred_proba[1];
            snapshot.pred_proba[2] = g_pred_proba[2];
            publish_reading(&snapshot);
            s_mqtt_count++;
        }

        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── ClassificationTask (Core 0, prio 4, 10Hz) — 052-edge-ai-inference ────────
// Streams every IMU sample through the band-pass (continuous filter), then once per
// CLASSIFY_PERIOD_MS produces a 3-class decision and updates the suppression gate. Pinned to
// Core 0 (Core 1 is saturated by Sensor+Control); never on the <70ms control path.

static void classificationTaskFn(void* pv) {
    (void)pv;
    edge::edge_reset();      // clear ring buffer + filter state (warm-up starts now)
    edge::gate_reset();      // safe (disengaged) until sustained Tremor is detected

    static float s6[edge::N_AXES];
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(CLASSIFY_PERIOD_MS);   // ~100ms => 10Hz

    for (;;) {
        // Drain ALL queued samples through the streaming filter (keeps it continuous).
        while (xQueueReceive(g_imu_stream, s6, 0) == pdTRUE) {
            edge::edge_push_sample(s6);
        }

        // Produce a decision (valid=false during warm-up / invalid window).
        edge::Decision d = edge::classify_current_window();
        uint32_t now_us = (uint32_t)esp_timer_get_time();
        d.t_decision_us = now_us;

        // Smoothly gate suppression on the decision.
        edge::gate_update(d, now_us);

        // Publish the latest valid prediction for MQTT telemetry.
        if (d.valid) {
            g_pred_proba[0] = d.proba[0];
            g_pred_proba[1] = d.proba[1];
            g_pred_proba[2] = d.proba[2];
            g_pred_class = (int8_t)d.cls;
            g_pred_valid = true;
        }

        s_classify_count++;
        vTaskDelayUntil(&xLastWakeTime, xPeriod);
    }
}

// ─── scheduler_start() ───────────────────────────────────────────────────────

void scheduler_start(CalibrationOffsets* offsets) {
    // Create the shared sensor mailbox (length 1, thread-safe via FreeRTOS internals)
    g_sensor_mailbox = xQueueCreate(1, sizeof(FusedReading));
    configASSERT(g_sensor_mailbox != NULL);

    // 052: continuous 100Hz sample stream to the classifier (32 deep ≈ 320ms buffer)
    g_imu_stream = xQueueCreate(32, sizeof(float) * edge::N_AXES);
    configASSERT(g_imu_stream != NULL);

    // Seed Kalman filters from calibration gyro biases
    kalman_init(&s_roll_kf,  offsets->gX_bias);
    kalman_init(&s_pitch_kf, offsets->gY_bias);

    // Create SensorTask (Core 1, prio 8, 100Hz)
    BaseType_t ret = xTaskCreatePinnedToCore(
        sensorTaskFn,        // task function
        "SensorTask",        // debug name
        SENSOR_TASK_STACK,   // stack in bytes (6144 — IMU + Kalman + I2C call depth)
        offsets,             // pvParameters: CalibrationOffsets* for apply_calibration()
        8,                   // priority (below ControlTask=10, above MqttTask=5)
        &s_sensor_handle,    // output handle
        1                    // Core 1 — isolated from WiFi/TCP driver jitter
    );
    configASSERT(ret == pdPASS);
    Serial.println("[BOOT] SensorTask  started (Core 1, prio 8, 100Hz)");

    // Create ControlTask (Core 1, prio 10, 200Hz — highest priority on Core 1)
    ret = xTaskCreatePinnedToCore(
        controlTaskFn,       // task function
        "ControlTask",       // debug name
        CONTROL_TASK_STACK,  // stack in bytes (4096 — PID + CMG LEDC write)
        NULL,                // pvParameters: not used
        10,                  // priority (highest user task on Core 1)
        &s_control_handle,   // output handle
        1                    // Core 1 — co-located with SensorTask; preempts it at prio 10
    );
    configASSERT(ret == pdPASS);
    Serial.println("[BOOT] ControlTask started (Core 1, prio 10, 200Hz)");

    // Create MqttTask (Core 0, prio 5, 30Hz — co-located with WiFi/TCP stack)
    ret = xTaskCreatePinnedToCore(
        mqttTaskFn,          // task function
        "MqttTask",          // debug name
        MQTT_TASK_STACK,     // stack in bytes (8192 — JSON serialization + MQTT library)
        NULL,                // pvParameters: not used
        5,                   // priority (above IDLE=0; below WiFi driver=3–23)
        &s_mqtt_handle,      // output handle
        0                    // Core 0 — co-located with WiFi/TCP stack
    );
    configASSERT(ret == pdPASS);
    Serial.println("[BOOT] MqttTask    started (Core 0, prio 5, 30Hz)");

    // Create ClassificationTask (Core 0, prio CLASSIFY_TASK_PRIO, ~10Hz) — 052-edge-ai-inference
    ret = xTaskCreatePinnedToCore(
        classificationTaskFn,   // task function
        "ClassifyTask",         // debug name
        CLASSIFY_TASK_STACK,    // stack in bytes (8192 — FFT/feature buffers are static, not stack)
        NULL,                   // pvParameters: not used
        CLASSIFY_TASK_PRIO,     // priority 4 (below MqttTask=5; never on the Core1 control path)
        &s_classify_handle,     // output handle
        CLASSIFY_TASK_CORE      // Core 0 — off the saturated Core 1
    );
    configASSERT(ret == pdPASS);
    Serial.println("[BOOT] ClassifyTask started (Core 0, prio 4, 10Hz)");
}
