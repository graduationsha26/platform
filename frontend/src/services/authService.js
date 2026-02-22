/**
 * Authentication Service
 * API functions for login and registration
 */

import api from './api';

/**
 * T019: Implement authService.login function
 * Login user with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Response with access token and user data
 */
export const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login/', {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * T027: Implement authService.register function (Phase 4 - US2)
 * Register new user account
 * @param {Object} data - Registration data
 * @param {string} data.name - User full name
 * @param {string} data.email - User email
 * @param {string} data.password - User password
 * @param {string} data.role - User role (doctor or patient)
 * @returns {Promise<Object>} Response with user data
 */
export const register = async (data) => {
  try {
    const response = await api.post('/auth/register/', data);
    return response.data;
  } catch (error) {
    throw error;
  }
};

/**
 * Logout is handled client-side only (no API call needed)
 * Just clear localStorage and redirect
 */
export const logout = () => {
  // Logout handled in AuthContext
};
