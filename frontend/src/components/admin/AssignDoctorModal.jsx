/**
 * AssignDoctorModal Component
 *
 * Feature 048: Patient Distribution (Admin)
 * Lightweight modal to assign or reassign a single patient to a doctor.
 * Doctor options come from feature 047's doctor list endpoint (active only).
 */

import React, { useState, useEffect } from 'react';
import { listDoctors } from '../../services/doctorService';

const AssignDoctorModal = ({ open, patient, onSubmit, onClose, loading, submitError }) => {
  const [doctorId, setDoctorId] = useState('');
  const [doctors, setDoctors] = useState([]);
  const [fieldError, setFieldError] = useState(null);

  // Pre-select the patient's current doctor (if any) and reset on open
  useEffect(() => {
    if (!open) return;
    setDoctorId(patient?.assigned_doctor ? String(patient.assigned_doctor.id) : '');
    setFieldError(null);
  }, [open, patient]);

  // Load active doctors when the modal opens
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    listDoctors({ page: 1 })
      .then((data) => {
        if (!cancelled) {
          setDoctors((data.results || []).filter((d) => d.is_active));
        }
      })
      .catch(() => {
        if (!cancelled) setDoctors([]);
      });
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!doctorId) {
      setFieldError('Please select a doctor.');
      return;
    }
    onSubmit(Number(doctorId));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={loading ? undefined : onClose}
      />

      {/* Panel */}
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-neutral-900 mb-1">
          {patient?.assigned_doctor ? 'Reassign Patient' : 'Assign Patient'}
        </h2>
        {patient && (
          <p className="text-sm text-neutral-500 mb-4">{patient.full_name}</p>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {submitError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              {submitError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="assign_doctor_id">
              Doctor <span className="text-red-500">*</span>
            </label>
            <select
              id="assign_doctor_id"
              value={doctorId}
              onChange={(e) => {
                setDoctorId(e.target.value);
                if (fieldError) setFieldError(null);
              }}
              className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 bg-white ${
                fieldError ? 'border-red-400' : 'border-neutral-300'
              }`}
            >
              <option value="">Select a doctor…</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name || d.email}
                </option>
              ))}
            </select>
            {fieldError && <p className="mt-1 text-xs text-red-600">{fieldError}</p>}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-neutral-300 text-sm font-medium rounded-lg hover:bg-neutral-50 disabled:opacity-60 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Saving…' : 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AssignDoctorModal;
