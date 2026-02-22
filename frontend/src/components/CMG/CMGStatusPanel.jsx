/**
 * CMGStatusPanel
 * Displays real-time CMG rotor motor state: RPM, current draw, and operational status.
 *
 * Receives live cmg_telemetry WebSocket messages from its parent's WebSocket hook.
 * Fetches initial state via REST on mount.
 *
 * Feature 027: CMG Brushless Motor & ESC Initialization
 */

import { useState, useEffect } from 'react';
import { getLatestTelemetry } from '../../services/cmgService';

const STATUS_STYLES = {
  idle:     { badge: 'bg-gray-100 text-gray-700',   label: 'Idle' },
  starting: { badge: 'bg-yellow-100 text-yellow-800', label: 'Starting' },
  running:  { badge: 'bg-green-100 text-green-800',  label: 'Running' },
  fault:    { badge: 'bg-red-100 text-red-800',      label: 'Fault' },
};

/**
 * @param {Object} props
 * @param {number} props.deviceId - Device ID to query on mount
 * @param {Object|null} props.latestMessage - Most recent cmg_telemetry WS message (or null)
 */
export default function CMGStatusPanel({ deviceId, latestMessage }) {
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial state on mount
  useEffect(() => {
    if (!deviceId) return;
    setLoading(true);
    getLatestTelemetry(deviceId)
      .then((data) => {
        setTelemetry(data);
        setError(null);
      })
      .catch(() => {
        setError('Could not load motor telemetry.');
      })
      .finally(() => setLoading(false));
  }, [deviceId]);

  // Merge live WebSocket updates
  useEffect(() => {
    if (latestMessage) {
      setTelemetry(latestMessage);
    }
  }, [latestMessage]);

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-sm text-gray-500">Loading motor status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 shadow-sm">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  const status = telemetry?.status ?? 'idle';
  const { badge, label } = STATUS_STYLES[status] ?? STATUS_STYLES.idle;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">CMG Motor</h3>
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badge}`}>
          {label}
        </span>
      </div>

      {telemetry ? (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500">Speed</p>
            <p className="text-3xl font-bold text-gray-900">
              {telemetry.rpm.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">RPM</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Current</p>
            <p className="text-3xl font-bold text-gray-900">
              {typeof telemetry.current_a === 'number'
                ? telemetry.current_a.toFixed(2)
                : '--'}
            </p>
            <p className="text-xs text-gray-500">A</p>
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-400">No telemetry available</p>
      )}

      {telemetry?.timestamp && (
        <p className="mt-3 text-xs text-gray-400">
          Updated {new Date(telemetry.timestamp).toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
