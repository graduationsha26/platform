/**
 * StatsPreview
 * Displays four aggregated tremor metric cards for the selected date range:
 * Avg Amplitude, Max Amplitude, Dominant Frequency, Tremor Reduction %.
 *
 * Handles three states: loading (skeletons), empty (no data message), data.
 *
 * Feature 035: Reports Page & PDF Download — User Story 1
 */

const MetricCard = ({ label, children }) => (
  <div className="bg-white border border-neutral-200 rounded-xl p-4">
    <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">{label}</p>
    <div className="text-xl font-semibold text-neutral-900">{children}</div>
  </div>
);

const SkeletonCard = () => (
  <div className="h-24 bg-neutral-100 rounded-xl animate-pulse" />
);

const TremorReductionValue = ({ value }) => {
  if (value == null) {
    return <span className="text-neutral-400 text-base font-medium">— Unavailable</span>;
  }
  if (value >= 0) {
    return <span className="text-green-700">+{value.toFixed(1)}%</span>;
  }
  return <span className="text-red-700">{value.toFixed(1)}%</span>;
};

const StatsPreview = ({ stats, loading, error }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-red-600 py-4">{error}</p>
    );
  }

  if (!stats?.hasData) {
    return (
      <p className="text-sm text-neutral-500 text-center py-8">
        No sessions recorded for this period. Try adjusting the date range.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      <MetricCard label="Avg Amplitude">
        {stats.avgAmplitude.toFixed(3)}
      </MetricCard>
      <MetricCard label="Max Amplitude">
        {stats.maxAmplitude.toFixed(3)}
      </MetricCard>
      <MetricCard label="Dominant Frequency">
        {stats.dominantFrequency.toFixed(1)} Hz
      </MetricCard>
      <MetricCard label="Tremor Reduction">
        <TremorReductionValue value={stats.tremorReductionPct} />
      </MetricCard>
    </div>
  );
};

export default StatsPreview;
