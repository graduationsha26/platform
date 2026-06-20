/**
 * PatientCreatePage
 * Doctor fills a form to create a new patient.
 * On success, navigates to the new patient's detail page.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import PatientForm from '../components/patients/PatientForm';
import { createPatient } from '../services/patientService';

const PatientCreatePage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const patient = await createPatient(formData);
      navigate(`/doctor/patients/${patient.id}`);
    } catch (err) {
      const message =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        'Failed to create patient. Please try again.';
      setError(message);
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="p-6 max-w-2xl">
        <h1 className="text-2xl font-bold text-neutral-900 mb-6">Add New Patient</h1>
        <div className="bg-white border border-neutral-200 rounded-xl p-6">
          <PatientForm onSubmit={handleSubmit} loading={loading} submitError={error} />
        </div>
      </div>
    </AppLayout>
  );
};

export default PatientCreatePage;
