/**
 * Analytics Service
 *
 * Feature 032: Dashboard Overview Page
 * API client functions for the analytics endpoints.
 */

import api from './api';

/**
 * Fetch dashboard summary statistics for the authenticated doctor.
 *
 * Returns total_patients, active_devices, alerts_count, and a 7-day
 * tremor_trend array — all scoped to the doctor's assigned patients.
 *
 * JWT token is injected automatically by the api Axios instance.
 *
 * @returns {Promise<Object>} Dashboard stats object
 * @throws {Error} On network failure or non-2xx response
 */
export async function fetchDashboardStats() {
  const response = await api.get('/analytics/dashboard/');
  return response.data;
}

/**
 * Fetch daily aggregated tremor statistics for a patient over a date range.
 *
 * Calls GET /api/analytics/stats/ with group_by=day and page_size=365
 * (covers up to a full year in a single request).
 *
 * @param {number|string} patientId - Patient database ID
 * @param {string} startDate - ISO date YYYY-MM-DD (inclusive)
 * @param {string} endDate   - ISO date YYYY-MM-DD (inclusive)
 * @returns {Promise<{ count: number, baseline: object|null, results: object[] }>}
 */
export async function fetchPatientStats(patientId, startDate, endDate) {
  const response = await api.get('/analytics/stats/', {
    params: {
      patient_id: patientId,
      start_date: startDate,
      end_date: endDate,
      group_by: 'day',
      page_size: 365,
    },
  });
  return response.data;
}

/**
 * Generate and download a PDF report for a patient over a date range.
 *
 * Calls POST /api/analytics/reports/ with responseType:'blob'. On error,
 * the response body is also a blob — this function reads it as text, parses
 * the JSON, and attaches a `parsedCode` property to the error before
 * re-throwing so callers can map error codes to user-facing messages.
 *
 * @param {number|string} patientId - Patient database ID
 * @param {string} startDate - ISO date YYYY-MM-DD
 * @param {string} endDate   - ISO date YYYY-MM-DD
 * @returns {Promise<Blob>} PDF blob
 */
export async function downloadPatientReport(patientId, startDate, endDate) {
  try {
    const response = await api.post(
      '/analytics/reports/',
      { patient_id: patientId, start_date: startDate, end_date: endDate },
      { responseType: 'blob' },
    );
    return response.data;
  } catch (err) {
    // Axios error responses with responseType:'blob' wrap the body as a Blob.
    // Read it as text to extract the structured error code.
    if (err.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text();
        const parsed = JSON.parse(text);
        err.parsedCode = parsed.code ?? null;
      } catch {
        // Could not parse error body — leave parsedCode undefined
      }
    }
    throw err;
  }
}
