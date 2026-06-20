import { useState, useEffect } from 'react';
import { fetchPatientsOverview } from '../services/patientService';

export function usePatientsOverview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchPatientsOverview()
      .then((result) => { if (!cancelled) { setData(result); setError(null); } })
      .catch(() => { if (!cancelled) { setError('Failed to load patient overview.'); } })
      .finally(() => { if (!cancelled) { setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
