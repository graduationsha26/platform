import { useState } from 'react';
import { Link } from 'react-router-dom';

function getInitials(fullName) {
  const words = (fullName || '').trim().split(/\s+/);
  return words
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || '')
    .join('');
}

/**
 * @param {{ patient: { id: number, full_name: string, avatar_url: string, device_online: boolean } }} props
 */
export default function PatientCard({ patient }) {
  const [imgError, setImgError] = useState(false);
  const showInitials = !patient.avatar_url || imgError;
  const initials = getInitials(patient.full_name);

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-5 flex flex-col items-center gap-3 hover:shadow-md transition-shadow duration-200">
      {showInitials ? (
        <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
          <span className="text-xl font-semibold text-primary-700">{initials}</span>
        </div>
      ) : (
        <img
          src={patient.avatar_url}
          alt={patient.full_name}
          className="w-16 h-16 rounded-full object-cover flex-shrink-0"
          onError={() => setImgError(true)}
        />
      )}

      <p className="text-base font-semibold text-neutral-900 text-center leading-tight">
        {patient.full_name}
      </p>

      {patient.device_online ? (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
          Online
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">
          <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 inline-block" />
          Offline
        </span>
      )}

      <div className="flex gap-2 w-full mt-1">
        <Link
          to={`/doctor/patients/${patient.id}`}
          className="flex-1 text-center text-xs font-medium px-3 py-1.5 rounded border border-neutral-300 text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          View Profile
        </Link>
        <Link
          to={`/doctor/patients/${patient.id}/monitor`}
          className="flex-1 text-center text-xs font-medium px-3 py-1.5 rounded border border-primary-300 text-primary-700 hover:bg-primary-50 transition-colors"
        >
          Live Monitor
        </Link>
      </div>
    </div>
  );
}
