/**
 * usePatients Hook
 * Manages paginated patient list with debounced server-side search.
 */

import { useState, useEffect, useCallback } from 'react';
import { getPatients } from '../services/patientService';

const PAGE_SIZE = 20;

export function usePatients() {
  const [patients, setPatients] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearchRaw] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Debounce search input by 300ms; reset to page 1 on new search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch patients when debouncedSearch or currentPage changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params = { page: currentPage, page_size: PAGE_SIZE };
    if (debouncedSearch) params.name = debouncedSearch;

    getPatients(params)
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
  }, [debouncedSearch, currentPage]);

  const setSearch = useCallback((value) => setSearchRaw(value), []);
  const setPage = useCallback((page) => setCurrentPage(page), []);

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
  };
}
