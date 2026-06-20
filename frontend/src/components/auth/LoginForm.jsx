/**
 * T020: Create LoginForm component with React Hook Form validation
 * Login Form Component
 */

import React from 'react';
import { useForm } from 'react-hook-form';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';
import Input from '../common/Input';
import LoadingSpinner from '../common/LoadingSpinner';
import { emailValidation, passwordLoginValidation } from '../../utils/validators';

const LoginForm = () => {
  const { login, isSubmitting, error, clearError } = useAuth();
  const location = useLocation();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = async (data) => {
    try {
      clearError();
      // T040: Pass the originally attempted URL from location state
      const from = location.state?.from || null;
      await login(data.email, data.password, from);
    } catch (err) {
      // Error is handled in AuthContext
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* T040: Display API error with animation and medical colors */}
      {error && (
        <div className="bg-error-50 border border-error-200 rounded-lg p-4 animate-slide-in-top">
          <p className="text-sm text-error-800 flex items-start gap-2">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </p>
        </div>
      )}

      {/* Email Input - T038: Enhanced input styling */}
      <Input
        label="Email"
        id="email"
        type="email"
        placeholder="doctor@example.com"
        error={errors.email?.message}
        {...register('email', emailValidation)}
      />

      {/* Password Input - T038: Enhanced input styling */}
      <Input
        label="Password"
        id="password"
        type="password"
        placeholder="Enter your password"
        error={errors.password?.message}
        {...register('password', passwordLoginValidation)}
      />

      {/* T043: Submit Button with enhanced hover states */}
      <Button
        type="submit"
        variant="primary"
        loading={isSubmitting}
        className="w-full mt-6"
      >
        Login
      </Button>
    </form>
  );
};

export default LoginForm;
