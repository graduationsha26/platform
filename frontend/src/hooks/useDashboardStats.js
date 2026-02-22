/**
 * useDashboardStats
 *
 * Feature 032: Dashboard Overview Page
 * Fetches dashboard summary statistics on mount and exposes loading/error state.
 */

import { useState, useEffect } from 'react';
import { fetchDashboardStats } from '../services/analyticsService';

/**
 * Hook that fetches dashboard stats once on mount.
 *
 * @returns {{ data: Object|null, loading: boolean, error: string|null }}
 *   - data: full response object (total_patients, active_devices, alerts_count, tremor_trend)
 *   - loading: true while the request is in flight
 *   - error: human-readable error message, or null on success
 */
export function useDashboardStats() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetchDashboardStats()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load dashboard data. Please refresh the page.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, error };
}
