"""
Gravity Filter Module

Implements a high-pass Butterworth filter to remove the static gravity component
from accelerometer IMU data, isolating the dynamic tremor signal.

Design rationale:
- Parkinson's tremor oscillates in the 3–12 Hz band.
- Gravity is a DC (0 Hz) component; orientation changes are typically < 0.3 Hz.
- A 2nd-order Butterworth high-pass with 0.5 Hz cutoff removes gravity while
  preserving all tremor content with negligible phase distortion (< 5° at 3 Hz).
- causal sosfilt is used for BOTH training and live inference to guarantee
  mathematical equivalence (FR-008). filtfilt cannot be used in streaming contexts.
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi
from typing import List, Tuple


ACCEL_COLUMNS = [0, 1, 2]   # aX, aY, aZ
GYRO_COLUMNS  = [3, 4, 5]   # gX, gY, gZ  — never filtered
ACCEL_AXES    = ["aX", "aY", "aZ"]
GYRO_AXES     = ["gX", "gY", "gZ"]


def design_gravity_filter(
    cutoff_hz: float = 0.5,
    fs: float = 37.0,
    order: int = 2,
) -> np.ndarray:
    """Design a high-pass Butterworth filter for gravity removal.

    Parameters
    ----------
    cutoff_hz : float
        Cutoff frequency in Hz (default 0.5 Hz — well below the 3 Hz tremor band).
    fs : float
        Sampling rate in Hz (default 37.0 Hz, empirically derived from PSMAD dataset).
    order : int
        Filter order (default 2 — sufficient rolloff, minimal phase distortion).

    Returns
    -------
    sos : np.ndarray
        Second-order sections representation of the designed filter, shape (n_sections, 6).
        Suitable for use with scipy.signal.sosfilt and sosfilt_zi.

    Raises
    ------
    ValueError
        If cutoff_hz is not in the valid range (0, fs/2).
    """
    nyquist = fs / 2.0
    if not (0 < cutoff_hz < nyquist):
        raise ValueError(
            f"cutoff_hz={cutoff_hz} must be in (0, {nyquist}) for fs={fs} Hz."
        )
    sos = butter(order, cutoff_hz / nyquist, btype="high", output="sos")
    return sos


def apply_gravity_filter(
    signal: np.ndarray,
    sos: np.ndarray,
    accel_columns: List[int] = None,
) -> np.ndarray:
    """Apply the gravity filter to a full (batch) signal array.

    Only the accelerometer columns are filtered. Gyroscope columns are copied
    through unchanged. Uses steady-state initial conditions so there is no
    startup transient — the filter behaves as if gravity has always been present.

    Use this function for TRAINING data (full signal available at once) and for
    DL model preprocessing (128-sample sequences). The filter is causal
    (forward-only) so output is identical to apply_gravity_filter_streaming
    called sample-by-sample with the same initial state.

    Parameters
    ----------
    signal : np.ndarray
        2-D array of shape (n_samples, n_axes). Column order must be
        [aX, aY, aZ, gX, gY, gZ] (or as specified by accel_columns).
    sos : np.ndarray
        SOS filter coefficients from design_gravity_filter().
    accel_columns : list of int, optional
        Column indices to filter. Defaults to [0, 1, 2] (aX, aY, aZ).

    Returns
    -------
    filtered : np.ndarray
        Array of same shape as signal. Accelerometer columns are high-pass
        filtered; gyroscope columns are unchanged.
    """
    if accel_columns is None:
        accel_columns = ACCEL_COLUMNS

    signal = np.asarray(signal, dtype=np.float64)
    filtered = signal.copy()

    for col in accel_columns:
        col_data = signal[:, col]
        # Steady-state initial conditions scaled by the first sample value.
        # This initialises the filter as if the signal has been at col_data[0]
        # forever, eliminating the startup transient caused by the gravity step.
        zi = sosfilt_zi(sos) * col_data[0]
        filtered_col, _ = sosfilt(sos, col_data, zi=zi)
        filtered[:, col] = filtered_col

    return filtered


def apply_gravity_filter_streaming(
    chunk: np.ndarray,
    sos: np.ndarray,
    zi: np.ndarray,
    accel_columns: List[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply the gravity filter to a streaming chunk, maintaining filter state.

    Use this for LIVE INFERENCE where samples arrive in real-time and the full
    signal is not available in advance. The state zi must be carried across
    successive calls to maintain continuity.

    Parameters
    ----------
    chunk : np.ndarray
        Array of shape (n_samples, n_axes) or (n_axes,) for a single sample.
        Accelerometer columns are filtered in-place; gyroscope columns pass through.
    sos : np.ndarray
        SOS filter coefficients from design_gravity_filter().
    zi : np.ndarray
        Current filter state, shape (n_sections, 2, n_accel_columns).
        Initialise with init_streaming_state() before the first call.
    accel_columns : list of int, optional
        Column indices to filter. Defaults to [0, 1, 2].

    Returns
    -------
    filtered_chunk : np.ndarray
        Filtered array with same shape as chunk.
    updated_zi : np.ndarray
        Updated filter state to pass to the next call.
    """
    if accel_columns is None:
        accel_columns = ACCEL_COLUMNS

    single_sample = chunk.ndim == 1
    if single_sample:
        chunk = chunk[np.newaxis, :]

    chunk = np.asarray(chunk, dtype=np.float64)
    filtered = chunk.copy()
    updated_zi = zi.copy()

    for i, col in enumerate(accel_columns):
        col_data = chunk[:, col]
        filtered_col, updated_zi[:, :, i] = sosfilt(
            sos, col_data, zi=updated_zi[:, :, i]
        )
        filtered[:, col] = filtered_col

    if single_sample:
        filtered = filtered[0]

    return filtered, updated_zi


