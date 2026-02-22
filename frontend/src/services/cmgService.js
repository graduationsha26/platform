/**
 * CMG Motor Service
 * API functions for CMG motor telemetry, fault events, motor commands,
 * gimbal servo commands, calibration, and gimbal state.
 *
 * Feature 027: CMG Brushless Motor & ESC Initialization
 * Feature 028: CMG Gimbal Servo Control
 */

import api from './api';

/**
 * Fetch the most recent telemetry record for a device.
 * @param {number} deviceId
 * @returns {Promise<Object>} Latest MotorTelemetry record
 */
export const getLatestTelemetry = async (deviceId) => {
  const response = await api.get('/cmg/telemetry/latest/', {
    params: { device_id: deviceId },
  });
  return response.data;
};

/**
 * Fetch telemetry history for a device.
 * @param {number} deviceId
 * @param {number} limit - Max records to return (default 60, max 300)
 * @returns {Promise<Object>} { count, results }
 */
export const getTelemetryHistory = async (deviceId, limit = 60) => {
  const response = await api.get('/cmg/telemetry/', {
    params: { device_id: deviceId, limit },
  });
  return response.data;
};

/**
 * Fetch fault events for a device, optionally filtered by acknowledgment status.
 * @param {number} deviceId
 * @param {Object} filters
 * @param {boolean} [filters.acknowledged] - Filter by acknowledgment status
 * @returns {Promise<Object>} { count, results }
 */
export const getFaults = async (deviceId, filters = {}) => {
  const params = { device_id: deviceId };
  if (filters.acknowledged !== undefined) {
    params.acknowledged = filters.acknowledged;
  }
  const response = await api.get('/cmg/faults/', { params });
  return response.data;
};

/**
 * Acknowledge a motor fault event.
 * Idempotent — acknowledging an already-acknowledged fault is safe.
 * @param {number} faultId
 * @returns {Promise<Object>} Updated MotorFaultEvent record
 */
export const acknowledgeFault = async (faultId) => {
  const response = await api.post(`/cmg/faults/${faultId}/acknowledge/`);
  return response.data;
};

/**
 * Send a motor control command to the glove via MQTT.
 * @param {number} deviceId
 * @param {'start'|'stop'|'emergency_stop'} command
 * @returns {Promise<Object>} { status, command, device_serial, published_at }
 */
export const sendCommand = async (deviceId, command) => {
  const response = await api.post('/cmg/commands/', {
    device_id: deviceId,
    command,
  });
  return response.data;
};

// ---------------------------------------------------------------------------
// Feature 028: CMG Gimbal Servo Control
// ---------------------------------------------------------------------------

/**
 * Send a gimbal servo position command or home command.
 * @param {number} deviceId
 * @param {'set_position'|'home'} command
 * @param {{ pitch_deg?: number, roll_deg?: number }} angles - Required for set_position
 * @returns {Promise<Object>} { success, command_id, device_id, command, target_pitch_deg, target_roll_deg, message }
 */
export const sendServoCommand = (deviceId, command, angles = {}) =>
  api.post('/cmg/servo/commands/', { device_id: deviceId, command, ...angles })
    .then((r) => r.data);

/**
 * Retrieve current gimbal calibration for a device.
 * Returns system defaults if no calibration has been set.
 * @param {number} deviceId
 * @returns {Promise<Object>} GimbalCalibration record
 */
export const getGimbalCalibration = (deviceId) =>
  api.get(`/cmg/servo/calibration/${deviceId}/`).then((r) => r.data);

/**
 * Create or fully replace the gimbal calibration for a device (doctor only).
 * @param {number} deviceId
 * @param {Object} data - Calibration fields (all required)
 * @returns {Promise<Object>} Updated GimbalCalibration record
 */
export const setGimbalCalibration = (deviceId, data) =>
  api.put(`/cmg/servo/calibration/${deviceId}/`, data).then((r) => r.data);

/**
 * Retrieve the latest gimbal state for a device.
 * Returns 404 if the device has never published a servo_state MQTT message.
 * @param {number} deviceId
 * @returns {Promise<Object>} GimbalState record
 */
export const getGimbalState = (deviceId) =>
  api.get(`/cmg/servo/state/${deviceId}/`).then((r) => r.data);

// ---------------------------------------------------------------------------
// Feature 029: CMG PID Controller Tuning
// ---------------------------------------------------------------------------

/**
 * Retrieve current PID gain configuration for a device.
 * Returns system defaults if no PID config has been set.
 * @param {number} deviceId
 * @returns {Promise<Object>} PIDConfig record
 */
export const getPIDConfig = (deviceId) =>
  api.get(`/cmg/pid/config/${deviceId}/`).then((r) => r.data);

/**
 * Create or fully replace the PID gain configuration for a device (doctor only).
 * @param {number} deviceId
 * @param {Object} data - PID gain fields (kp_pitch, ki_pitch, kd_pitch, kp_roll, ki_roll, kd_roll)
 * @returns {Promise<Object>} Updated PIDConfig record
 */
export const setPIDConfig = (deviceId, data) =>
  api.put(`/cmg/pid/config/${deviceId}/`, data).then((r) => r.data);

// ---------------------------------------------------------------------------
// Feature 029: Suppression Mode & Sessions
// ---------------------------------------------------------------------------

/**
 * Start a tremor suppression session for a device (doctor only).
 * Returns 400 if the device has no PID config, 409 if a session is already active.
 * @param {number} deviceId
 * @returns {Promise<Object>} Created SuppressionSession record
 */
export const startSuppression = (deviceId) =>
  api.post('/cmg/pid/sessions/', { device_id: deviceId }).then((r) => r.data);

/**
 * Stop (complete) an active suppression session (doctor only).
 * @param {number} sessionPk
 * @returns {Promise<Object>} Updated SuppressionSession record
 */
export const stopSuppression = (sessionPk) =>
  api.delete(`/cmg/pid/sessions/${sessionPk}/`).then((r) => r.data);

/**
 * Get the current suppression mode status for a device.
 * @param {number} deviceId
 * @returns {Promise<Object>} { device_id, is_active, session_id, session_uuid, started_at }
 */
export const getSuppressionMode = (deviceId) =>
  api.get(`/cmg/pid/mode/${deviceId}/`).then((r) => r.data);

/**
 * List suppression sessions for a device with optional filters.
 * @param {number} deviceId
 * @param {Object} params - Optional query params (limit, status, etc.)
 * @returns {Promise<Object>} { count, results }
 */
export const listSessions = (deviceId, params = {}) =>
  api.get('/cmg/pid/sessions/', { params: { device_id: deviceId, ...params } }).then((r) => r.data);

/**
 * Fetch time-series metrics for a suppression session, including aggregate.
 * @param {number} sessionPk
 * @param {Object} params - Optional query params (since, limit)
 * @returns {Promise<Object>} { session_id, session_status, aggregate, metrics }
 */
export const getSessionMetrics = (sessionPk, params = {}) =>
  api.get(`/cmg/pid/sessions/${sessionPk}/metrics/`, { params }).then((r) => r.data);
