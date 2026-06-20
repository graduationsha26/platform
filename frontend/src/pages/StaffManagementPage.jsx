/**
 * StaffManagementPage
 *
 * Feature 047: Staff (Doctor) Management
 * Admin page at /admin/doctors — doctor roster with add/edit modal and
 * per-row deactivate/reactivate toggle.
 */

import React, { useState } from 'react';
import AppLayout from '../components/layout/AppLayout';
import DoctorManagementTable from '../components/admin/DoctorManagementTable';
import DoctorFormModal from '../components/admin/DoctorFormModal';
import { useDoctors } from '../hooks/useDoctors';
import { createDoctor, updateDoctor } from '../services/doctorService';

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

const StaffManagementPage = () => {
  const {
    doctors,
    totalCount,
    currentPage,
    totalPages,
    loading,
    error,
    search,
    setSearch,
    setPage,
    refresh,
  } = useDoctors();

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('add');
  const [editingDoctor, setEditingDoctor] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [togglingId, setTogglingId] = useState(null);

  const openAdd = () => {
    setModalMode('add');
    setEditingDoctor(null);
    setSubmitError(null);
    setModalOpen(true);
  };

  const openEdit = (doctor) => {
    setModalMode('edit');
    setEditingDoctor(doctor);
    setSubmitError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (submitting) return;
    setModalOpen(false);
  };

  const handleSubmit = async (payload) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (modalMode === 'edit' && editingDoctor) {
        await updateDoctor(editingDoctor.id, payload);
      } else {
        await createDoctor(payload);
      }
      setModalOpen(false);
      refresh();
    } catch (err) {
      setSubmitError(extractError(err, 'Failed to save doctor.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (doctor) => {
    if (togglingId) return;
    setTogglingId(doctor.id);
    try {
      await updateDoctor(doctor.id, { is_active: !doctor.is_active });
      refresh();
    } catch {
      // Surface failure via the roster error path on next load; keep page stable.
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <AppLayout>
      <div className="p-6">
        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Staff Management</h1>
            {!loading && !error && (
              <p className="text-sm text-neutral-500 mt-1">
                {totalCount} doctor{totalCount !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={openAdd}
            className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
          >
            Add Doctor
          </button>
        </div>

        <DoctorManagementTable
          doctors={doctors}
          loading={loading}
          error={error}
          search={search}
          onSearchChange={setSearch}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setPage}
          onEdit={openEdit}
          onToggleActive={handleToggleActive}
          togglingId={togglingId}
        />
      </div>

      <DoctorFormModal
        open={modalOpen}
        mode={modalMode}
        initialValues={editingDoctor}
        onSubmit={handleSubmit}
        onClose={closeModal}
        loading={submitting}
        submitError={submitError}
      />
    </AppLayout>
  );
};

export default StaffManagementPage;
