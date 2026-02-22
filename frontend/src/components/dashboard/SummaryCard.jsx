/**
 * SummaryCard
 *
 * Feature 032: Dashboard Overview Page
 * Displays a single labeled summary metric with loading and error states.
 */

const VARIANT_CLASSES = {
  primary: {
    container: 'bg-primary-50 border-primary-200 hover:shadow-primary',
    title: 'text-primary-900',
    value: 'text-primary-600',
    subtitle: 'text-primary-700',
  },
  success: {
    container: 'bg-success-50 border-success-200 hover:shadow-success',
    title: 'text-success-900',
    value: 'text-success-600',
    subtitle: 'text-success-700',
  },
  warning: {
    container: 'bg-amber-50 border-amber-200 hover:shadow-sm',
    title: 'text-amber-900',
    value: 'text-amber-600',
    subtitle: 'text-amber-700',
  },
  secondary: {
    container: 'bg-secondary-50 border-secondary-200 hover:shadow-secondary',
    title: 'text-secondary-900',
    value: 'text-secondary-600',
    subtitle: 'text-secondary-700',
  },
};

/**
 * @param {Object}          props
 * @param {string}          props.label    - Card title label
 * @param {string}          props.subtitle - Descriptive line beneath the value
 * @param {number|null}     props.value    - Numeric value to display
 * @param {boolean}         props.loading  - Show skeleton placeholder when true
 * @param {boolean}         props.error    - Show error dash when true
 * @param {'primary'|'success'|'warning'|'secondary'} [props.variant='primary']
 */
export default function SummaryCard({
  label,
  subtitle,
  value,
  loading = false,
  error = false,
  variant = 'primary',
}) {
  const classes = VARIANT_CLASSES[variant] ?? VARIANT_CLASSES.primary;

  return (
    <div
      className={`border rounded-lg p-6 transition-shadow duration-200 ${classes.container}`}
    >
      <h3 className={`text-lg font-semibold mb-2 ${classes.title}`}>
        {label}
      </h3>

      {loading ? (
        <div className="h-9 w-16 rounded bg-current opacity-20 animate-pulse mb-2" />
      ) : error ? (
        <p className={`text-3xl font-bold ${classes.value}`}>—</p>
      ) : (
        <p className={`text-3xl font-bold ${classes.value}`}>
          {value ?? 0}
        </p>
      )}

      <p className={`text-sm mt-2 ${classes.subtitle}`}>{subtitle}</p>
    </div>
  );
}
