/**
 * PatientListPage
 * Displays a searchable, paginated list of the doctor's assigned patients.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import PatientTable from '../components/patients/PatientTable';
import { usePatients } from '../hooks/usePatients';

const PatientListPage = () => {
  const {
    patients,
    totalCount,
    currentPage,
    totalPages,
    loading,
    error,
    search,
    setSearch,
    setPage,
  } = usePatients();

  return (
    <AppLayout>
      <div className="p-6">
        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Patients</h1>
            {!loading && !error && (
              <p className="text-sm text-neutral-500 mt-1">
                {totalCount} patient{totalCount !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          <Link
            to="/doctor/patients/new"
            className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Add Patient
          </Link>
        </div>

        <PatientTable
          patients={patients}
          loading={loading}
          error={error}
          search={search}
          onSearchChange={setSearch}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </div>
    </AppLayout>
  );
};

export default PatientListPage;
