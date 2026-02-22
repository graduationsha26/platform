/**
 * PatientDetailPage
 * Shows a patient's full profile card and paginated session history.
 */

import React from 'react';
import { Link, useParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import SessionHistoryList from '../components/patients/SessionHistoryList';
import { usePatient } from '../hooks/usePatient';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

const ProfileField = ({ label, value }) => {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs font-medium text-neutral-500 uppercase tracking-wide">{label}</dt>
      <dd className="mt-1 text-sm text-neutral-900">{value}</dd>
    </div>
  );
};

const PatientDetailPage = () => {
  const { id } = useParams();
  const {
    patient,
    sessions,
    sessionCount,
    sessionPage,
    sessionTotalPages,
    loading,
    sessionsLoading,
    error,
    setSessionPage,
  } = usePatient(id);

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6 space-y-4">
          <div className="h-8 w-48 bg-neutral-100 rounded animate-pulse" />
          <div className="h-40 bg-neutral-100 rounded animate-pulse" />
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <div className="p-6">
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <Link to="/doctor/patients" className="text-primary-600 hover:underline text-sm">
            ← Back to patients
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link
              to="/doctor/patients"
              className="text-sm text-neutral-500 hover:text-neutral-700 mb-1 block"
            >
              ← Patients
            </Link>
            <h1 className="text-2xl font-bold text-neutral-900">{patient?.full_name}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/doctor/patients/${id}/reports`}
              className="px-4 py-2 border border-neutral-300 text-sm font-medium rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Reports
            </Link>
            <Link
              to={`/doctor/patients/${id}/monitor`}
              className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
            >
              Live Monitor
            </Link>
            <Link
              to={`/doctor/patients/${id}/edit`}
              className="px-4 py-2 border border-neutral-300 text-sm font-medium rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Edit
            </Link>
          </div>
        </div>

        {/* Profile card */}
        <div className="bg-white border border-neutral-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-4">Patient Profile</h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ProfileField label="Date of Birth" value={formatDate(patient?.date_of_birth)} />
            <ProfileField label="Contact Phone" value={patient?.contact_phone} />
            <ProfileField label="Contact Email" value={patient?.contact_email} />
            {patient?.medical_notes && (
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Medical Notes
                </dt>
                <dd className="mt-1 text-sm text-neutral-900 whitespace-pre-wrap">
                  {patient.medical_notes}
                </dd>
              </div>
            )}
            {patient?.paired_device && (
              <ProfileField
                label="Paired Device"
                value={`${patient.paired_device.serial_number} (${patient.paired_device.status})`}
              />
            )}
          </dl>
        </div>

        {/* Session history */}
        <div className="bg-white border border-neutral-200 rounded-xl p-6">
          <SessionHistoryList
            sessions={sessions}
            loading={sessionsLoading}
            error={null}
            currentPage={sessionPage}
            totalPages={sessionTotalPages}
            onPageChange={setSessionPage}
          />
        </div>
      </div>
    </AppLayout>
  );
};

export default PatientDetailPage;
