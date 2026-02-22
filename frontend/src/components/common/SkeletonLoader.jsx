/**
 * T061: SkeletonLoader Component
 * Skeleton screens for improved perceived performance
 * Shows placeholder content while actual data loads
 */

import React from 'react';

const SkeletonLoader = ({ variant = 'text', width = '100%', height, className = '', count = 1 }) => {
  // Variant presets for common skeleton types
  const variantClasses = {
    text: 'h-4 rounded', // Single line of text
    title: 'h-6 rounded', // Larger heading
    circle: 'rounded-full', // Avatar/icon
    rectangle: 'rounded-lg', // Card/image
    card: 'h-32 rounded-lg', // Full card
  };

  // Base skeleton styles with shimmer animation
  const baseClasses = 'bg-neutral-200 animate-pulse';

  // Generate skeleton elements based on count
  const skeletons = Array.from({ length: count }, (_, index) => (
    <div
      key={index}
      className={`${baseClasses} ${variantClasses[variant]} ${className} ${index > 0 ? 'mt-2' : ''}`}
      style={{
        width: width,
        height: height || (variant === 'circle' ? width : undefined),
      }}
      aria-hidden="true"
    />
  ));

  return <>{skeletons}</>;
};

// Preset skeleton components for common use cases
export const SkeletonText = ({ lines = 3, ...props }) => (
  <SkeletonLoader variant="text" count={lines} {...props} />
);

export const SkeletonTitle = (props) => (
  <SkeletonLoader variant="title" width="60%" {...props} />
);

export const SkeletonCircle = ({ size = '3rem', ...props }) => (
  <SkeletonLoader variant="circle" width={size} {...props} />
);

export const SkeletonCard = (props) => (
  <SkeletonLoader variant="card" {...props} />
);

// Dashboard card skeleton with complete structure
export const SkeletonDashboardCard = () => (
  <div className="bg-white border border-neutral-200 rounded-lg p-6 animate-pulse">
    <div className="flex items-center justify-between mb-4">
      <div className="h-4 bg-neutral-200 rounded w-1/3"></div>
      <div className="h-8 w-8 bg-neutral-200 rounded-full"></div>
    </div>
    <div className="h-10 bg-neutral-200 rounded w-1/2 mb-2"></div>
    <div className="h-3 bg-neutral-200 rounded w-2/3"></div>
  </div>
);

export default SkeletonLoader;
