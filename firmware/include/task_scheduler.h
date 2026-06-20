/**
 * task_scheduler.h — FreeRTOS Task Scheduler: Handles, Queue Mailbox, and Startup
 *
 * Feature: 031-freertos-scheduler
 *
 * Replaces the single-threaded Arduino loop() with three dedicated FreeRTOS tasks:
 *
 *   SensorTask  (Core 1, prio 8,  100Hz): IMU read → Kalman update → xQueueOverwrite
 *   ControlTask (Core 1, prio 10, 200Hz): xQueuePeek → PID → cmg_set_gimbal
 *   MqttTask    (Core 0, prio 5,  30Hz):  xQueuePeek → read_battery → publish_reading
 *
 * Core assignment:
 *   Core 1 — Real-time tasks (isolated from WiFi/TCP driver jitter)
 *   Core 0 — WiFi/TCP stack (Espressif-reserved) + MqttTask (co-located to minimize
 *             cross-core data transfer for MQTT publish)
 *
 * Shared data — Queue Mailbox pattern (xQueueOverwrite / xQueuePeek):
 *   A length-1 queue acts as a thread-safe single-slot register.
 *   xQueueOverwrite: never blocks; atomically replaces the item.
 *   xQueuePeek: reads without consuming; both ControlTask and MqttTask see latest value.
 *   No mutex required — eliminates priority inversion risk (MqttTask cannot block ControlTask).
 *
 * CRITICAL — loop() must call vTaskDelete(NULL):
 *   An empty loop() body starves the IDLE task and triggers a watchdog reset in ~5 seconds.
 *   vTaskDelete(NULL) permanently removes loopTask and frees its ~8KB stack.
 *
 * Timing:
 *   All tasks use vTaskDelayUntil() — drift-free periodic scheduling.
 *   CONFIG_FREERTOS_HZ = 1000 (1ms tick) provides sufficient resolution for 5ms periods.
 */

#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "imu.h"

/**
 * g_sensor_mailbox — Length-1 FreeRTOS queue acting as a thread-safe sensor data mailbox.
 *
 * Writer:  SensorTask via xQueueOverwrite (non-blocking; always writes latest FusedReading)
 * Readers: ControlTask via xQueuePeek (10ms timeout)
 *          MqttTask    via xQueuePeek (100ms timeout)
 *
 * Created by scheduler_start() before any tasks are created.
 * Size: sizeof(FusedReading) — carries all sensor data including t_sensor_us for
 *       sensor-to-actuation latency measurement.
 */
extern QueueHandle_t g_sensor_mailbox;

/**
 * scheduler_start() — Create all three FreeRTOS tasks and the shared mailbox.
 *
 * Operations (in order):
 *   1. Creates g_sensor_mailbox (length 1, sizeof FusedReading).
 *   2. Seeds Kalman filters from calibration gyro biases (offsets->gX_bias, gY_bias).
 *   3. Creates SensorTask  via xTaskCreatePinnedToCore (Core 1, prio 8).
 *   4. Creates ControlTask via xTaskCreatePinnedToCore (Core 1, prio 10).
 *   5. Creates MqttTask    via xTaskCreatePinnedToCore (Core 0, prio 5).
 *   6. Logs boot messages for each task.
 *
 * Must be called from setup() AFTER calibrate_imu() and cmg_init().
 * Must NOT be called more than once.
 *
 * @param offsets  Calibration offsets from calibrate_imu(); must have valid=true.
 *                 Pointer must remain valid for the device lifetime (static storage in main.cpp).
 */
void scheduler_start(CalibrationOffsets* offsets);
