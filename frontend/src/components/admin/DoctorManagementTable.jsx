/**
 * DoctorManagementTable Component
 *
 * Feature 047: Staff (Doctor) Management
 * Searchable, paginated roster of doctors showing name, assigned patient count,
 * and account status, with per-row Edit and Deactivate/Reactivate actions.
 */

import React from 'react';
import Pagination from '../common/Pagination';

const StatusBadge = ({ active }) => (
  <span
    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
      active
        ? 'bg-green-100 text-green-800'
        : 'bg-neutral-200 text-neutral-600'
    }`}
  >
    {active ? 'Active' : 'Inactive'}
  </span>
);

const DoctorManagementTable = ({
  doctors,
  loading,
  error,
  search,
  onSearchChange,
  currentPage,
  totalPages,
  onPageChange,
  onEdit,
  onToggleActive,
  togglingId,
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
      {!loading && error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      {/* Empty states */}
      {!loading && !error && doctors.length === 0 && !search && (
        <p className="text-neutral-500 text-sm py-8 text-center">
          No doctors yet. Add your first doctor.
        </p>
      )}
      {!loading && !error && doctors.length === 0 && search && (
        <p className="text-neutral-500 text-sm py-8 text-center">
          No doctors match your search.
        </p>
      )}

      {/* Doctor table */}
      {!loading && !error && doctors.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-200">
          <table className="min-w-full divide-y divide-neutral-200">
            <thead>
              <tr className="bg-neutral-50">
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Patients
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 bg-white">
              {doctors.map((doctor) => (
                <tr key={doctor.id} className="hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-neutral-900">
                    {doctor.name || '—'}
                    <div className="text-xs text-neutral-500 font-normal">{doctor.email}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-600">
                    {doctor.patient_count}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <StatusBadge active={doctor.is_active} />
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => onEdit(doctor)}
                      className="text-primary-600 hover:text-primary-800 text-sm font-medium mr-4"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onToggleActive(doctor)}
                      disabled={togglingId === doctor.id}
                      className={`text-sm font-medium disabled:opacity-50 ${
                        doctor.is_active
                          ? 'text-red-600 hover:text-red-800'
                          : 'text-green-600 hover:text-green-800'
                      }`}
                    >
                      {doctor.is_active ? 'Deactivate' : 'Reactivate'}
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

export default DoctorManagementTable;
