/**
 * PatientEditPage
 * Pre-populates PatientForm with existing patient data.
 * On success, navigates back to the patient's detail page.
 */

import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import PatientForm from '../components/patients/PatientForm';
import { getPatient, updatePatient } from '../services/patientService';

const PatientEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialValues, setInitialValues] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Fetch patient data to pre-populate form
  useEffect(() => {
    let cancelled = false;
    getPatient(id)
      .then((data) => {
        if (!cancelled) setInitialValues(data);
      })
      .catch(() => {
        if (!cancelled) setFetchError('Could not load patient data.');
      });
    return () => { cancelled = true; };
  }, [id]);

  const handleSubmit = async (formData) => {
    setLoading(true);
    setSubmitError(null);
    try {
      await updatePatient(id, formData);
      navigate(`/doctor/patients/${id}`);
    } catch (err) {
      const message =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        'Failed to update patient. Please try again.';
      setSubmitError(message);
      setLoading(false);
    }
  };

  // Loading skeleton while fetching patient
  if (!initialValues && !fetchError) {
    return (
      <AppLayout>
        <div className="p-6 space-y-4 max-w-2xl">
          <div className="h-8 w-48 bg-neutral-100 rounded animate-pulse" />
          <div className="h-64 bg-neutral-100 rounded animate-pulse" />
        </div>
      </AppLayout>
    );
  }

  if (fetchError) {
    return (
      <AppLayout>
        <div className="p-6">
          <p className="text-red-600 text-sm mb-4">{fetchError}</p>
          <Link to="/doctor/patients" className="text-primary-600 hover:underline text-sm">
            ← Back to patients
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="p-6 max-w-2xl">
        <div className="mb-6">
          <Link
            to={`/doctor/patients/${id}`}
            className="text-sm text-neutral-500 hover:text-neutral-700 block mb-1"
          >
            ← Back to patient
          </Link>
          <h1 className="text-2xl font-bold text-neutral-900">Edit Patient</h1>
        </div>
        <div className="bg-white border border-neutral-200 rounded-xl p-6">
          <PatientForm
            initialValues={initialValues}
            onSubmit={handleSubmit}
            loading={loading}
            submitError={submitError}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default PatientEditPage;
