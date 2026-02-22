/**
 * LiveTremorPage
 * Real-time tremor monitoring page for a specific patient.
 * Feature 034: Live Tremor Monitor Page
 *
 * Assembled incrementally:
 *  US1 — ConnectionStatus + AmplitudeChart
 *  US2 — SpectrumChart
 *  US3 — SeverityIndicator
 *  US4 — RawValuesPanel + no-stream overlay
 */

import { Link, useParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import ConnectionStatus from '../components/tremor/ConnectionStatus';
import AmplitudeChart from '../components/tremor/AmplitudeChart';
import SpectrumChart from '../components/tremor/SpectrumChart';
import SeverityIndicator from '../components/tremor/SeverityIndicator';
import RawValuesPanel from '../components/tremor/RawValuesPanel';
import { useTremorMonitor } from '../hooks/useTremorMonitor';

const LiveTremorPage = () => {
  const { id } = useParams();

  const {
    connectionStatus,
    accessDenied,
    chartData,
    spectrumData,
    severity,
    rawValues,
    hasActiveStream,
  } = useTremorMonitor(id);

  const isStale = connectionStatus === 'disconnected';

  if (accessDenied) {
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
              You do not have access to this patient's live monitor.
            </p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="p-6 space-y-6 max-w-5xl">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link
              to={`/doctor/patients/${id}`}
              className="text-sm text-neutral-500 hover:text-neutral-700 block mb-1"
            >
              ← Back to patient
            </Link>
            <h1 className="text-2xl font-bold text-neutral-900">Live Tremor Monitor</h1>
          </div>
          <ConnectionStatus status={connectionStatus} />
        </div>

        {/* No Active Stream Banner */}
        {connectionStatus === 'connected' && !hasActiveStream && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-start gap-3">
            <svg className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-amber-800">No active data stream</p>
              <p className="text-sm text-amber-700 mt-0.5">Check that the patient's device is powered on and connected.</p>
            </div>
          </div>
        )}

        {/* Top Row: Severity + Raw Values */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border border-neutral-200 rounded-xl p-4">
            <h2 className="text-sm font-semibold text-neutral-700 mb-3">Severity</h2>
            <SeverityIndicator severity={severity} isStale={isStale} />
          </div>
          <div className="bg-white border border-neutral-200 rounded-xl p-4">
            <h2 className="text-sm font-semibold text-neutral-700 mb-3">Raw Sensor Values</h2>
            <RawValuesPanel rawValues={rawValues} isStale={isStale} />
          </div>
        </div>

        {/* Amplitude Chart */}
        <div className="bg-white border border-neutral-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-neutral-700 mb-3">Tremor Amplitude (rolling 60 s)</h2>
          <AmplitudeChart data={chartData} isStale={isStale} />
        </div>

        {/* FFT Spectrum Chart */}
        <div className="bg-white border border-neutral-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-neutral-700 mb-3">Frequency Spectrum (dominant axis)</h2>
          <SpectrumChart data={spectrumData} isStale={isStale} />
        </div>

      </div>
    </AppLayout>
  );
};

export default LiveTremorPage;
