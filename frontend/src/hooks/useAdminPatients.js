/**
 * useAdminPatients Hook
 *
 * Feature 048: Patient Distribution (Admin)
 * Manages the paginated center-wide patient roster with debounced server-side
 * search. Exposes `refresh()` so register/reassign actions can re-fetch.
 */

import { useState, useEffect, useCallback } from 'react';
import { listAdminPatients } from '../services/adminPatientService';

const PAGE_SIZE = 50; // matches backend AdminPatientPagination page_size

export function useAdminPatients() {
  const [patients, setPatients] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearchRaw] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  // Debounce search input by 300ms; reset to page 1 on new search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch patients when search, page, or reloadKey changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params = { page: currentPage };
    if (debouncedSearch) params.search = debouncedSearch;

    listAdminPatients(params)
      .then((data) => {
        if (!cancelled) {
          setPatients(data.results);
          setTotalCount(data.count);
          setTotalPages(Math.ceil(data.count / PAGE_SIZE));
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load patients.');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [debouncedSearch, currentPage, reloadKey]);

  const setSearch = useCallback((value) => setSearchRaw(value), []);
  const setPage = useCallback((page) => setCurrentPage(page), []);
  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  return {
    patients,
    totalCount,
    currentPage,
    totalPages,
    loading,
    error,
    search,
    setSearch,
    setPage,
    refresh,
  };
}
