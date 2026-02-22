/**
 * useTremorMonitor
 * Main hook for the Live Tremor Monitor page (Feature 034).
 *
 * Manages the WebSocket connection lifecycle and all live data state:
 *  - connectionStatus — 'connecting' | 'connected' | 'disconnected'
 *  - chartData        — rolling 60-second amplitude array for AmplitudeChart
 *  - spectrumData     — FFT frequency bins for SpectrumChart (US2)
 *  - severity         — current ML severity level + confidence (US3)
 *  - rawValues        — live 6-axis sensor readings (US4)
 *  - hasActiveStream  — false if no biometric_reading in the last 5 s (US4)
 *
 * Architecture:
 *  - biometric_reading (~100 Hz) → pushed to bufferRef without setState
 *  - setInterval at 100 ms (10 Hz) → prunes buffer, flushes to chartData state
 *  - All other message types update their respective state on every message
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import TremorWebSocketService from '../services/tremorWebSocketService';

const WINDOW_MS = 60_000;       // 60-second rolling amplitude window
const FLUSH_INTERVAL_MS = 100;  // flush buffer to chart state at 10 Hz
const STREAM_TIMEOUT_MS = 5_000; // "No active stream" after 5 s of silence

export function useTremorMonitor(patientId) {
  // ── Connection ─────────────────────────────────────────────────────────────
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [accessDenied, setAccessDenied] = useState(false);

  // ── US1: Amplitude chart ───────────────────────────────────────────────────
  // Write path: useRef (no re-renders at 100 Hz)
  const bufferRef = useRef([]);
  // Read path: useState (triggers chart re-render at 10 Hz)
  const [chartData, setChartData] = useState([]);

  // ── US2: FFT spectrum ──────────────────────────────────────────────────────
  const [spectrumData, setSpectrumData] = useState([]);

  // ── US3: Severity ──────────────────────────────────────────────────────────
  const [severity, setSeverity] = useState({ level: null, confidence: null });

  // ── US4: Raw axis values + active stream detection ─────────────────────────
  const [rawValues, setRawValues] = useState(null);
  const [hasActiveStream, setHasActiveStream] = useState(false);
  const lastDataAtRef = useRef(0);

  // ── WebSocket service ref ──────────────────────────────────────────────────
  const serviceRef = useRef(null);

  // ── Message handler (stable reference via useCallback) ────────────────────
  const handleMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'biometric_reading': {
        // US1: push amplitude point to ref buffer (no setState)
        const { aX, aY, aZ } = msg;
        const amplitude = Math.sqrt(aX * aX + aY * aY + aZ * aZ);
        bufferRef.current.push({ ts: Date.parse(msg.timestamp), amplitude });

        // US4: update raw axis values + record last-data timestamp
        setRawValues({
          aX: msg.aX,
          aY: msg.aY,
          aZ: msg.aZ,
          gX: msg.gX,
          gY: msg.gY,
          gZ: msg.gZ,
          timestamp: msg.timestamp,
        });
        lastDataAtRef.current = Date.now();
        break;
      }

      case 'tremor_metrics_update': {
        // US2: build spectrum data from dominant axis band arrays
        if (msg.dominant_band_freqs && msg.dominant_band_amplitudes) {
          setSpectrumData(
            msg.dominant_band_freqs.map((freq, i) => ({
              freq: Number(freq.toFixed(2)),
              amplitude: msg.dominant_band_amplitudes[i] ?? 0,
            }))
          );
        }
        break;
      }

      case 'tremor_data': {
        // US3: extract ML severity prediction
        setSeverity({
          level: msg.prediction?.severity ?? null,
          confidence: msg.prediction?.confidence ?? null,
        });
        break;
      }

      case 'status':
        // Connection lifecycle status from backend — handled via onConnected/onDisconnected
        break;

      case 'pong':
        // Keepalive response — no action needed
        break;

      default:
        break;
    }
  }, []);

  // ── Mount / unmount: open WS, start intervals, close on cleanup ───────────
  useEffect(() => {
    if (!patientId) return;

    const service = new TremorWebSocketService(patientId, {
      onMessage: handleMessage,
      onConnected: () => setConnectionStatus('connected'),
      onDisconnected: (code) => {
        setConnectionStatus('disconnected');
        if (code === 4403) setAccessDenied(true);
      },
      onError: () => {}, // errors are followed by onDisconnected
    });
    serviceRef.current = service;
    service.connect();

    // 10 Hz flush: prune buffer to last 60 s, push to chart state
    const flushTimer = setInterval(() => {
      if (bufferRef.current.length === 0) return;
      const cutoff = Date.now() - WINDOW_MS;
      setChartData((prev) => {
        const merged = [...prev, ...bufferRef.current];
        bufferRef.current = [];
        return merged.filter((p) => p.ts >= cutoff);
      });
    }, FLUSH_INTERVAL_MS);

    // 1 Hz active-stream check
    const streamTimer = setInterval(() => {
      setHasActiveStream(Date.now() - lastDataAtRef.current < STREAM_TIMEOUT_MS);
    }, 1_000);

    return () => {
      service.destroy();
      clearInterval(flushTimer);
      clearInterval(streamTimer);
    };
  }, [patientId, handleMessage]);

  return {
    connectionStatus,
    accessDenied,
    chartData,
    spectrumData,
    severity,
    rawValues,
    hasActiveStream,
  };
}
