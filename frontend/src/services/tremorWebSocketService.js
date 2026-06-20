/**
 * TremorWebSocketService
 * WebSocket client for the live tremor data stream with automatic
 * exponential-backoff reconnection and 30-second ping keepalive.
 *
 * Feature 034: Live Tremor Monitor Page
 *
 * Endpoint: ws://{host}/ws/tremor-data/{patientId}/?token={jwt}
 * Authentication: JWT access token appended as a query parameter.
 */

import { getToken } from '../utils/tokenStorage';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
const PING_INTERVAL_MS = 30_000;
const MAX_RECONNECT_ATTEMPTS = 10;
// Backoff delays in ms: 1s, 2s, 4s, 8s, 16s, then capped at 30s
const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];

class TremorWebSocketService {
  /**
   * @param {number|string} patientId - Patient database ID
   * @param {{
   *   onMessage: (msg: object) => void,
   *   onConnected: () => void,
   *   onDisconnected: (code: number, reason: string) => void,
   *   onError: (event: Event) => void,
   * }} handlers
   */
  constructor(patientId, handlers) {
    this._patientId = patientId;
    this._handlers = handlers;
    this._ws = null;
    this._pingTimer = null;
    this._reconnectTimer = null;
    this._reconnectAttempts = 0;
    this._destroyed = false;
  }

  /** Open the WebSocket connection. */
  connect() {
    if (this._destroyed) return;

    const token = getToken();
    const url = `${WS_BASE_URL}/ws/tremor-data/${this._patientId}/?token=${token}`;

    this._ws = new WebSocket(url);

    this._ws.onopen = () => {
      if (this._destroyed) { this._ws.close(); return; }
      this._reconnectAttempts = 0;
      this._startPing();
      this._handlers.onConnected();
    };

    this._ws.onmessage = (event) => {
      if (this._destroyed) return;
      try {
        const msg = JSON.parse(event.data);
        this._handlers.onMessage(msg);
      } catch {
        // Ignore malformed frames
      }
    };

    this._ws.onclose = (event) => {
      this._stopPing();
      if (this._destroyed) return;
      this._handlers.onDisconnected(event.code, event.reason);
      // 4403: access denied — do not retry
      if (event.code !== 4403) {
        this._scheduleReconnect();
      }
    };

    this._ws.onerror = (event) => {
      if (this._destroyed) return;
      this._handlers.onError(event);
    };
  }

  /** Permanently close the connection and cancel any pending reconnection. */
  destroy() {
    this._destroyed = true;
    this._stopPing();
    clearTimeout(this._reconnectTimer);
    if (this._ws) {
      this._ws.onclose = null; // prevent reconnect loop on manual close
      this._ws.close();
      this._ws = null;
    }
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  _startPing() {
    this._stopPing();
    this._pingTimer = setInterval(() => {
      if (this._ws?.readyState === WebSocket.OPEN) {
        this._ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL_MS);
  }

  _stopPing() {
    clearInterval(this._pingTimer);
    this._pingTimer = null;
  }

  _scheduleReconnect() {
    if (this._destroyed) return;
    if (this._reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      // Exhausted retries — leave in permanent disconnect state
      return;
    }
    const delayMs = BACKOFF_DELAYS[Math.min(this._reconnectAttempts, BACKOFF_DELAYS.length - 1)];
    this._reconnectAttempts += 1;
    this._reconnectTimer = setTimeout(() => {
      if (!this._destroyed) this.connect();
    }, delayMs);
  }
}

export default TremorWebSocketService;
