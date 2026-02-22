/**
 * T035-T037: Create ProtectedRoute wrapper component
 * Protected Route Component
 * Ensures only authenticated users can access wrapped routes
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import LoadingSpinner from '../common/LoadingSpinner';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking auth state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // T036: Redirect unauthenticated users to login
  // T037: Store attempted URL in location state for post-login redirect
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  // User is authenticated, render the protected content
  return children;
};

export default ProtectedRoute;
