/**
 * T030: Create RegisterPage component wrapping RegisterForm
 * Registration Page
 */

import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import RegisterForm from '../components/auth/RegisterForm';

const RegisterPage = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  // T039: Redirect authenticated users away from register to role-specific dashboard
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
              Create Your Account
            </h1>
            <p className="text-base text-neutral-600">
              Join TremoAI to start monitoring
            </p>
          </div>

          {/* Register Form */}
          <RegisterForm />

          {/* T033: Login Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-primary-600 hover:text-primary-700 font-medium transition-colors duration-200"
              >
                Login here
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

export default RegisterPage;
