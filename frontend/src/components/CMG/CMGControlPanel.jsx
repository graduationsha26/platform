/**
 * CMGControlPanel
 * Allows doctors to send start / stop / emergency_stop commands to the glove motor.
 *
 * Only rendered when user.role === 'doctor'. Button states are driven by the
 * current motor status prop so that invalid transitions are disabled.
 *
 * Feature 027: CMG Brushless Motor & ESC Initialization
 */

import { useState } from 'react';
import { sendCommand } from '../../services/cmgService';

const COMMANDS = [
  { command: 'start',          label: 'Start',         disableWhen: ['running', 'starting'] },
  { command: 'stop',           label: 'Stop',          disableWhen: ['idle'] },
  { command: 'emergency_stop', label: 'Emergency Stop', disableWhen: [] },
];

/**
 * @param {Object} props
 * @param {number} props.deviceId
 * @param {string} props.motorStatus - Current motor status: 'idle'|'starting'|'running'|'fault'
 * @param {Object} props.user - Authenticated user object ({ role, ... })
 */
export default function CMGControlPanel({ deviceId, motorStatus, user }) {
  const [loading, setLoading] = useState({});
  const [lastError, setLastError] = useState(null);

  if (user?.role !== 'doctor') return null;

  const handleCommand = async (command) => {
    setLoading((prev) => ({ ...prev, [command]: true }));
    setLastError(null);
    try {
      await sendCommand(deviceId, command);
    } catch (err) {
      const message = err?.response?.data?.error ?? 'Command failed. Please try again.';
      setLastError(message);
    } finally {
      setLoading((prev) => ({ ...prev, [command]: false }));
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Motor Control</h3>

      <div className="flex flex-wrap gap-2">
        {COMMANDS.map(({ command, label, disableWhen }) => {
          const isEmergency = command === 'emergency_stop';
          const isDisabled = loading[command] || disableWhen.includes(motorStatus);

          return (
            <button
              key={command}
              onClick={() => handleCommand(command)}
              disabled={isDisabled}
              className={[
                'rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50',
                isEmergency
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-gray-800 text-white hover:bg-gray-900',
              ].join(' ')}
            >
              {loading[command] ? `${label}…` : label}
            </button>
          );
        })}
      </div>

      {lastError && (
        <p className="mt-2 text-xs text-red-600">{lastError}</p>
      )}
    </div>
  );
}
