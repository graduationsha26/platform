/**
 * Form Validation Utilities
 * Reusable validation functions for React Hook Form
 */

/**
 * Email validation pattern (RFC 5322 simplified)
 */
export const emailPattern = {
  value: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  message: 'Please enter a valid email address',
};

/**
 * Password validation for registration
 * Requires: min 8 chars, at least one letter, at least one number
 */
export const passwordPattern = {
  value: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/,
  message: 'Password must be at least 8 characters and contain at least one letter and one number',
};

/**
 * Name validation (2-100 characters)
 */
export const nameValidation = {
  required: 'Name is required',
  minLength: {
    value: 2,
    message: 'Name must be at least 2 characters',
  },
  maxLength: {
    value: 100,
    message: 'Name must not exceed 100 characters',
  },
  pattern: {
    value: /^[a-zA-Z\s'-]+$/,
    message: 'Name can only contain letters, spaces, hyphens, and apostrophes',
  },
};

/**
 * Email validation rules for React Hook Form
 */
export const emailValidation = {
  required: 'Email is required',
  pattern: emailPattern,
};

/**
 * Password validation for login (just required, any password)
 */
export const passwordLoginValidation = {
  required: 'Password is required',
};

/**
 * Password validation for registration (strength requirements)
 */
export const passwordRegisterValidation = {
  required: 'Password is required',
  minLength: {
    value: 8,
    message: 'Password must be at least 8 characters',
  },
  pattern: passwordPattern,
};

/**
 * Password confirmation validation
 * @param {string} password - The password to match against
 * @returns {Object} Validation rules
 */
export const passwordConfirmValidation = (password) => ({
  required: 'Please confirm your password',
  validate: (value) => value === password || 'Passwords do not match',
});

/**
 * Role validation (doctor or admin)
 */
export const roleValidation = {
  required: 'Please select a role',
  validate: (value) =>
    ['doctor', 'admin'].includes(value) || 'Role must be either doctor or admin',
};
