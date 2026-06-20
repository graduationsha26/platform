/**
 * DateRangePicker
 * Two native date inputs (Start / End) with inline validation.
 * Prevents future date selection via the `max` attribute.
 *
 * Feature 035: Reports Page & PDF Download — User Story 1
 */

const DateRangePicker = ({ startDate, endDate, onChange, onApply, loading }) => {
  const today = new Date().toISOString().split('T')[0];
  const validationError =
    endDate && startDate && endDate < startDate
      ? 'End date must be on or after start date.'
      : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        {/* Start date */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            Start date
          </label>
          <input
            type="date"
            value={startDate}
            max={today}
            onChange={(e) => onChange(e.target.value, endDate)}
            className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
              validationError ? 'border-red-400' : 'border-neutral-300'
            }`}
          />
        </div>

        {/* End date */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            End date
          </label>
          <input
            type="date"
            value={endDate}
            max={today}
            onChange={(e) => onChange(startDate, e.target.value)}
            className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 ${
              validationError ? 'border-red-400' : 'border-neutral-300'
            }`}
          />
        </div>

        {/* Apply button */}
        <button
          onClick={onApply}
          disabled={!!validationError || loading}
          className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Loading…' : 'Apply'}
        </button>
      </div>

      {/* Inline validation error */}
      {validationError && (
        <p className="text-xs text-red-600">{validationError}</p>
      )}
    </div>
  );
};

export default DateRangePicker;
