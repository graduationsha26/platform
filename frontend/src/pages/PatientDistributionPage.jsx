/**
 * PatientDistributionPage
 *
 * Feature 048: Patient Distribution (Admin)
 * Admin page at /admin/patients — center-wide patient roster with a register
 * modal and per-row assign/reassign modal.
 */

import React, { useState } from 'react';
import AppLayout from '../components/layout/AppLayout';
import AdminPatientTable from '../components/admin/AdminPatientTable';
import RegisterPatientForm from '../components/admin/RegisterPatientForm';
import AssignDoctorModal from '../components/admin/AssignDoctorModal';
import { useAdminPatients } from '../hooks/useAdminPatients';
import { registerPatient, assignPatient } from '../services/adminPatientService';

/** Flatten a DRF error response body into a single readable message. */
function extractError(err, fallback) {
  const data = err?.response?.data;
  if (data && typeof data === 'object') {
    const parts = [];
    for (const value of Object.values(data)) {
      if (Array.isArray(value)) parts.push(value.join(' '));
      else if (typeof value === 'string') parts.push(value);
    }
    if (parts.length) return parts.join(' ');
  }
  return fallback;
}

const PatientDistributionPage = () => {
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
    refresh,
  } = useAdminPatients();

  // Register modal state
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState(null);

  // Assign / reassign modal state
  const [assignTarget, setAssignTarget] = useState(null);
  const [assigning, setAssigning] = useState(false);
  const [assignError, setAssignError] = useState(null);

  const openRegister = () => {
    setRegisterError(null);
    setRegisterOpen(true);
  };

  const closeRegister = () => {
    if (registering) return;
    setRegisterOpen(false);
  };

  const handleRegister = async (payload) => {
    setRegistering(true);
    setRegisterError(null);
    try {
      await registerPatient(payload);
      setRegisterOpen(false);
      refresh();
    } catch (err) {
      setRegisterError(extractError(err, 'Failed to register patient.'));
    } finally {
      setRegistering(false);
    }
  };

  const openReassign = (patient) => {
    setAssignError(null);
    setAssignTarget(patient);
  };

  const closeReassign = () => {
    if (assigning) return;
    setAssignTarget(null);
  };

  const handleAssign = async (doctorId) => {
    if (!assignTarget) return;
    setAssigning(true);
    setAssignError(null);
    try {
      await assignPatient(assignTarget.id, doctorId);
      setAssignTarget(null);
      refresh();
    } catch (err) {
      setAssignError(extractError(err, 'Failed to assign doctor.'));
    } finally {
      setAssigning(false);
    }
  };

  return (
    <AppLayout>
      <div className="p-6">
        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Patient Distribution</h1>
            {!loading && !error && (
              <p className="text-sm text-neutral-500 mt-1">
                {totalCount} patient{totalCount !== 1 ? 's' : ''} across the center
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={openRegister}
            className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Register Patient
          </button>
        </div>

        <AdminPatientTable
          patients={patients}
          loading={loading}
          error={error}
          search={search}
          onSearchChange={setSearch}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setPage}
          onReassign={openReassign}
        />
      </div>

      <RegisterPatientForm
        open={registerOpen}
        onSubmit={handleRegister}
        onClose={closeRegister}
        loading={registering}
        submitError={registerError}
      />

      <AssignDoctorModal
        open={assignTarget !== null}
        patient={assignTarget}
        onSubmit={handleAssign}
        onClose={closeReassign}
        loading={assigning}
        submitError={assignError}
      />
    </AppLayout>
  );
};

export default PatientDistributionPage;
