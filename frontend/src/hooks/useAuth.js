/**
 * useAuth Hook
 * T018: Create useAuth custom hook to access AuthContext
 * Custom hook for accessing authentication context
 */

import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};

export default useAuth;
