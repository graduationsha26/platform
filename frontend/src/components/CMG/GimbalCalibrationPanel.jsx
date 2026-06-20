/**
 * GimbalCalibrationPanel
 * Allows doctors to read and update per-device gimbal servo calibration.
 *
 * Only rendered when user.role === 'doctor'. Pre-populated from the current
 * calibration record on mount. Inline validation prevents min >= max before submit.
 *
 * Feature 028: CMG Gimbal Servo Control
 */

import { useState, useEffect } from 'react';
import { getGimbalCalibration, setGimbalCalibration } from '../../services/cmgService';

const DEFAULT_FORM = {
  pitch_center_deg: '0',
  roll_center_deg: '0',
  pitch_min_deg: '-30',
  pitch_max_deg: '30',
  roll_min_deg: '-20',
  roll_max_deg: '20',
  rate_limit_deg_per_sec: '45',
};

/**
 * @param {Object}  props
 * @param {number}  props.deviceId - Device primary key
 * @param {Object}  props.user     - Authenticated user object ({ role, ... })
 */
export default function GimbalCalibrationPanel({ deviceId, user }) {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!deviceId) return;
    setLoading(true);
    getGimbalCalibration(deviceId)
      .then((cal) => {
        setForm({
          pitch_center_deg: String(cal.pitch_center_deg ?? 0),
          roll_center_deg: String(cal.roll_center_deg ?? 0),
          pitch_min_deg: String(cal.pitch_min_deg ?? -30),
          pitch_max_deg: String(cal.pitch_max_deg ?? 30),
          roll_min_deg: String(cal.roll_min_deg ?? -20),
          roll_max_deg: String(cal.roll_max_deg ?? 20),
          rate_limit_deg_per_sec: String(cal.rate_limit_deg_per_sec ?? 45),
        });
      })
      .catch(() => {
        // leave defaults if fetch fails
      })
      .finally(() => setLoading(false));
  }, [deviceId]);

  if (user?.role !== 'doctor') return null;

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    setError(null);
    setSuccess(null);
  };

  const validate = () => {
    const errs = {};
    const f = form;
    const pitchMin = parseFloat(f.pitch_min_deg);
    const pitchMax = parseFloat(f.pitch_max_deg);
    const rollMin = parseFloat(f.roll_min_deg);
    const rollMax = parseFloat(f.roll_max_deg);

    if (!isNaN(pitchMin) && !isNaN(pitchMax) && pitchMin >= pitchMax) {
      errs.pitch_min_deg = `pitch_min_deg (${pitchMin}) must be strictly less than pitch_max_deg (${pitchMax}).`;
    }
    if (!isNaN(rollMin) && !isNaN(rollMax) && rollMin >= rollMax) {
      errs.roll_min_deg = `roll_min_deg (${rollMin}) must be strictly less than roll_max_deg (${rollMax}).`;
    }
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }

    setSaving(true);
    try {
      await setGimbalCalibration(deviceId, {
        pitch_center_deg: parseFloat(form.pitch_center_deg),
        roll_center_deg: parseFloat(form.roll_center_deg),
        pitch_min_deg: parseFloat(form.pitch_min_deg),
        pitch_max_deg: parseFloat(form.pitch_max_deg),
        roll_min_deg: parseFloat(form.roll_min_deg),
        roll_max_deg: parseFloat(form.roll_max_deg),
        rate_limit_deg_per_sec: parseFloat(form.rate_limit_deg_per_sec),
      });
      setSuccess('Calibration saved and pushed to device.');
      setFieldErrors({});
    } catch (err) {
      const data = err?.response?.data;
      if (data && typeof data === 'object' && !data.error) {
        // DRF field-level validation errors
        const fe = {};
        Object.entries(data).forEach(([k, v]) => {
          fe[k] = Array.isArray(v) ? v[0] : v;
        });
        setFieldErrors(fe);
      } else {
        setError(data?.error ?? 'Save failed. Please try again.');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-sm text-gray-400">Loading calibration…</p>
      </div>
    );
  }

  const Field = ({ label, field, step = '0.1' }) => (
    <div>
      <label className="mb-1 block text-xs text-gray-500">{label}</label>
      <input
        type="number"
        step={step}
        value={form[field]}
        onChange={handleChange(field)}
        className={`w-full rounded border px-2 py-1 text-sm focus:outline-none ${
          fieldErrors[field] ? 'border-red-400 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
        }`}
      />
      {fieldErrors[field] && (
        <p className="mt-0.5 text-xs text-red-600">{fieldErrors[field]}</p>
      )}
    </div>
  );

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Gimbal Calibration</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Pitch Center (°)" field="pitch_center_deg" />
          <Field label="Roll Center (°)" field="roll_center_deg" />
          <Field label="Pitch Min (°)" field="pitch_min_deg" />
          <Field label="Pitch Max (°)" field="pitch_max_deg" />
          <Field label="Roll Min (°)" field="roll_min_deg" />
          <Field label="Roll Max (°)" field="roll_max_deg" />
        </div>
        <Field label="Rate Limit (deg/s)" field="rate_limit_deg_per_sec" step="1" />

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Calibration'}
        </button>

        {error && <p className="text-xs text-red-600">{error}</p>}
        {success && <p className="text-xs text-green-600">{success}</p>}
      </form>
    </div>
  );
}
