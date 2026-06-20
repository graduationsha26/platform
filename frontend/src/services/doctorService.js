/**
 * Doctor Service
 *
 * Feature 047: Staff (Doctor) Management
 * Admin-only API client functions for managing doctor accounts.
 *
 * JWT token is injected automatically by the api Axios instance.
 */

import api from './api';

/**
 * List doctor accounts with assigned patient counts (paginated).
 * @param {Object} params - Query params: page, search
 * @returns {Promise<{ count, next, previous, results }>}
 */
export const listDoctors = async (params = {}) => {
  const response = await api.get('/admin/doctors/', { params });
  return response.data;
};

/**
 * Create a new doctor account.
 * @param {Object} data - { name, email, password, is_active }
 * @returns {Promise<Object>} Created doctor (201)
 */
export const createDoctor = async (data) => {
  const response = await api.post('/admin/doctors/', data);
  return response.data;
};

/**
 * Partially update a doctor's details or toggle is_active.
 * @param {number} id - Doctor account ID
 * @param {Object} data - Fields to update (e.g. { name }, { is_active })
 * @returns {Promise<Object>} Updated doctor
 */
export const updateDoctor = async (id, data) => {
  const response = await api.patch(`/admin/doctors/${id}/`, data);
  return response.data;
};
