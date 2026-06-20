/**
 * PIDGainPanel
 * Allows doctors to read and update per-device PID gain configuration.
 *
 * Only rendered when user.role === 'doctor'. Pre-populated from the current
 * PID config record (or system defaults) on mount. Inline validation prevents
 * gains from exceeding per-axis safety bounds before submit.
 *
 * Feature 029: CMG PID Controller Tuning
 */

import { useState, useEffect } from 'react';
import { getPIDConfig, setPIDConfig } from '../../services/cmgService';

// Per-axis maximum bounds — mirror env var values (PID_K*_*_MAX)
const BOUNDS = {
  kp_pitch: { min: 0, max: 0.20 },
  ki_pitch: { min: 0, max: 0.020 },
  kd_pitch: { min: 0, max: 0.050 },
  kp_roll:  { min: 0, max: 0.15 },
  ki_roll:  { min: 0, max: 0.015 },
  kd_roll:  { min: 0, max: 0.040 },
};

const DEFAULT_FORM = {
  kp_pitch: '0.08',
  ki_pitch: '0.002',
  kd_pitch: '0.012',
  kp_roll:  '0.06',
  ki_roll:  '0.001',
  kd_roll:  '0.008',
};

/**
 * @param {Object}  props
 * @param {number}  props.deviceId - Device primary key
 * @param {Object}  props.user     - Authenticated user object ({ role, ... })
 */
export default function PIDGainPanel({ deviceId, user }) {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!deviceId) return;
    setLoading(true);
    getPIDConfig(deviceId)
      .then((cfg) => {
        setForm({
          kp_pitch: String(cfg.kp_pitch ?? 0.08),
          ki_pitch: String(cfg.ki_pitch ?? 0.002),
          kd_pitch: String(cfg.kd_pitch ?? 0.012),
          kp_roll:  String(cfg.kp_roll  ?? 0.06),
          ki_roll:  String(cfg.ki_roll  ?? 0.001),
          kd_roll:  String(cfg.kd_roll  ?? 0.008),
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
    Object.keys(BOUNDS).forEach((field) => {
      const val = parseFloat(form[field]);
      if (isNaN(val)) {
        errs[field] = `${field} must be a number.`;
      } else if (val < BOUNDS[field].min) {
        errs[field] = `${field} must be ≥ ${BOUNDS[field].min}.`;
      } else if (val > BOUNDS[field].max) {
        errs[field] = `${field} exceeds maximum of ${BOUNDS[field].max}.`;
      }
    });
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
      await setPIDConfig(deviceId, {
        kp_pitch: parseFloat(form.kp_pitch),
        ki_pitch: parseFloat(form.ki_pitch),
        kd_pitch: parseFloat(form.kd_pitch),
        kp_roll:  parseFloat(form.kp_roll),
        ki_roll:  parseFloat(form.ki_roll),
        kd_roll:  parseFloat(form.kd_roll),
      });
      setSuccess('PID gains saved and pushed to device.');
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
        <p className="text-sm text-gray-400">Loading PID configuration…</p>
      </div>
    );
  }

  const Field = ({ label, field }) => (
    <div>
      <label className="mb-1 block text-xs text-gray-500">{label}</label>
      <input
        type="number"
        step="0.001"
        value={form[field]}
        onChange={handleChange(field)}
        className={`w-full rounded border px-2 py-1 text-sm focus:outline-none ${
          fieldErrors[field]
            ? 'border-red-400 focus:border-red-500'
            : 'border-gray-300 focus:border-blue-500'
        }`}
      />
      {fieldErrors[field] && (
        <p className="mt-0.5 text-xs text-red-600">{fieldErrors[field]}</p>
      )}
    </div>
  );

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">PID Gain Configuration</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <p className="mb-1 text-xs font-medium text-gray-500 uppercase tracking-wide">Pitch Axis</p>
          <div className="grid grid-cols-3 gap-2">
            <Field label="Kp (max 0.20)" field="kp_pitch" />
            <Field label="Ki (max 0.020)" field="ki_pitch" />
            <Field label="Kd (max 0.050)" field="kd_pitch" />
          </div>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-gray-500 uppercase tracking-wide">Roll Axis</p>
          <div className="grid grid-cols-3 gap-2">
            <Field label="Kp (max 0.15)" field="kp_roll" />
            <Field label="Ki (max 0.015)" field="ki_roll" />
            <Field label="Kd (max 0.040)" field="kd_roll" />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save PID Gains'}
        </button>

        {error && <p className="text-xs text-red-600">{error}</p>}
        {success && <p className="text-xs text-green-600">{success}</p>}
      </form>
    </div>
  );
}
