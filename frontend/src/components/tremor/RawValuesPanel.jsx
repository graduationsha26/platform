/**
 * RawValuesPanel
 * Displays live 6-axis IMU sensor readings from the glove.
 * Shows accelerometer (Acc X/Y/Z in m/s²) and gyroscope (Gyro X/Y/Z in °/s).
 *
 * Feature 034: Live Tremor Monitor — User Story 4
 */

const fmt = (v, decimals = 3) =>
  v == null ? '—' : Number(v).toFixed(decimals);

const AxisRow = ({ label, value, unit }) => (
  <div className="flex items-center justify-between py-1">
    <span className="text-xs font-medium text-neutral-600 w-14">{label}</span>
    <span className="text-xs font-mono text-neutral-900 tabular-nums">
      {fmt(value)} <span className="text-neutral-400">{unit}</span>
    </span>
  </div>
);

const RawValuesPanel = ({ rawValues, isStale }) => {
  const v = rawValues;

  return (
    <div>
      {isStale && v != null && (
        <p className="text-xs text-neutral-400 mb-1">(stale)</p>
      )}
      <div className="grid grid-cols-2 gap-x-6 gap-y-0">
        {/* Accelerometer */}
        <div>
          <p className="text-xs font-semibold text-neutral-500 mb-1 uppercase tracking-wide">Accelerometer</p>
          <AxisRow label="Acc X" value={v?.aX} unit="m/s²" />
          <AxisRow label="Acc Y" value={v?.aY} unit="m/s²" />
          <AxisRow label="Acc Z" value={v?.aZ} unit="m/s²" />
        </div>
        {/* Gyroscope */}
        <div>
          <p className="text-xs font-semibold text-neutral-500 mb-1 uppercase tracking-wide">Gyroscope</p>
          <AxisRow label="Gyro X" value={v?.gX} unit="°/s" />
          <AxisRow label="Gyro Y" value={v?.gY} unit="°/s" />
          <AxisRow label="Gyro Z" value={v?.gZ} unit="°/s" />
        </div>
      </div>
      {!v && (
        <p className="text-xs text-neutral-400 text-center mt-2">Waiting for sensor readings…</p>
      )}
    </div>
  );
};

export default RawValuesPanel;
