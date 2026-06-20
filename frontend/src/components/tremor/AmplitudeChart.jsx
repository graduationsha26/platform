/**
 * AmplitudeChart
 * Rolling 60-second tremor amplitude line chart.
 * Receives pre-computed {ts, amplitude} data points from useTremorMonitor.
 *
 * Feature 034: Live Tremor Monitor — User Story 1
 */

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

const AmplitudeChart = ({ data, isStale }) => {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-neutral-50 rounded-lg border border-neutral-200">
        <p className="text-sm text-neutral-500">Waiting for sensor data…</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {isStale && (
        <div className="absolute inset-0 bg-neutral-100/60 rounded-lg flex items-center justify-center z-10">
          <span className="text-xs text-neutral-500 font-medium">(stale)</span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickCount={7}
            tickFormatter={(ms) => `${Math.round((ms - Date.now()) / 1000)}s`}
            tick={{ fontSize: 11 }}
            label={{ value: 'Time (s)', position: 'insideBottom', offset: -4, fontSize: 11 }}
          />
          <YAxis
            domain={[0, 'auto']}
            animationDuration={0}
            tick={{ fontSize: 11 }}
            label={{ value: 'm/s²', angle: -90, position: 'insideLeft', offset: 8, fontSize: 11 }}
            width={45}
          />
          <Tooltip
            formatter={(v) => [`${v.toFixed(4)} m/s²`, 'Amplitude']}
            labelFormatter={(ms) => `${Math.round((ms - Date.now()) / 1000)}s`}
            contentStyle={{ fontSize: 12 }}
          />
          <Line
            type="linear"
            dataKey="amplitude"
            stroke="#6366f1"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            animationDuration={0}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default AmplitudeChart;
