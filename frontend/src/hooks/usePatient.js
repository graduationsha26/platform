/**
 * usePatient Hook
 * Manages a single patient's profile and paginated session history.
 */

import { useState, useEffect, useCallback } from 'react';
import { getPatient, getSessions } from '../services/patientService';

const SESSION_PAGE_SIZE = 10;

export function usePatient(patientId) {
  const [patient, setPatient] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionCount, setSessionCount] = useState(0);
  const [sessionPage, setSessionPageRaw] = useState(1);
  const [sessionTotalPages, setSessionTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch patient profile on mount
  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;

    setLoading(true);
    setError(null);

    getPatient(patientId)
      .then((data) => {
        if (!cancelled) {
          setPatient(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Patient not found or access denied.');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [patientId]);

  // Fetch sessions when patientId or sessionPage changes
  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;

    setSessionsLoading(true);

    getSessions(patientId, { page: sessionPage, page_size: SESSION_PAGE_SIZE })
      .then((data) => {
        if (!cancelled) {
          setSessions(data.results);
          setSessionCount(data.count);
          setSessionTotalPages(Math.ceil(data.count / SESSION_PAGE_SIZE));
          setSessionsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSessions([]);
          setSessionsLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [patientId, sessionPage]);

  const setSessionPage = useCallback((page) => setSessionPageRaw(page), []);

  return {
    patient,
    sessions,
    sessionCount,
    sessionPage,
    sessionTotalPages,
    loading,
    sessionsLoading,
    error,
    setSessionPage,
  };
}
