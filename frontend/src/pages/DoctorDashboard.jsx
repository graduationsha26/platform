/**
 * Doctor Dashboard Page
 *
 * Feature 032: Dashboard Overview Page
 * Displays three live summary cards (total patients, active devices, critical alerts)
 * scoped to the logged-in doctor.
 */

import React from 'react';
import { useAuth } from '../hooks/useAuth';
import AppLayout from '../components/layout/AppLayout';
import SummaryCard from '../components/dashboard/SummaryCard';
import PatientOverviewGrid from '../components/dashboard/PatientOverviewGrid';
import { useDashboardStats } from '../hooks/useDashboardStats';
import { useCriticalAlerts } from '../hooks/useCriticalAlerts';

const DoctorDashboard = () => {
  const { user } = useAuth();
  const { data, loading, error } = useDashboardStats();
  const { data: alertsData, loading: alertsLoading, error: alertsError } = useCriticalAlerts();

  const hasError = Boolean(error);

  return (
    <AppLayout>
      <div className="page-container">
        <div className="dashboard-card">
          <h1 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-2">
            Doctor Dashboard
          </h1>
          <p className="text-base text-neutral-600 mb-8">
            Welcome, <span className="font-semibold text-neutral-900">{user?.name}</span>!
          </p>

          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
            <SummaryCard
              label="Patients"
              subtitle="Total patients under care"
              value={data?.total_patients}
              loading={loading}
              error={hasError}
              variant="primary"
            />

            <SummaryCard
              label="Active Devices"
              subtitle="Devices currently online"
              value={data?.active_devices}
              loading={loading}
              error={hasError}
              variant="success"
            />

            <SummaryCard
              label="Critical Alerts"
              subtitle="Patients with 5+ consecutive severe days"
              value={alertsData?.count}
              loading={alertsLoading}
              error={Boolean(alertsError)}
              variant="warning"
            />
          </div>
        </div>

        <div className="mt-8">
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">Your Patients</h2>
          <PatientOverviewGrid />
        </div>
      </div>
    </AppLayout>
  );
};

export default DoctorDashboard;
