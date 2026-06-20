/**
 * AdminPatientTable Component
 *
 * Feature 048: Patient Distribution (Admin)
 * Searchable, paginated center-wide roster of patients showing each patient's
 * name, assigned doctor (or an "Unassigned" badge), and registration date,
 * with a per-row Reassign action.
 */

import React from 'react';
import Pagination from '../common/Pagination';

const UnassignedBadge = () => (
  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
    Unassigned
  </span>
);

const formatDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString();
};

const AdminPatientTable = ({
  patients,
  loading,
  error,
  search,
  onSearchChange,
  currentPage,
  totalPages,
  onPageChange,
  onReassign,
}) => {
  return (
    <div>
      {/* Search input */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by name or email…"
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
      {!loading && error && <p className="text-red-600 text-sm">{error}</p>}

      {/* Empty states */}
      {!loading && !error && patients.length === 0 && !search && (
        <p className="text-neutral-500 text-sm py-8 text-center">
          No patients registered yet. Register your first patient.
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
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Assigned Doctor
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Registered
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 bg-white">
              {patients.map((patient) => (
                <tr key={patient.id} className="hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-neutral-900">
                    {patient.full_name || '—'}
                    {patient.contact_email && (
                      <div className="text-xs text-neutral-500 font-normal">
                        {patient.contact_email}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-600">
                    {patient.assigned_doctor ? (
                      patient.assigned_doctor.name
                    ) : (
                      <UnassignedBadge />
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-600">
                    {formatDate(patient.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => onReassign(patient)}
                      className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                    >
                      {patient.assigned_doctor ? 'Reassign' : 'Assign'}
                    </button>
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

export default AdminPatientTable;
