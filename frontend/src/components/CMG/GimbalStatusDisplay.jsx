/**
 * GimbalStatusDisplay
 * Shows the live pitch/roll position and per-axis status of the gimbal.
 *
 * Fetches initial state via REST on mount, then merges live updates received
 * through the parent's WebSocket connection (latestMessage prop). All roles
 * (doctor and patient) can view this component.
 *
 * Feature 028: CMG Gimbal Servo Control
 */

import { useState, useEffect } from 'react';
import { getGimbalState } from '../../services/cmgService';

const STATUS_COLORS = {
  idle: 'bg-gray-100 text-gray-600',
  moving: 'bg-blue-100 text-blue-700',
  fault: 'bg-red-100 text-red-700',
};

function StatusBadge({ status }) {
  const colorClass = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-500';
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${colorClass}`}>
      {status ?? '—'}
    </span>
  );
}

/**
 * @param {Object}      props
 * @param {number}      props.deviceId      - Device primary key
 * @param {Object|null} props.latestMessage - Most recent WebSocket message object (or null)
 */
export default function GimbalStatusDisplay({ deviceId, latestMessage }) {
  const [state, setState] = useState(null);
  const [fetchError, setFetchError] = useState(false);

  // Initial REST fetch
  useEffect(() => {
    if (!deviceId) return;
    getGimbalState(deviceId)
      .then((s) => {
        setState(s);
        setFetchError(false);
      })
      .catch((err) => {
        // 404 = no state yet — not an error to surface as red
        if (err?.response?.status !== 404) {
          setFetchError(true);
        }
      });
  }, [deviceId]);

  // Merge incoming WebSocket servo_state messages
  useEffect(() => {
    if (!latestMessage || latestMessage.type !== 'servo_state') return;
    setState((prev) => ({
      ...prev,
      pitch_deg: latestMessage.pitch_deg,
      roll_deg: latestMessage.roll_deg,
      pitch_status: latestMessage.pitch_status,
      roll_status: latestMessage.roll_status,
      device_timestamp: latestMessage.device_timestamp,
    }));
    setFetchError(false);
  }, [latestMessage]);

  if (fetchError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-600">Failed to load gimbal state.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Gimbal State</h3>
        {!state && (
          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-400">
            No data yet
          </span>
        )}
      </div>

      {state ? (
        <div className="grid grid-cols-2 gap-4">
          {/* Pitch */}
          <div>
            <p className="mb-0.5 text-xs text-gray-400">Pitch</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900">
              {state.pitch_deg != null ? `${state.pitch_deg.toFixed(1)}°` : '—'}
            </p>
            <StatusBadge status={state.pitch_status} />
          </div>

          {/* Roll */}
          <div>
            <p className="mb-0.5 text-xs text-gray-400">Roll</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900">
              {state.roll_deg != null ? `${state.roll_deg.toFixed(1)}°` : '—'}
            </p>
            <StatusBadge status={state.roll_status} />
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span className="inline-block h-2 w-2 rounded-full bg-gray-300" />
          Disconnected — awaiting first servo state
        </div>
      )}

      {state?.device_timestamp && (
        <p className="mt-2 text-xs text-gray-400">
          Updated: {new Date(state.device_timestamp).toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
