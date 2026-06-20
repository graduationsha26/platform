/**
 * RegisterPatientForm Component
 *
 * Feature 048: Patient Distribution (Admin)
 * Modal form for an admin to register a new patient and optionally assign a
 * doctor from a dropdown (active doctors only, sourced from feature 047's
 * doctor list endpoint).
 */

import React, { useState, useEffect } from 'react';
import { listDoctors } from '../../services/doctorService';

const EMPTY_FORM = {
  full_name: '',
  date_of_birth: '',
  contact_phone: '',
  contact_email: '',
  medical_notes: '',
  doctor_id: '',
};

const RegisterPatientForm = ({ open, onSubmit, onClose, loading, submitError }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [doctors, setDoctors] = useState([]);

  // Reset the form whenever the modal opens
  useEffect(() => {
    if (!open) return;
    setForm(EMPTY_FORM);
    setFieldErrors({});
  }, [open]);

  // Load active doctors for the dropdown when the modal opens
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    listDoctors({ page: 1 })
      .then((data) => {
        if (!cancelled) {
          const active = (data.results || []).filter((d) => d.is_active);
          setDoctors(active);
        }
      })
      .catch(() => {
        if (!cancelled) setDoctors([]);
      });
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const validate = () => {
    const errors = {};
    if (!form.full_name.trim()) errors.full_name = 'Name is required.';
    if (!form.date_of_birth) errors.date_of_birth = 'Date of birth is required.';
    return errors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    const payload = {
      full_name: form.full_name.trim(),
      date_of_birth: form.date_of_birth,
    };
    if (form.contact_phone.trim()) payload.contact_phone = form.contact_phone.trim();
    if (form.contact_email.trim()) payload.contact_email = form.contact_email.trim();
    if (form.medical_notes.trim()) payload.medical_notes = form.medical_notes.trim();
    if (form.doctor_id) payload.doctor_id = Number(form.doctor_id);
    onSubmit(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={loading ? undefined : onClose}
      />

      {/* Panel */}
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-neutral-900 mb-4">Register New Patient</h2>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {submitError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              {submitError}
            </div>
          )}

          {/* Full name */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="full_name">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              value={form.full_name}
              onChange={handleChange}
              className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
                fieldErrors.full_name ? 'border-red-400' : 'border-neutral-300'
              }`}
              placeholder="Patient's full name"
            />
            {fieldErrors.full_name && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.full_name}</p>
            )}
          </div>

          {/* Date of birth */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="date_of_birth">
              Date of Birth <span className="text-red-500">*</span>
            </label>
            <input
              id="date_of_birth"
              name="date_of_birth"
              type="date"
              value={form.date_of_birth}
              onChange={handleChange}
              className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
                fieldErrors.date_of_birth ? 'border-red-400' : 'border-neutral-300'
              }`}
            />
            {fieldErrors.date_of_birth && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.date_of_birth}</p>
            )}
          </div>

          {/* Contact phone */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="contact_phone">
              Phone
            </label>
            <input
              id="contact_phone"
              name="contact_phone"
              type="text"
              value={form.contact_phone}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              placeholder="+1234567890"
            />
          </div>

          {/* Contact email */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="contact_email">
              Email
            </label>
            <input
              id="contact_email"
              name="contact_email"
              type="email"
              value={form.contact_email}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              placeholder="patient@example.com"
            />
          </div>

          {/* Medical notes */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="medical_notes">
              Medical Notes
            </label>
            <textarea
              id="medical_notes"
              name="medical_notes"
              rows={3}
              value={form.medical_notes}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              placeholder="Optional clinical notes"
            />
          </div>

          {/* Doctor assignment */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="doctor_id">
              Assign Doctor
            </label>
            <select
              id="doctor_id"
              name="doctor_id"
              value={form.doctor_id}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 bg-white"
            >
              <option value="">Unassigned</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name || d.email}
                </option>
              ))}
            </select>
          </div>

          {/* Actions */}
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
              {loading ? 'Saving…' : 'Register'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterPatientForm;
