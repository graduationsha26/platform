/**
 * SuppressionModeControl
 * Allows doctors to enable or disable tremor suppression for a device.
 *
 * Only rendered when user.role === 'doctor'. Shows current active/inactive status.
 * Live status updates arrive via WebSocket pid_status messages.
 *
 * Feature 029: CMG PID Controller Tuning
 */

import { useState, useEffect } from 'react';
import { getSuppressionMode, startSuppression, stopSuppression } from '../../services/cmgService';

const STATUS_STYLES = {
  active:      'bg-green-100 text-green-800',
  inactive:    'bg-gray-100 text-gray-600',
  interrupted: 'bg-amber-100 text-amber-800',
};

/**
 * @param {Object}        props
 * @param {number}        props.deviceId      - Device primary key
 * @param {Object}        props.user          - Authenticated user object ({ role, ... })
 * @param {Object|null}   props.latestMessage - Most recent WebSocket message (or null)
 */
export default function SuppressionModeControl({ deviceId, user, latestMessage }) {
  const [isActive, setIsActive] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [statusLabel, setStatusLabel] = useState('inactive');
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [error, setError] = useState(null);

  const fetchMode = () => {
    if (!deviceId) return;
    getSuppressionMode(deviceId)
      .then((data) => {
        setIsActive(data.is_active);
        setSessionId(data.session_id);
        setStatusLabel(data.is_active ? 'active' : 'inactive');
      })
      .catch(() => {
        // leave current state on fetch failure
      });
  };

  useEffect(() => {
    fetchMode();
  }, [deviceId]);

  // Merge live WebSocket pid_status updates
  useEffect(() => {
    if (!latestMessage) return;
    if (latestMessage.type === 'pid_status') {
      const mode = latestMessage.mode;
      if (mode === 'enabled') {
        setIsActive(true);
        setStatusLabel('active');
      } else if (mode === 'disabled') {
        setIsActive(false);
        setStatusLabel('inactive');
        setSessionId(null);
      } else if (mode === 'fault' || mode === 'interrupted') {
        setIsActive(false);
        setStatusLabel('interrupted');
        setSessionId(null);
      }
    }
  }, [latestMessage]);

  if (user?.role !== 'doctor') return null;

  const handleEnable = async () => {
    setError(null);
    setEnabling(true);
    try {
      const session = await startSuppression(deviceId);
      setIsActive(true);
      setSessionId(session.id);
      setStatusLabel('active');
    } catch (err) {
      const data = err?.response?.data;
      setError(data?.error ?? 'Failed to enable suppression. Please try again.');
    } finally {
      setEnabling(false);
    }
  };

  const handleDisable = async () => {
    if (!sessionId) return;
    setError(null);
    setDisabling(true);
    try {
      await stopSuppression(sessionId);
      setIsActive(false);
      setSessionId(null);
      setStatusLabel('inactive');
    } catch (err) {
      const data = err?.response?.data;
      setError(data?.error ?? 'Failed to disable suppression. Please try again.');
    } finally {
      setDisabling(false);
    }
  };

  const labelText = {
    active:      'Active',
    inactive:    'Inactive',
    interrupted: 'Interrupted',
  }[statusLabel] ?? 'Unknown';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Suppression Mode</h3>

      <div className="mb-3 flex items-center gap-2">
        <span className="text-xs text-gray-500">Status:</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[statusLabel] ?? STATUS_STYLES.inactive}`}>
          {labelText}
        </span>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleEnable}
          disabled={isActive || enabling || disabling}
          className="flex-1 rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enabling ? 'Enabling…' : 'Enable Suppression'}
        </button>
        <button
          onClick={handleDisable}
          disabled={!isActive || disabling || enabling}
          className="flex-1 rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabling ? 'Disabling…' : 'Disable Suppression'}
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