def init_streaming_state(
    sos: np.ndarray,
    first_values: np.ndarray,
    accel_columns: List[int] = None,
) -> np.ndarray:
    """Compute initial filter state for streaming inference.

    Scales the steady-state initial conditions by the first sample value for each
    accelerometer axis, so the filter starts as if gravity has been present at that
    level since before the recording began. This eliminates the startup transient.

    Parameters
    ----------
    sos : np.ndarray
        SOS filter coefficients from design_gravity_filter().
    first_values : np.ndarray
        1-D array of the first sample values for ALL axes, shape (n_axes,).
        Only the accelerometer columns are used for scaling.
    accel_columns : list of int, optional
        Column indices that will be filtered. Defaults to [0, 1, 2].

    Returns
    -------
    zi : np.ndarray
        Initial filter state, shape (n_sections, 2, n_accel_columns).
        Pass this as the zi argument to apply_gravity_filter_streaming().
    """
    if accel_columns is None:
        accel_columns = ACCEL_COLUMNS

    n_sections = sos.shape[0]
    zi_base = sosfilt_zi(sos)  # shape (n_sections, 2)

    zi = np.zeros((n_sections, 2, len(accel_columns)), dtype=np.float64)
    for i, col in enumerate(accel_columns):
        zi[:, :, i] = zi_base * first_values[col]

    return zi


def get_filter_params_dict(
    cutoff_hz: float,
    fs: float,
    order: int,
    sos: np.ndarray,
    accel_columns: List[int] = None,
) -> dict:
    """Return a JSON-serialisable dict of filter parameters for model metadata.

    Storing the SOS coefficients (not just the design parameters) eliminates
    any floating-point differences if the filter is reconstructed at inference time.

    Parameters
    ----------
    cutoff_hz : float
        Cutoff frequency used to design the filter.
    fs : float
        Sampling rate used to design the filter.
    order : int
        Filter order.
    sos : np.ndarray
        SOS coefficients returned by design_gravity_filter().
    accel_columns : list of int, optional
        Which column indices were filtered. Defaults to [0, 1, 2].

    Returns
    -------
    dict
        Keys: type, subtype, order, cutoff_hz, sampling_rate_hz,
              sos_coefficients (nested list), applied_to_axes,
              skipped_axes, initial_conditions.
    """
    if accel_columns is None:
        accel_columns = ACCEL_COLUMNS

    all_axes = ACCEL_AXES + GYRO_AXES
    applied = [all_axes[c] for c in accel_columns if c < len(all_axes)]
    skipped = [ax for ax in all_axes if ax not in applied]

    return {
        "type": "butterworth",
        "subtype": "highpass",
        "order": order,
        "cutoff_hz": cutoff_hz,
        "sampling_rate_hz": fs,
        "sos_coefficients": sos.tolist(),
        "applied_to_axes": applied,
        "skipped_axes": skipped,
        "initial_conditions": "sosfilt_zi_scaled",
    }
