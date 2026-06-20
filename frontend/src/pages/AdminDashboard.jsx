import React from 'react';
import { useAuth } from '../hooks/useAuth';
import AppLayout from '../components/layout/AppLayout';
import SummaryCard from '../components/dashboard/SummaryCard';
import { useAdminStats } from '../hooks/useAdminStats';

const AdminDashboard = () => {
  const { user } = useAuth();
  const { data, loading, error } = useAdminStats();
  const hasError = Boolean(error);

  return (
    <AppLayout>
      <div className="page-container">
        <div className="dashboard-card">
          <h1 className="text-3xl sm:text-4xl font-bold text-neutral-900 mb-2">
            Admin Dashboard
          </h1>
          <p className="text-base text-neutral-600 mb-8">
            Welcome, <span className="font-semibold text-neutral-900">{user?.name}</span>!
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            <SummaryCard
              label="Total Doctors"
              subtitle="Doctors registered in the center"
              value={data?.total_doctors}
              loading={loading}
              error={hasError}
              variant="primary"
            />
            <SummaryCard
              label="Total Center Patients"
              subtitle="Patients enrolled across all doctors"
              value={data?.total_patients}
              loading={loading}
              error={hasError}
              variant="success"
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default AdminDashboard;
