import React from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';

const Input = ({
  label,
  type = 'text',
  error,
  success,
  id,
  className = '',
  ...props
}) => {
  // Determine validation state
  const hasError = !!error;
  const hasSuccess = !!success && !error;

  return (
    <div className="mb-4 form-group">
      {/* T035: Enhanced label styling */}
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-medium text-neutral-700 mb-2"
        >
          {label}
        </label>
      )}

      {/* T036-T038: Enhanced input with focus animations and validation states */}
      <div className="relative">
        <input
          id={id}
          type={type}
          className={`
            w-full px-4 py-3 border rounded-lg touch-target
            font-body text-base text-neutral-900
            placeholder-neutral-400
            transition-all duration-200
            focus:outline-none focus:ring-4 focus:scale-[1.02]
            ${hasError
              ? 'border-error-500 focus:border-error-600 focus:ring-error-200'
              : hasSuccess
              ? 'border-success-500 focus:border-success-600 focus:ring-success-200'
              : 'border-neutral-300 focus:border-primary-600 focus:ring-primary-200'
            }
            ${props.disabled ? 'bg-neutral-100 cursor-not-allowed opacity-60' : 'bg-white'}
            ${className}
          `}
          {...props}
        />

        {/* T039: Validation icons */}
        {(hasError || hasSuccess) && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            {hasError && (
              <AlertCircle className="w-5 h-5 text-error-500" />
            )}
            {hasSuccess && (
              <CheckCircle className="w-5 h-5 text-success-500" />
            )}
          </div>
        )}
      </div>

      {/* T039: Enhanced error message with animation */}
      {error && (
        <div className="mt-2 flex items-start gap-1 animate-slide-in-top">
          <AlertCircle className="w-4 h-4 text-error-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-error-600">
            {error}
          </p>
        </div>
      )}

      {/* Success message */}
      {success && !error && (
        <div className="mt-2 flex items-start gap-1 animate-slide-in-top">
          <CheckCircle className="w-4 h-4 text-success-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-success-600">
            {success}
          </p>
        </div>
      )}
    </div>
  );
};

export default Input;
