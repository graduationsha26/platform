/**
 * useCriticalAlerts
 *
 * Feature 044: Smart Medical Alerts
 * Fetches the count of patients with severe tremors on 5 consecutive days,
 * exposing loading/error state for the Critical Alerts metric card.
 */

import { useState, useEffect } from 'react';
import { fetchCriticalAlerts } from '../services/analyticsService';

/**
 * Hook that fetches critical alerts count once on mount.
 *
 * @returns {{ data: { count: number }|null, loading: boolean, error: string|null }}
 */
export function useCriticalAlerts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetchCriticalAlerts()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load critical alerts.');
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
