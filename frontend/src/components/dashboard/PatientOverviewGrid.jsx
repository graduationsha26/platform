import { usePatientsOverview } from '../../hooks/usePatientsOverview';
import PatientCard from './PatientCard';

export default function PatientOverviewGrid() {
  const { data, loading, error } = usePatientsOverview();

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className="bg-white border border-neutral-200 rounded-lg p-5 flex flex-col items-center gap-3 animate-pulse"
          >
            <div className="w-16 h-16 rounded-full bg-neutral-200" />
            <div className="h-4 w-32 rounded bg-neutral-200" />
            <div className="h-5 w-16 rounded-full bg-neutral-200" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
        {error}
      </p>
    );
  }

  if (!data || data.count === 0) {
    return (
      <p className="text-sm text-neutral-500 bg-neutral-50 border border-neutral-200 rounded-lg px-4 py-6 text-center">
        No patients assigned yet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.results.map((patient) => (
        <PatientCard key={patient.id} patient={patient} />
      ))}
    </div>
  );
}
