/**
 * GimbalControlPanel
 * Allows doctors to send set_position or home commands to the gimbal servos.
 *
 * Only rendered when user.role === 'doctor'. Input bounds are driven by the
 * calibration prop so that the form rejects out-of-range values before submit.
 *
 * Feature 028: CMG Gimbal Servo Control
 */

import { useState } from 'react';
import { sendServoCommand } from '../../services/cmgService';

/**
 * @param {Object}  props
 * @param {number}  props.deviceId    - Device primary key
 * @param {Object}  props.calibration - GimbalCalibration record (or system defaults)
 * @param {Object}  props.user        - Authenticated user object ({ role, ... })
 */
export default function GimbalControlPanel({ deviceId, calibration, user }) {
  const [pitch, setPitch] = useState('');
  const [roll, setRoll] = useState('');
  const [loadingSet, setLoadingSet] = useState(false);
  const [loadingHome, setLoadingHome] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (user?.role !== 'doctor') return null;

  const cal = calibration ?? {
    pitch_min_deg: -30,
    pitch_max_deg: 30,
    roll_min_deg: -20,
    roll_max_deg: 20,
  };

  const clearFeedback = () => {
    setError(null);
    setSuccess(null);
  };

  const handleSetPosition = async () => {
    clearFeedback();
    if (pitch === '' && roll === '') {
      setError('Enter at least one angle before sending a set_position command.');
      return;
    }
    const angles = {};
    if (pitch !== '') angles.pitch_deg = parseFloat(pitch);
    if (roll !== '') angles.roll_deg = parseFloat(roll);

    setLoadingSet(true);
    try {
      await sendServoCommand(deviceId, 'set_position', angles);
      setSuccess('Position command sent.');
      setPitch('');
      setRoll('');
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Command failed. Please try again.');
    } finally {
      setLoadingSet(false);
    }
  };

  const handleHome = async () => {
    clearFeedback();
    setLoadingHome(true);
    try {
      await sendServoCommand(deviceId, 'home');
      setSuccess('Home command sent.');
    } catch (err) {
      setError(err?.response?.data?.error ?? 'Command failed. Please try again.');
    } finally {
      setLoadingHome(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Gimbal Position Control</h3>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-500">
            Pitch (°) <span className="text-gray-400">[{cal.pitch_min_deg}, {cal.pitch_max_deg}]</span>
          </label>
          <input
            type="number"
            step="0.1"
            min={cal.pitch_min_deg}
            max={cal.pitch_max_deg}
            value={pitch}
            onChange={(e) => setPitch(e.target.value)}
            placeholder="—"
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">
            Roll (°) <span className="text-gray-400">[{cal.roll_min_deg}, {cal.roll_max_deg}]</span>
          </label>
          <input
            type="number"
            step="0.1"
            min={cal.roll_min_deg}
            max={cal.roll_max_deg}
            value={roll}
            onChange={(e) => setRoll(e.target.value)}
            placeholder="—"
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSetPosition}
          disabled={loadingSet || loadingHome}
          className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loadingSet ? 'Sending…' : 'Set Position'}
        </button>
        <button
          onClick={handleHome}
          disabled={loadingSet || loadingHome}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loadingHome ? 'Sending…' : 'Home'}
        </button>
      </div>

      {error && (
        <p className="mt-2 text-xs text-red-600">{error}</p>
      )}
      {success && (
        <p className="mt-2 text-xs text-green-600">{success}</p>
      )}
    </div>
  );
}
