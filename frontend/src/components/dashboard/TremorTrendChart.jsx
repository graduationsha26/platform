/**
 * TremorTrendChart
 *
 * Feature 032: Dashboard Overview Page
 * Renders a Recharts LineChart showing 7-day daily average tremor amplitude.
 * Handles loading, error, and empty-data states.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

/**
 * Format a YYYY-MM-DD date string to "Mon D" (e.g. "Feb 14").
 * Parses parts directly to avoid UTC-offset issues.
 */
function formatDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * @param {Object}            props
 * @param {Array|null}        props.data    - Array of {date, avg_amplitude} (7 entries) or null
 * @param {boolean}           props.loading - Show skeleton while fetching
 * @param {boolean}           props.error   - Show error message if fetch failed
 */
export default function TremorTrendChart({ data, loading, error }) {
  if (loading) {
    return (
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6">
        <div className="h-48 flex items-center justify-center">
          <div className="h-6 w-48 rounded bg-neutral-300 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6">
        <div className="h-48 flex items-center justify-center">
          <p className="text-sm text-neutral-500">
            Unable to load trend data. Please refresh.
          </p>
        </div>
      </div>
    );
  }

  const allNull = !data || data.every((point) => point.avg_amplitude === null);

  if (allNull) {
    return (
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6">
        <div className="h-48 flex items-center justify-center">
          <p className="text-sm text-neutral-500">No tremor data available.</p>
        </div>
      </div>
    );
  }

  const chartData = data.map((point) => ({
    date: formatDate(point.date),
    avg_amplitude: point.avg_amplitude,
  }));

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#9ca3af' }}
            axisLine={{ stroke: '#e5e7eb' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => (v != null ? v.toFixed(2) : '')}
          />
          <Tooltip
            contentStyle={{ fontSize: '12px', padding: '6px 10px' }}
            formatter={(value) => [
              value != null ? value.toFixed(3) : '—',
              'Avg Amplitude',
            ]}
          />
          <Line
            type="monotone"
            dataKey="avg_amplitude"
            stroke="#2c5aa0"
            strokeWidth={2}
            dot={{ r: 4, fill: '#2c5aa0' }}
            activeDot={{ r: 6 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
