/**
 * T060: Enhanced LoadingSpinner Component
 * Professional circular spinner with medical color scheme
 */

import React from 'react';

const LoadingSpinner = ({ size = 'md', color = 'primary', className = '' }) => {
  // T060: Size variants (sm: 16px, md: 32px, lg: 48px)
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  // T060: Medical color scheme
  const colorClasses = {
    primary: 'border-primary-600 border-t-transparent',
    secondary: 'border-secondary-600 border-t-transparent',
    white: 'border-white border-t-transparent',
    neutral: 'border-neutral-600 border-t-transparent',
  };

  return (
    <div className={`flex justify-center items-center ${className}`}>
      <div
        className={`
          ${sizeClasses[size]}
          ${colorClasses[color]}
          rounded-full animate-spin
        `}
        style={{ animationDuration: '1s' }}
        role="status"
        aria-label="Loading"
      />
    </div>
  );
};

export default LoadingSpinner;
