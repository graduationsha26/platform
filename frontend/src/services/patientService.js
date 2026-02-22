/**
 * Patient Service
 * API client functions for patient and session endpoints.
 */

import api from './api';

/**
 * Get paginated list of patients for the authenticated doctor.
 * @param {Object} params - Query params: name, page, page_size
 * @returns {Object} { count, next, previous, results }
 */
export const getPatients = async (params = {}) => {
  const response = await api.get('/patients/', { params });
  return response.data;
};

/**
 * Get full patient profile by ID.
 * @param {number} id - Patient ID
 * @returns {Object} PatientDetail
 */
export const getPatient = async (id) => {
  const response = await api.get(`/patients/${id}/`);
  return response.data;
};

/**
 * Create a new patient. Doctor is automatically assigned.
 * @param {Object} data - { full_name, date_of_birth, contact_phone?, contact_email?, medical_notes? }
 * @returns {Object} PatientDetail (201 Created)
 */
export const createPatient = async (data) => {
  const response = await api.post('/patients/', data);
  return response.data;
};

/**
 * Partially update a patient's profile.
 * @param {number} id - Patient ID
 * @param {Object} data - Fields to update
 * @returns {Object} Updated PatientDetail
 */
export const updatePatient = async (id, data) => {
  const response = await api.patch(`/patients/${id}/`, data);
  return response.data;
};

/**
 * Get paginated session history for a patient.
 * @param {number} patientId - Patient ID
 * @param {Object} params - Additional query params: page, page_size
 * @returns {Object} { count, next, previous, results }
 */
export const getSessions = async (patientId, params = {}) => {
  const response = await api.get('/biometric-sessions/', {
    params: { patient: patientId, ...params },
  });
  return response.data;
};
