/**
 * Token Storage Utility
 * Manages JWT token and user data persistence in localStorage
 */

const TOKEN_KEY = 'tremoai_token';
const USER_KEY = 'tremoai_user';

/**
 * Store JWT access token in localStorage
 * @param {string} token - JWT access token
 */
export const setToken = (token) => {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (error) {
    console.error('Error saving token to localStorage:', error);
  }
};

/**
 * Retrieve JWT access token from localStorage
 * @returns {string|null} JWT token or null if not found
 */
export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error retrieving token from localStorage:', error);
    return null;
  }
};

/**
 * Remove JWT token from localStorage
 */
export const removeToken = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error removing token from localStorage:', error);
  }
};

/**
 * Store user object in localStorage
 * @param {Object} user - User object { id, email, name, role }
 */
export const setUser = (user) => {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch (error) {
    console.error('Error saving user to localStorage:', error);
  }
};

/**
 * Retrieve user object from localStorage
 * @returns {Object|null} User object or null if not found
 */
export const getUser = () => {
  try {
    const userData = localStorage.getItem(USER_KEY);
    return userData ? JSON.parse(userData) : null;
  } catch (error) {
    console.error('Error retrieving user from localStorage:', error);
    return null;
  }
};

/**
 * Remove user object from localStorage
 */
export const removeUser = () => {
  try {
    localStorage.removeItem(USER_KEY);
  } catch (error) {
    console.error('Error removing user from localStorage:', error);
  }
};

/**
 * Clear all authentication data from localStorage
 */
export const clearAuth = () => {
  removeToken();
  removeUser();
};
