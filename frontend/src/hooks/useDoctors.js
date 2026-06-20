/**
 * useDoctors Hook
 *
 * Feature 047: Staff (Doctor) Management
 * Manages the paginated admin doctor roster with debounced server-side search.
 * Exposes `refresh()` so create/edit/toggle actions can re-fetch without reload.
 */

import { useState, useEffect, useCallback } from 'react';
import { listDoctors } from '../services/doctorService';

const PAGE_SIZE = 50; // matches backend global PageNumberPagination PAGE_SIZE

export function useDoctors() {
  const [doctors, setDoctors] = useState([]);
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

  // Fetch doctors when search, page, or reloadKey changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params = { page: currentPage };
    if (debouncedSearch) params.search = debouncedSearch;

    listDoctors(params)
      .then((data) => {
        if (!cancelled) {
          setDoctors(data.results);
          setTotalCount(data.count);
          setTotalPages(Math.ceil(data.count / PAGE_SIZE));
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load doctors.');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [debouncedSearch, currentPage, reloadKey]);

  const setSearch = useCallback((value) => setSearchRaw(value), []);
  const setPage = useCallback((page) => setCurrentPage(page), []);
  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  return {
    doctors,
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
