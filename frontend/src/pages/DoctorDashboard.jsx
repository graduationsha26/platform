/**
 * Doctor Dashboard Page
 *
 * Feature 032: Dashboard Overview Page
 * Displays three live summary cards (total patients, active devices, alerts)
 * and a 7-day tremor trend line chart, all scoped to the logged-in doctor.
 */

import React from 'react';
import { useAuth } from '../hooks/useAuth';
import AppLayout from '../components/layout/AppLayout';
import SummaryCard from '../components/dashboard/SummaryCard';
import TremorTrendChart from '../components/dashboard/TremorTrendChart';
import { useDashboardStats } from '../hooks/useDashboardStats';

const DoctorDashboard = () => {
  const { user } = useAuth();
  const { data, loading, error } = useDashboardStats();

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
              label="Alerts"
              subtitle="Severe tremor events (last 24h)"
              value={data?.alerts_count}
              loading={loading}
              error={hasError}
              variant="warning"
            />
          </div>

          {/* 7-day tremor trend chart */}
          <div className="mt-8">
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              7-Day Tremor Trend
            </h2>
            <TremorTrendChart
              data={data?.tremor_trend ?? null}
              loading={loading}
              error={hasError}
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default DoctorDashboard;
