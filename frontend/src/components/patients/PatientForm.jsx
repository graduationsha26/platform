/**
 * PatientForm Component
 * Shared create/edit form for patient profiles with client-side validation.
 * Used by PatientCreatePage and PatientEditPage.
 */

import React, { useState, useEffect } from 'react';

const PHONE_REGEX = /^\+?[\d\s\-()]{7,20}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const EMPTY_FORM = {
  full_name: '',
  date_of_birth: '',
  contact_phone: '',
  contact_email: '',
  medical_notes: '',
};

const PatientForm = ({ initialValues, onSubmit, loading, submitError }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});

  // Pre-populate form fields when initialValues are provided (edit mode)
  useEffect(() => {
    if (initialValues) {
      setForm({
        full_name: initialValues.full_name || '',
        date_of_birth: initialValues.date_of_birth || '',
        contact_phone: initialValues.contact_phone || '',
        contact_email: initialValues.contact_email || '',
        medical_notes: initialValues.medical_notes || '',
      });
    }
  }, [initialValues]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear field error on change
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const validate = () => {
    const errors = {};

    if (!form.full_name.trim()) {
      errors.full_name = 'Full name is required.';
    }

    if (!form.date_of_birth) {
      errors.date_of_birth = 'Date of birth is required.';
    } else {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const dob = new Date(form.date_of_birth);
      if (dob > today) {
        errors.date_of_birth = 'Date of birth cannot be in the future.';
      }
    }

    if (form.contact_phone && !PHONE_REGEX.test(form.contact_phone)) {
      errors.contact_phone = 'Enter a valid phone number.';
    }

    if (form.contact_email && !EMAIL_REGEX.test(form.contact_email)) {
      errors.contact_email = 'Enter a valid email address.';
    }

    return errors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    // Build submission payload — omit empty optional fields
    const payload = { full_name: form.full_name.trim(), date_of_birth: form.date_of_birth };
    if (form.contact_phone.trim()) payload.contact_phone = form.contact_phone.trim();
    if (form.contact_email.trim()) payload.contact_email = form.contact_email.trim();
    if (form.medical_notes.trim()) payload.medical_notes = form.medical_notes.trim();

    onSubmit(payload);
  };

  const handleCancel = () => {
    window.history.back();
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* Top-level submit error banner */}
      {submitError && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {submitError}
        </div>
      )}

      {/* Full Name */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="full_name">
          Full Name <span className="text-red-500">*</span>
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

      {/* Date of Birth */}
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
          max={new Date().toISOString().split('T')[0]}
          className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
            fieldErrors.date_of_birth ? 'border-red-400' : 'border-neutral-300'
          }`}
        />
        {fieldErrors.date_of_birth && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.date_of_birth}</p>
        )}
      </div>

      {/* Contact Phone */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="contact_phone">
          Contact Phone
        </label>
        <input
          id="contact_phone"
          name="contact_phone"
          type="tel"
          value={form.contact_phone}
          onChange={handleChange}
          className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
            fieldErrors.contact_phone ? 'border-red-400' : 'border-neutral-300'
          }`}
          placeholder="+20 123 456 7890"
        />
        {fieldErrors.contact_phone && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.contact_phone}</p>
        )}
      </div>

      {/* Contact Email */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="contact_email">
          Contact Email
        </label>
        <input
          id="contact_email"
          name="contact_email"
          type="email"
          value={form.contact_email}
          onChange={handleChange}
          className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
            fieldErrors.contact_email ? 'border-red-400' : 'border-neutral-300'
          }`}
          placeholder="patient@example.com"
        />
        {fieldErrors.contact_email && (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.contact_email}</p>
        )}
      </div>

      {/* Medical Notes */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1" htmlFor="medical_notes">
          Medical Notes
        </label>
        <textarea
          id="medical_notes"
          name="medical_notes"
          rows={4}
          value={form.medical_notes}
          onChange={handleChange}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 resize-none"
          placeholder="Diagnosis, treatment notes, observations…"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {loading && (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4l-3 3-3-3h4z" />
            </svg>
          )}
          Save
        </button>
        <button
          type="button"
          onClick={handleCancel}
          disabled={loading}
          className="px-5 py-2 border border-neutral-300 text-sm font-medium rounded-lg hover:bg-neutral-50 disabled:opacity-60 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};

export default PatientForm;
