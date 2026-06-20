/**
 * ConnectionStatus
 * Small badge showing the live WebSocket connection state.
 * Feature 034: Live Tremor Monitor
 */

const STATUS_CONFIG = {
  connecting: {
    dot: 'bg-amber-400 animate-pulse',
    text: 'text-amber-700',
    label: 'Connecting...',
  },
  connected: {
    dot: 'bg-green-500',
    text: 'text-green-700',
    label: 'Connected',
  },
  disconnected: {
    dot: 'bg-red-500',
    text: 'text-red-700',
    label: 'Disconnected',
  },
};

const ConnectionStatus = ({ status }) => {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.disconnected;

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-block w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
      <span className={`text-sm font-medium ${cfg.text}`}>{cfg.label}</span>
    </div>
  );
};

export default ConnectionStatus;
