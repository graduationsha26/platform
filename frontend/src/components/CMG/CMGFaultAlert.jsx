/**
 * CMGFaultAlert
 * Displays a dismissible alert card per unacknowledged motor fault event.
 *
 * Loads unacknowledged faults on mount. Each card shows fault details and
 * an "Acknowledge" button that calls the REST API and removes the card.
 *
 * Feature 027: CMG Brushless Motor & ESC Initialization
 */

import { useState, useEffect } from 'react';
import { getFaults, acknowledgeFault } from '../../services/cmgService';

/**
 * @param {Object} props
 * @param {number} props.deviceId - Device to query for unacknowledged faults
 * @param {Object|null} props.newFaultMessage - Live cmg_fault WS message (or null)
 */
export default function CMGFaultAlert({ deviceId, newFaultMessage }) {
  const [faults, setFaults] = useState([]);
  const [acknowledging, setAcknowledging] = useState({});

  // Fetch unacknowledged faults on mount
  useEffect(() => {
    if (!deviceId) return;
    getFaults(deviceId, { acknowledged: false })
      .then((data) => setFaults(data.results ?? []))
      .catch(() => {});
  }, [deviceId]);

  // Append new fault arriving via WebSocket
  useEffect(() => {
    if (!newFaultMessage) return;
    setFaults((prev) => {
      const alreadyPresent = prev.some((f) => f.id === newFaultMessage.id);
      return alreadyPresent ? prev : [newFaultMessage, ...prev];
    });
  }, [newFaultMessage]);

  const handleAcknowledge = async (faultId) => {
    setAcknowledging((prev) => ({ ...prev, [faultId]: true }));
    try {
      await acknowledgeFault(faultId);
      setFaults((prev) => prev.filter((f) => f.id !== faultId));
    } catch {
      // Leave the card visible so the doctor can retry
    } finally {
      setAcknowledging((prev) => ({ ...prev, [faultId]: false }));
    }
  };

  if (faults.length === 0) return null;

  return (
    <div className="space-y-2">
      {faults.map((fault) => (
        <div
          key={fault.id}
          className="flex items-start justify-between rounded-lg border border-red-300 bg-red-50 p-3 shadow-sm"
        >
          <div className="text-sm text-red-800">
            <p className="font-semibold capitalize">
              {fault.fault_type} fault
            </p>
            <p className="text-xs text-red-600">
              {new Date(fault.occurred_at).toLocaleString()}
            </p>
            {fault.rpm_at_fault != null && (
              <p className="text-xs text-red-600">
                RPM at fault: {fault.rpm_at_fault.toLocaleString()}
              </p>
            )}
            {fault.current_at_fault != null && (
              <p className="text-xs text-red-600">
                Current at fault: {fault.current_at_fault.toFixed(2)} A
              </p>
            )}
          </div>
          <button
            onClick={() => handleAcknowledge(fault.id)}
            disabled={acknowledging[fault.id]}
            className="ml-4 shrink-0 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {acknowledging[fault.id] ? 'Acknowledging…' : 'Acknowledge'}
          </button>
        </div>
      ))}
    </div>
  );
}
