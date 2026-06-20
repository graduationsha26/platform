/**
 * SuppressionEffectivenessChart
 * Displays per-session aggregate (avg raw amplitude, avg residual amplitude,
 * % reduction with 60% target indicator) and a live time-series chart of
 * raw vs residual tremor amplitude during suppression.
 *
 * Live metrics arrive via WebSocket suppression_metric messages.
 * Historical session data is loaded via getSessionMetrics() on session selection.
 *
 * Both doctors and patients can view this component.
 *
 * Feature 029: CMG PID Controller Tuning
 */

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { listSessions, getSessionMetrics } from '../../services/cmgService';

/**
 * @param {Object}      props
 * @param {number}      props.deviceId      - Device primary key
 * @param {Object|null} props.latestMessage - Most recent WebSocket message (or null)
 */
export default function SuppressionEffectivenessChart({ deviceId, latestMessage }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [aggregate, setAggregate] = useState(null);
  const [liveMetrics, setLiveMetrics] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Load session list on mount
  useEffect(() => {
    if (!deviceId) return;
    listSessions(deviceId, { limit: 20 })
      .then((data) => {
        const results = data.results ?? [];
        setSessions(results);
        // Auto-select most recent session
        if (results.length > 0) {
          const first = results[0];
          setActiveSessionId(first.id);
          setAggregate({
            avg_raw_amplitude_deg: first.avg_raw_amplitude_deg,
            avg_residual_amplitude_deg: first.avg_residual_amplitude_deg,
            reduction_pct: first.reduction_pct,
          });
        }
      })
      .catch(() => {
        // Fail silently — no sessions available
      });
  }, [deviceId]);

  // Load historical metrics when session selection changes
  useEffect(() => {
    if (!activeSessionId) return;
    setLoadingHistory(true);
    setLiveMetrics([]);
    getSessionMetrics(activeSessionId, { limit: 300 })
      .then((data) => {
        setAggregate(data.aggregate);
        setLiveMetrics(
          (data.metrics ?? []).map((m) => ({
            time: m.device_timestamp,
            raw: m.raw_amplitude_deg,
            residual: m.residual_amplitude_deg,
          }))
        );
      })
      .catch(() => {
        // Fail silently
      })
      .finally(() => setLoadingHistory(false));
  }, [activeSessionId]);

  // Append live WebSocket suppression_metric messages
  useEffect(() => {
    if (!latestMessage) return;
    if (latestMessage.type === 'suppression_metric') {
      if (latestMessage.session_id !== activeSessionId) return;
      setLiveMetrics((prev) => {
        const next = [
          ...prev,
          {
            time: latestMessage.timestamp,
            raw: latestMessage.raw_amplitude_deg,
            residual: latestMessage.residual_amplitude_deg,
          },
        ];
        // Cap at last 300 data points
        return next.length > 300 ? next.slice(next.length - 300) : next;
      });
    }
  }, [latestMessage, activeSessionId]);

  const reductionPct = aggregate?.reduction_pct ?? null;
  const avgRaw = aggregate?.avg_raw_amplitude_deg ?? null;
  const avgResidual = aggregate?.avg_residual_amplitude_deg ?? null;
  // Target residual = 40% of avg raw (≥60% reduction means residual ≤40%)
  const targetResidual = avgRaw != null ? avgRaw * 0.40 : null;

  const meetsTarget = reductionPct != null && reductionPct >= 60;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Suppression Effectiveness</h3>

      {/* Session selector */}
      {sessions.length > 0 && (
        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-500">Session</label>
          <select
            className="w-full rounded border border-gray-300 px-2 py-1 text-xs focus:outline-none focus:border-blue-500"
            value={activeSessionId ?? ''}
            onChange={(e) => setActiveSessionId(Number(e.target.value))}
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {new Date(s.started_at).toLocaleString()} — {s.status}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Aggregate summary */}
      {aggregate && (
        <div className="mb-3 grid grid-cols-3 gap-2 rounded bg-gray-50 p-2">
          <div className="text-center">
            <p className="text-xs text-gray-400">Avg Raw</p>
            <p className="text-sm font-semibold text-gray-700">
              {avgRaw != null ? `${avgRaw.toFixed(2)}°` : '—'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400">Avg Residual</p>
            <p className="text-sm font-semibold text-gray-700">
              {avgResidual != null ? `${avgResidual.toFixed(2)}°` : '—'}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400">Reduction</p>
            <p className={`text-sm font-semibold ${reductionPct != null ? (meetsTarget ? 'text-green-600' : 'text-amber-600') : 'text-gray-400'}`}>
              {reductionPct != null ? `${reductionPct}%` : '—'}
            </p>
          </div>
        </div>
      )}

      {/* Target indicator badge */}
      {reductionPct != null && (
        <div className="mb-3">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meetsTarget ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
            {meetsTarget ? 'Meets 60% target' : 'Below 60% target'}
          </span>
        </div>
      )}

      {/* Time-series chart */}
      {loadingHistory ? (
        <p className="text-xs text-gray-400">Loading metrics…</p>
      ) : liveMetrics.length === 0 ? (
        <p className="text-xs text-gray-400">No metrics available for this session yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={liveMetrics} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="time"
              tick={false}
              tickLine={false}
              axisLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ fontSize: '11px', padding: '4px 8px' }}
              labelFormatter={() => ''}
              formatter={(value, name) => [
                `${Number(value).toFixed(3)}°`,
                name === 'raw' ? 'Raw amplitude' : 'Residual amplitude',
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px' }}
              formatter={(value) =>
                value === 'raw' ? 'Raw amplitude' : 'Residual amplitude'
              }
            />
            <Line
              type="monotone"
              dataKey="raw"
              stroke="#9ca3af"
              strokeDasharray="4 2"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="residual"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            {targetResidual != null && (
              <ReferenceLine
                y={targetResidual}
                stroke="#22c55e"
                strokeDasharray="6 3"
                label={{ value: '60% target', fill: '#22c55e', fontSize: 10 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
