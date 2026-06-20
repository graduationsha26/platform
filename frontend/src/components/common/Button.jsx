import React from 'react';

const Button = ({
  type = 'button',
  variant = 'primary',
  children,
  disabled = false,
  loading = false,
  className = '',
  onClick,
  ...props
}) => {
  // Base classes with micro-interactions (T032, T045: touch-action via style prop)
  const baseClasses = `
    px-4 py-2 rounded-lg font-medium touch-target
    transition-all duration-200
    focus:outline-none focus:ring-4 focus:ring-offset-2
    active:scale-95
  `;

  // Variant classes with medical color scheme (T032, T033)
  const variantClasses = {
    primary: `
      bg-primary-600 text-white
      hover:bg-primary-700 hover:shadow-md hover:-translate-y-0.5
      focus:ring-primary-300
      disabled:bg-primary-300 disabled:cursor-not-allowed
      ${loading ? 'opacity-70 cursor-wait' : ''}
    `,
    secondary: `
      bg-neutral-200 text-neutral-800
      hover:bg-neutral-300 hover:shadow-md hover:-translate-y-0.5
      focus:ring-neutral-300
      disabled:bg-neutral-100 disabled:text-neutral-400 disabled:cursor-not-allowed
      ${loading ? 'opacity-70 cursor-wait' : ''}
    `,
    danger: `
      bg-error-600 text-white
      hover:bg-error-700 hover:shadow-md hover:-translate-y-0.5
      focus:ring-error-300
      disabled:bg-error-300 disabled:cursor-not-allowed
      ${loading ? 'opacity-70 cursor-wait' : ''}
    `,
    success: `
      bg-success-600 text-white
      hover:bg-success-700 hover:shadow-md hover:-translate-y-0.5
      focus:ring-success-300
      disabled:bg-success-300 disabled:cursor-not-allowed
      ${loading ? 'opacity-70 cursor-wait' : ''}
    `,
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={{ touchAction: 'manipulation' }}
      {...props}
    >
      {/* T033: Loading state with spinner */}
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          {children}
        </span>
      ) : (
        children
      )}
    </button>
  );
};

export default Button;
