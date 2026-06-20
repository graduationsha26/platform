/**
 * SpectrumChart
 * FFT frequency spectrum bar chart for the live tremor monitor.
 * Shows the power distribution of the dominant tremor axis across
 * the 3–8 Hz Parkinsonian tremor band.
 *
 * Feature 034: Live Tremor Monitor — User Story 2
 */

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

const SpectrumChart = ({ data, isStale }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 bg-neutral-50 rounded-lg border border-neutral-200">
        <p className="text-sm text-neutral-500">Waiting for FFT data…</p>
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
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="freq"
            tick={{ fontSize: 11 }}
            label={{ value: 'Frequency (Hz)', position: 'insideBottom', offset: -8, fontSize: 11 }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{ value: 'Amplitude', angle: -90, position: 'insideLeft', offset: 8, fontSize: 11 }}
            width={50}
          />
          <Tooltip
            formatter={(v) => [`${v.toFixed(5)}`, 'Amplitude']}
            labelFormatter={(f) => `${f} Hz`}
            contentStyle={{ fontSize: 12 }}
          />
          {/* Highlight typical Parkinson tremor range 4–6 Hz */}
          <ReferenceLine x={4} stroke="#f59e0b" strokeDasharray="3 3" />
          <ReferenceLine x={6} stroke="#f59e0b" strokeDasharray="3 3" />
          <Bar
            dataKey="amplitude"
            fill="#a78bfa"
            isAnimationActive={false}
            animationDuration={0}
          />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-neutral-400 text-center mt-1">
        Dashed lines mark the 4–6 Hz Parkinsonian tremor range
      </p>
    </div>
  );
};

export default SpectrumChart;
