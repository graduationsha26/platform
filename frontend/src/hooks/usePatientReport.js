/**
 * usePatientReport
 * Custom hook for the Reports page (Feature 035).
 *
 * Manages:
 *  - dateRange    — selected start/end dates (default: last 30 days)
 *  - stats        — StatsSummary computed from the stats API results
 *  - statsLoading / statsError — fetch lifecycle
 *  - downloadLoading / downloadError — PDF download lifecycle
 *  - applyDateRange() — fetches stats for the current dateRange
 *  - downloadPDF()    — POSTs to report endpoint and triggers file download
 *
 * Feature 035: Reports Page & PDF Download
 */

import { useState, useCallback } from 'react';
import { fetchPatientStats, downloadPatientReport } from '../services/analyticsService';

// ── Date helpers ────────────────────────────────────────────────────────────

/** Format a Date as YYYY-MM-DD (local time). */
function toISODate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function getDefaultDateRange() {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 29);
  return { startDate: toISODate(start), endDate: toISODate(today) };
}

// ── Summary aggregation ─────────────────────────────────────────────────────

/**
 * Compute a StatsSummary from the results array returned by the stats API.
 *
 * @param {object[]} results - Array of daily TremorStatistics objects
 * @returns {{ hasData, sessionCount, avgAmplitude, maxAmplitude, dominantFrequency, tremorReductionPct }}
 */
function computeSummary(results) {
  if (!results || results.length === 0) {
    return {
      hasData: false,
      sessionCount: 0,
      avgAmplitude: 0,
      maxAmplitude: 0,
      dominantFrequency: 0,
      tremorReductionPct: null,
    };
  }

  const n = results.length;
  const sessionCount = results.reduce((s, r) => s + r.session_count, 0);
  const avgAmplitude = results.reduce((s, r) => s + r.avg_amplitude, 0) / n;
  const maxAmplitude = Math.max(...results.map((r) => r.avg_amplitude));
  const dominantFrequency = results.reduce((s, r) => s + r.dominant_frequency, 0) / n;

  const validReductions = results.filter((r) => r.tremor_reduction_pct != null);
  const tremorReductionPct =
    validReductions.length > 0
      ? validReductions.reduce((s, r) => s + r.tremor_reduction_pct, 0) / validReductions.length
      : null;

  return {
    hasData: true,
    sessionCount,
    avgAmplitude,
    maxAmplitude,
    dominantFrequency,
    tremorReductionPct,
  };
}

// ── Error code → user message ───────────────────────────────────────────────

function mapDownloadError(parsedCode) {
  switch (parsedCode) {
    case 'NO_DATA_FOR_REPORT':
      return 'No data available for this period — try a different date range.';
    case 'PDF_SIZE_LIMIT_EXCEEDED':
      return 'Report too large — try a smaller date range (max ~90 days recommended).';
    default:
      return 'Report generation failed — please try again.';
  }
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function usePatientReport(patientId) {
  // Date range state
  const [dateRange, setDateRange] = useState(getDefaultDateRange);

  // Stats state
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState(null);

  // Download state
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  // ── applyDateRange ────────────────────────────────────────────────────────

  const applyDateRange = useCallback(async () => {
    if (!patientId) return;
    setStatsLoading(true);
    setStatsError(null);
    try {
      const data = await fetchPatientStats(patientId, dateRange.startDate, dateRange.endDate);
      setStats(computeSummary(data.results));
    } catch (err) {
      const status = err.response?.status;
      if (status === 403) {
        setStatsError('403: You do not have access to this patient\'s reports.');
      } else if (status === 404) {
        setStatsError('Patient not found.');
      } else {
        setStatsError('Failed to load statistics — please try again.');
      }
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  }, [patientId, dateRange.startDate, dateRange.endDate]);

  // ── downloadPDF ───────────────────────────────────────────────────────────

  const downloadPDF = useCallback(async () => {
    if (!patientId || !stats?.hasData) return;
    setDownloadLoading(true);
    setDownloadError(null);
    try {
      const blob = await downloadPatientReport(patientId, dateRange.startDate, dateRange.endDate);
      const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_patient${patientId}_${dateRange.startDate}_${dateRange.endDate}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(mapDownloadError(err.parsedCode));
    } finally {
      setDownloadLoading(false);
    }
  }, [patientId, dateRange.startDate, dateRange.endDate, stats?.hasData]);

  return {
    dateRange,
    setDateRange,
    stats,
    statsLoading,
    statsError,
    applyDateRange,
    downloadLoading,
    downloadError,
    downloadPDF,
  };
}
