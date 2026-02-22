/**
 * SeverityIndicator
 * Color-coded severity badge for the live tremor monitor.
 * Reflects the ML model's current tremor classification.
 *
 * Feature 034: Live Tremor Monitor — User Story 3
 */

const SEVERITY_CONFIG = {
  mild: {
    badge: 'bg-green-100 border-green-300 text-green-800',
    dot: 'bg-green-500',
    label: 'Mild',
  },
  moderate: {
    badge: 'bg-amber-100 border-amber-300 text-amber-800',
    dot: 'bg-amber-500',
    label: 'Moderate',
  },
  severe: {
    badge: 'bg-red-100 border-red-300 text-red-800',
    dot: 'bg-red-500',
    label: 'Severe',
  },
};

const SeverityIndicator = ({ severity, isStale }) => {
  const { level, confidence } = severity ?? {};
  const cfg = level ? SEVERITY_CONFIG[level] : null;

  if (!cfg) {
    return (
      <div className="flex items-center gap-3">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border bg-neutral-100 border-neutral-300">
          <span className="w-3 h-3 rounded-full bg-neutral-400" />
          <span className="text-sm font-semibold text-neutral-600">No Data</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-3">
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${cfg.badge}`}>
          <span className={`w-3 h-3 rounded-full ${cfg.dot}`} />
          <span className="text-sm font-semibold">{cfg.label}</span>
        </div>
        {isStale && (
          <span className="text-xs text-neutral-400">(stale)</span>
        )}
      </div>
      {confidence != null && (
        <p className="text-xs text-neutral-500 ml-1">
          Confidence: {Math.round(confidence * 100)}%
        </p>
      )}
    </div>
  );
};

export default SeverityIndicator;
