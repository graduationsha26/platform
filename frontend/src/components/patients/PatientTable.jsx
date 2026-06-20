/**
 * PatientTable Component
 * Searchable, paginated table of patients with clickable rows.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import Pagination from '../common/Pagination';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(isoStr) {
  if (!isoStr) return 'No sessions';
  const d = new Date(isoStr);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const PatientTable = ({
  patients,
  loading,
  error,
  search,
  onSearchChange,
  currentPage,
  totalPages,
  onPageChange,
}) => {
  return (
    <div>
      {/* Search input */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by name…"
          className="w-full max-w-sm px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-neutral-100 rounded animate-pulse" />
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      {/* Empty states */}
      {!loading && !error && patients.length === 0 && !search && (
        <p className="text-neutral-500 text-sm py-8 text-center">
          No patients yet. Add your first patient.
        </p>
      )}
      {!loading && !error && patients.length === 0 && search && (
        <p className="text-neutral-500 text-sm py-8 text-center">
          No patients match your search.
        </p>
      )}

      {/* Patient table */}
      {!loading && !error && patients.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-200">
          <table className="min-w-full divide-y divide-neutral-200">
            <thead>
              <tr className="bg-neutral-50">
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Full Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Date of Birth
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Last Session
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 bg-white">
              {patients.map((patient) => (
                <tr key={patient.id} className="hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-neutral-900">
                    {patient.full_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-600">
                    {formatDate(patient.date_of_birth)}
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-600">
                    {formatDateTime(patient.last_session_date)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/doctor/patients/${patient.id}`}
                      className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                    >
                      →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
};

export default PatientTable;
