/**
 * T029: Create RegisterForm component with React Hook Form validation
 * Registration Form Component
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useAuth } from '../../hooks/useAuth';
import Button from '../common/Button';
import Input from '../common/Input';
import LoadingSpinner from '../common/LoadingSpinner';
import {
  nameValidation,
  emailValidation,
  passwordRegisterValidation,
  passwordConfirmValidation,
  roleValidation,
} from '../../utils/validators';

// T042: Password strength calculator
const calculatePasswordStrength = (password) => {
  if (!password) return { strength: 'none', color: 'neutral', label: '', percentage: 0 };

  let score = 0;
  // Length check
  if (password.length >= 8) score += 25;
  if (password.length >= 12) score += 15;
  // Character variety
  if (/[a-z]/.test(password)) score += 15;
  if (/[A-Z]/.test(password)) score += 15;
  if (/[0-9]/.test(password)) score += 15;
  if (/[^a-zA-Z0-9]/.test(password)) score += 15;

  if (score < 40) return { strength: 'weak', color: 'error', label: 'Weak password', percentage: score };
  if (score < 70) return { strength: 'medium', color: 'warning', label: 'Medium strength', percentage: score };
  return { strength: 'strong', color: 'success', label: 'Strong password', percentage: score };
};

const RegisterForm = () => {
  const { register: registerUser, isSubmitting, error, clearError } = useAuth();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      role: 'doctor', // Default role
    },
  });

  // Watch password field for confirmation validation and strength indicator
  const password = watch('password');
  const [passwordStrength, setPasswordStrength] = useState({ strength: 'none', color: 'neutral', label: '', percentage: 0 });

  // T042: Update password strength on password change
  useEffect(() => {
    setPasswordStrength(calculatePasswordStrength(password));
  }, [password]);

  const onSubmit = async (data) => {
    try {
      clearError();
      // Map passwordConfirm → password_confirm (backend field name)
      const { passwordConfirm, ...registrationData } = data;
      await registerUser({ ...registrationData, password_confirm: passwordConfirm });
    } catch (err) {
      // Error is handled in AuthContext
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* T041: Display API error with animation and medical colors */}
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

      {/* First Name Input */}
      <Input
        label="First Name"
        id="first_name"
        type="text"
        placeholder="John"
        error={errors.first_name?.message}
        {...register('first_name', nameValidation)}
      />

      {/* Last Name Input */}
      <Input
        label="Last Name"
        id="last_name"
        type="text"
        placeholder="Doe"
        error={errors.last_name?.message}
        {...register('last_name', nameValidation)}
      />

      {/* Email Input - T039: Enhanced input styling */}
      <Input
        label="Email"
        id="email"
        type="email"
        placeholder="doctor@example.com"
        error={errors.email?.message}
        {...register('email', emailValidation)}
      />

      {/* Password Input with Strength Indicator - T039, T042 */}
      <div>
        <Input
          label="Password"
          id="password"
          type="password"
          placeholder="Min 8 chars, letter + number"
          error={errors.password?.message}
          {...register('password', passwordRegisterValidation)}
        />

        {/* T042: Password strength indicator */}
        {password && passwordStrength.strength !== 'none' && (
          <div className="mt-2 animate-slide-in-top">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-xs font-medium text-${passwordStrength.color}-700`}>
                {passwordStrength.label}
              </span>
              <span className={`text-xs text-${passwordStrength.color}-600`}>
                {passwordStrength.percentage}%
              </span>
            </div>
            <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
              <div
                className={`h-full bg-${passwordStrength.color}-500 transition-all duration-300 ease-out`}
                style={{ width: `${passwordStrength.percentage}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Password Confirmation Input - T039: Enhanced input styling */}
      <Input
        label="Confirm Password"
        id="passwordConfirm"
        type="password"
        placeholder="Re-enter your password"
        error={errors.passwordConfirm?.message}
        {...register('passwordConfirm', passwordConfirmValidation(password))}
      />

      {/* Role Selection - T039: Medical color scheme */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          I am a:
        </label>
        <div className="space-y-2">
          <label className="flex items-center p-3 border border-neutral-300 rounded-lg cursor-pointer hover:bg-neutral-50 transition-colors duration-200">
            <input
              type="radio"
              value="doctor"
              {...register('role', roleValidation)}
              className="mr-3 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <p className="font-medium text-neutral-900">Doctor</p>
              <p className="text-sm text-neutral-600">
                I monitor and care for patients with Parkinson's
              </p>
            </div>
          </label>

          <label className="flex items-center p-3 border border-neutral-300 rounded-lg cursor-pointer hover:bg-neutral-50 transition-colors duration-200">
            <input
              type="radio"
              value="admin"
              {...register('role', roleValidation)}
              className="mr-3 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <p className="font-medium text-neutral-900">Admin</p>
              <p className="text-sm text-neutral-600">
                I manage the TremoAI platform
              </p>
            </div>
          </label>
        </div>
        {errors.role && (
          <p className="mt-2 text-sm text-error-600 flex items-start gap-1">
            <svg className="w-4 h-4 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errors.role.message}
          </p>
        )}
      </div>

      {/* T044: Submit Button with enhanced hover states */}
      <Button
        type="submit"
        variant="primary"
        loading={isSubmitting}
        className="w-full mt-6"
      >
        Create Account
      </Button>
    </form>
  );
};

export default RegisterForm;
