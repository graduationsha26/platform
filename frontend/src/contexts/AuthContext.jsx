/**
 * Authentication Context
 * Manages global authentication state for the TremoAI platform
 */

import React, { createContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getToken,
  setToken as storeToken,
  removeToken,
  getUser as getStoredUser,
  setUser as storeUser,
  clearAuth as clearStoredAuth
} from '../utils/tokenStorage';
import api from '../services/api';

// Create the context
export const AuthContext = createContext();

// AuthProvider component
export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();

  // Authentication state
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Initialize authentication state from localStorage on app load
   * T017: Implement token persistence on app initialization
   */
  useEffect(() => {
    const initializeAuth = () => {
      try {
        const storedToken = getToken();
        const storedUser = getStoredUser();

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(storedUser);
          setIsAuthenticated(true);
        }
      } catch (err) {
        console.error('Error initializing auth:', err);
        clearStoredAuth();
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  /**
   * Login action
   * T015: Implement login action in AuthContext
   * @param {string} email - User email
   * @param {string} password - User password
   * @param {string} redirectTo - Optional redirect path after login
   */
  const login = useCallback(async (email, password, redirectTo = null) => {
    try {
      setIsSubmitting(true);
      setError(null);

      // Call login API endpoint (will be implemented in authService)
      const response = await api.post('/auth/login/', { email, password });

      const { access, user: userData } = response.data;

      // Store token and user in localStorage
      storeToken(access);
      storeUser(userData);

      // Update state
      setToken(access);
      setUser(userData);
      setIsAuthenticated(true);

      // T040: Post-login redirect to originally attempted URL
      // If redirectTo is provided (from protected route attempt), use it
      // Otherwise, T026: redirect to role-specific dashboard
      let targetPath = redirectTo;

      if (!targetPath || targetPath === '/login' || targetPath === '/register') {
        // Default to role-specific dashboard
        targetPath = '/doctor/dashboard';
      }

      navigate(targetPath);
    } catch (err) {
      console.error('Login error:', err);
      const errorMessage = err.response?.data?.error || 'Invalid credentials. Please try again.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, [navigate]);

  /**
   * Logout action
   * T016: Implement logout action in AuthContext
   */
  const logout = useCallback(() => {
    // Clear localStorage
    clearStoredAuth();

    // Reset state
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    setError(null);

    // Redirect to login
    navigate('/login');
  }, [navigate]);

  /**
   * Register action (will be implemented in Phase 4 - US2)
   * Placeholder for now
   */
  const register = useCallback(async (data) => {
    try {
      setIsSubmitting(true);
      setError(null);

      // Call register API endpoint (will be implemented in authService)
      const response = await api.post('/auth/register/', data);

      // Registration successful - redirect to login with success message
      navigate('/login', {
        state: { message: 'Account created successfully! Please log in.' }
      });
    } catch (err) {
      console.error('Registration error:', err);
      const errorMessage = err.response?.data?.error || 'Registration failed. Please try again.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, [navigate]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Context value
  const value = {
    // State
    user,
    token,
    isAuthenticated,
    isLoading,
    isSubmitting,
    error,

    // Actions
    login,
    logout,
    register,
    clearError,
  };

  // Don't render children until initial auth check is complete
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
