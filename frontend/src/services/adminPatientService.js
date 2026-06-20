/**
 * Admin Patient Service
 *
 * Feature 048: Patient Distribution (Admin)
 * Admin-only API client for the center-wide patient roster, registration,
 * and doctor (re)assignment.
 *
 * JWT token is injected automatically by the api Axios instance.
 */

import api from './api';

/**
 * List all center-wide patients with their assigned doctor (paginated).
 * @param {Object} params - Query params: page, search
 * @returns {Promise<{ count, next, previous, results }>}
 */
export const listAdminPatients = async (params = {}) => {
  const response = await api.get('/admin/patients/', { params });
  return response.data;
};

/**
 * Register a new patient (admin), optionally assigning a doctor.
 * @param {Object} data - { full_name, date_of_birth, contact_phone?, contact_email?, medical_notes?, doctor_id? }
 * @returns {Promise<Object>} Created patient roster row (201)
 */
export const registerPatient = async (data) => {
  const response = await api.post('/admin/patients/', data);
  return response.data;
};

/**
 * Assign or reassign a patient to a doctor (replace semantics).
 * @param {number} id - Patient ID
 * @param {number} doctorId - Target doctor account ID
 * @returns {Promise<Object>} Updated patient roster row (200)
 */
export const assignPatient = async (id, doctorId) => {
  const response = await api.post(`/admin/patients/${id}/assign/`, { doctor_id: doctorId });
  return response.data;
};
