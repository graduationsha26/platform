/**
 * T024: Create AppRoutes component with React Router configuration
 * Application Routes Configuration
 */

import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ProtectedRoute from '../components/auth/ProtectedRoute';

// T056: Lazy load pages for better performance
const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const DoctorDashboard = lazy(() => import('../pages/DoctorDashboard'));

// Live tremor monitor page
const LiveTremorPage = lazy(() => import('../pages/LiveTremorPage'));

// Patient reports page
const PatientReportsPage = lazy(() => import('../pages/PatientReportsPage'));

// Patient management pages
const PatientListPage = lazy(() => import('../pages/PatientListPage'));
const PatientCreatePage = lazy(() => import('../pages/PatientCreatePage'));
const PatientDetailPage = lazy(() => import('../pages/PatientDetailPage'));
const PatientEditPage = lazy(() => import('../pages/PatientEditPage'));

const AppRoutes = () => {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* T038: Protected Dashboard Routes */}
      <Route
        path="/doctor/dashboard"
        element={
          <ProtectedRoute>
            <DoctorDashboard />
          </ProtectedRoute>
        }
      />

      {/* Patient Management Routes — order matters: /new before /:id */}
      <Route
        path="/doctor/patients"
        element={
          <ProtectedRoute>
            <PatientListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/new"
        element={
          <ProtectedRoute>
            <PatientCreatePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/:id"
        element={
          <ProtectedRoute>
            <PatientDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/:id/edit"
        element={
          <ProtectedRoute>
            <PatientEditPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/:id/monitor"
        element={
          <ProtectedRoute>
            <LiveTremorPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patients/:id/reports"
        element={
          <ProtectedRoute>
            <PatientReportsPage />
          </ProtectedRoute>
        }
      />

      {/* Default redirect to login */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Catch-all: redirect unknown routes to login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
};

export default AppRoutes;
