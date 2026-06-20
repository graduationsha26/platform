/**
 * T021: Create LoginPage component wrapping LoginForm
 * Login Page
 */

import React, { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import LoginForm from '../components/auth/LoginForm';

const LoginPage = () => {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Session expired message from URL params
  const searchParams = new URLSearchParams(location.search);
  const sessionExpired = searchParams.get('session_expired');

  // Success message from registration (via location state)
  const successMessage = location.state?.message;

  // T039: Redirect authenticated users away from login to role-specific dashboard
  useEffect(() => {
    if (isAuthenticated && user) {
      const dashboardPath = '/doctor/dashboard';
      navigate(dashboardPath, { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-secondary-50 to-primary-100 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
          {/* Header */}
          <div className="text-center mb-6 sm:mb-8">
            <h1 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-2">
              Welcome to TremoAI
            </h1>
            <p className="text-base text-neutral-600">
              Sign in to access your dashboard
            </p>
          </div>

          {/* Session Expired Message */}
          {sessionExpired && (
            <div className="bg-warning-50 border border-warning-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-warning-800">
                Your session has expired. Please log in again.
              </p>
            </div>
          )}

          {/* Success Message from Registration */}
          {successMessage && (
            <div className="bg-success-50 border border-success-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-success-800">{successMessage}</p>
            </div>
          )}

          {/* Login Form */}
          <LoginForm />

          {/* Register Link - T032 will be added in Phase 4 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-primary-600 hover:text-primary-700 font-medium transition-colors duration-200"
              >
                Register here
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-neutral-500 mt-6">
          TremoAI Platform - Parkinson's Tremor Monitoring
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
