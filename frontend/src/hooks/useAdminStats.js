import { useState, useEffect } from 'react';
import { fetchAdminStats } from '../services/analyticsService';

export function useAdminStats() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchAdminStats()
      .then((result) => { if (!cancelled) { setData(result); setError(null); } })
      .catch(() => { if (!cancelled) { setError('Failed to load admin stats.'); } })
      .finally(() => { if (!cancelled) { setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
