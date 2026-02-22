/**
 * PatientReportsPage
 * Date range statistics preview and PDF download for a specific patient.
 *
 * Assembled across two user stories:
 *  US1 — DateRangePicker + StatsPreview (default 30-day load on mount)
 *  US2 — Download PDF button
 *
 * Feature 035: Reports Page & PDF Download
 */

import { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DateRangePicker from '../components/reports/DateRangePicker';
import StatsPreview from '../components/reports/StatsPreview';
import { usePatientReport } from '../hooks/usePatientReport';

const PatientReportsPage = () => {
  const { id } = useParams();

  const {
    dateRange,
    setDateRange,
    stats,
    statsLoading,
    statsError,
    applyDateRange,
    downloadLoading,
    downloadError,
    downloadPDF,
  } = usePatientReport(id);

  // Load default 30-day range on mount
  useEffect(() => {
    applyDateRange();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Access-denied state
  const isAccessDenied =
    statsError && (statsError.includes('403') || statsError.toLowerCase().includes('access'));

  if (isAccessDenied) {
    return (
      <AppLayout>
        <div className="p-6 space-y-4">
          <Link
            to="/doctor/patients"
            className="text-sm text-neutral-500 hover:text-neutral-700 block"
          >
            ← Back to patients
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-800 font-semibold mb-1">Access Denied</p>
            <p className="text-red-700 text-sm">
              You do not have access to this patient's reports.
            </p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="p-6 space-y-6 max-w-3xl">

        {/* Header */}
        <div>
          <Link
            to={`/doctor/patients/${id}`}
            className="text-sm text-neutral-500 hover:text-neutral-700 block mb-1"
          >
            ← Back to patient
          </Link>
          <h1 className="text-2xl font-bold text-neutral-900">Reports</h1>
        </div>

        {/* Main card */}
        <div className="bg-white border border-neutral-200 rounded-xl p-6 space-y-6">

          {/* Date range picker */}
          <DateRangePicker
            startDate={dateRange.startDate}
            endDate={dateRange.endDate}
            onChange={(s, e) => setDateRange({ startDate: s, endDate: e })}
            onApply={applyDateRange}
            loading={statsLoading}
          />

          {/* Stats preview */}
          <StatsPreview
            stats={stats}
            loading={statsLoading}
            error={isAccessDenied ? null : statsError}
          />

          {/* Download PDF — US2 */}
          <div className="pt-4 border-t border-neutral-100">
            <button
              onClick={downloadPDF}
              disabled={downloadLoading || !stats?.hasData}
              className="px-6 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-2"
            >
              {downloadLoading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Generating…
                </>
              ) : (
                'Download PDF'
              )}
            </button>

            {!stats?.hasData && !statsLoading && (
              <p className="text-xs text-neutral-400 mt-2">
                Select a date range with data to enable download.
              </p>
            )}

            {downloadError && (
              <p className="text-sm text-red-600 mt-2">{downloadError}</p>
            )}
          </div>

        </div>
      </div>
    </AppLayout>
  );
};

export default PatientReportsPage;
