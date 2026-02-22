/**
 * SessionHistoryList Component
 * Displays a paginated table of biometric sessions with ML severity badges.
 */

import React from 'react';
import Pagination from '../common/Pagination';

function formatDateTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(durationStr) {
  // Input format: "HH:MM:SS" or "D days, HH:MM:SS"
  if (!durationStr) return '—';
  const parts = durationStr.split(':');
  if (parts.length < 3) return durationStr;
  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);
  const seconds = parseInt(parts[2], 10);

  const segments = [];
  if (hours > 0) segments.push(`${hours}h`);
  if (minutes > 0) segments.push(`${minutes}m`);
  if (seconds > 0 || segments.length === 0) segments.push(`${seconds}s`);
  return segments.join(' ');
}

const SEVERITY_BADGE = {
  mild: 'bg-green-100 text-green-800',
  moderate: 'bg-amber-100 text-amber-800',
  severe: 'bg-red-100 text-red-800',
};

const SeverityBadge = ({ severity }) => {
  if (!severity) {
    return <span className="text-xs text-neutral-400">No prediction</span>;
  }
  const classes = SEVERITY_BADGE[severity] || 'bg-neutral-100 text-neutral-600';
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${classes}`}>
      {severity}
    </span>
  );
};

const SessionHistoryList = ({
  sessions,
  loading,
  error,
  currentPage,
  totalPages,
  onPageChange,
}) => {
  return (
    <div>
      <h2 className="text-lg font-semibold text-neutral-900 mb-3">Session History</h2>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 bg-neutral-100 rounded animate-pulse" />
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      {/* Empty state */}
      {!loading && !error && sessions.length === 0 && (
        <p className="text-neutral-500 text-sm py-6 text-center">
          No monitoring sessions recorded yet.
        </p>
      )}

      {/* Sessions table */}
      {!loading && !error && sessions.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-neutral-200">
          <table className="min-w-full divide-y divide-neutral-200">
            <thead>
              <tr className="bg-neutral-50">
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Date & Time
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  Duration
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wide">
                  ML Severity
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 bg-white">
              {sessions.map((session) => (
                <tr key={session.id} className="hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3 text-sm text-neutral-700">
                    {formatDateTime(session.session_start)}
                  </td>
                  <td className="px-4 py-3 text-sm text-neutral-700">
                    {formatDuration(session.session_duration)}
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={session.ml_prediction_severity} />
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

export default SessionHistoryList;
