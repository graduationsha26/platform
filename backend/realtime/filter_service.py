"""
Tremor signal filtering and FFT analysis service.

Implements a real-time Parkinsonian tremor processing pipeline:
  1. FilterBank: per-patient, per-axis 4th-order Butterworth band-pass IIR
     filter (3-8 Hz, SOS form) applied to every 100 Hz BiometricReading.
  2. TremorFilterService: accumulates filtered samples in a 256-sample
     sliding window and runs an FFT every 100 samples (~1 Hz) to extract
     dominant tremor frequency and amplitude for all 6 IMU axes.
     Results are stored as TremorMetrics records and broadcast via
     Django Channels WebSocket to the patient's channel group.
"""
import logging
from collections import deque

import numpy as np
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from scipy.signal import butter, sosfilt, sosfilt_zi

logger = logging.getLogger(__name__)

# --- Algorithm constants -------------------------------------------------------

SAMPLE_RATE = 100               # Hz — glove firmware ODR
BANDPASS_LOW = 3.0              # Hz — clinical lower bound for Parkinsonian tremor
BANDPASS_HIGH = 8.0             # Hz — clinical upper bound
FILTER_ORDER = 4                # Butterworth prototype order (LP→BP doubles to 8th)
FFT_WINDOW_SIZE = 256           # samples — power of 2; 0.39 Hz frequency resolution
FFT_STEP_SIZE = 100             # samples — ~1 Hz FFT update rate; 61% overlap
AXES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']

# Noise-floor thresholds below which an axis is considered tremor-free
ACCEL_NO_TREMOR_THRESHOLD = 0.005   # m/s²  (~1.5× MPU9250 accel noise floor)
GYRO_NO_TREMOR_THRESHOLD = 0.1      # °/s   (~6× MPU9250 gyro noise floor)


# --- FilterBank ---------------------------------------------------------------

class FilterBank:
    """Per-patient, per-axis 4th-order Butterworth band-pass IIR filter bank.

    The filter is designed once at import time in SOS form (scipy recommends SOS
    over direct-form 'ba' for IIR filters above 2nd order to avoid numerical
    instability from poles near the unit circle).

    butter(N=4, btype='bandpass') produces an 8th-order filter (the LP→BP
    transform doubles the prototype order), so sos.shape == (8, 6) and each
    per-axis filter state zi has shape (8, 2).

    Filter state is stored per (patient_id, axis) and lazy-initialized from the
    first sample value to suppress the startup transient (FR-011).
    """

    def __init__(self):
        # Design the shared SOS filter (computed once, reused for all patients/axes)
        self.sos = butter(
            N=FILTER_ORDER,
            Wn=[BANDPASS_LOW, BANDPASS_HIGH],
            btype='bandpass',
            fs=SAMPLE_RATE,
            output='sos',
        )
        # _states[patient_id][axis] = zi (np.ndarray, shape (8, 2))
        self._states: dict[int, dict[str, np.ndarray]] = {}

    def filter(self, patient_id: int, axis: str, value: float) -> float:
        """Apply the IIR filter to a single sample and return the filtered value.

        Lazy-initializes filter state for new (patient_id, axis) pairs using
        the first sample value to minimise the startup transient.
        """
        if patient_id not in self._states:
            self._states[patient_id] = {}

        if axis not in self._states[patient_id]:
            # Initialize state as if the filter has been processing a constant
            # signal equal to `value` forever → zero initial transient
            self._states[patient_id][axis] = sosfilt_zi(self.sos) * value

        y, zi = sosfilt(
            self.sos,
            np.array([value]),
            zi=self._states[patient_id][axis],
        )
        self._states[patient_id][axis] = zi
        return float(y[0])

    def reset(self, patient_id: int) -> None:
        """Remove all filter state for a patient (e.g., on reconnect)."""
        self._states.pop(patient_id, None)


# --- TremorFilterService ------------------------------------------------------

class TremorFilterService:
    """Processes BiometricReading records through the tremor analysis pipeline.

    For each incoming reading:
      1. Applies FilterBank to all 6 axes.
      2. Appends filtered values to a per-patient 256-sample deque.
      3. Every FFT_STEP_SIZE (100) samples — once the buffer has accumulated
         FFT_WINDOW_SIZE (256) samples — triggers _run_fft_and_store().
      4. The first full window is discarded as a warmup period (FR-011).

    Designed to be called from the MQTT client process (single-threaded).
    All per-patient state is held in Python dicts (no Redis needed for local dev).
    """

    def __init__(self):
        self.filter_bank = FilterBank()
        self.channel_layer = get_channel_layer()
        # _buffers[patient_id] = deque of filtered sample dicts (maxlen=256)
        self._buffers: dict[int, deque] = {}
        # _sample_counters[patient_id] = samples since last FFT trigger
        self._sample_counters: dict[int, int] = {}
        # _warmed_up[patient_id] = True after the first window is discarded
        self._warmed_up: dict[int, bool] = {}

    def process(self, reading) -> None:
        """Process one BiometricReading through the filter+buffer+FFT pipeline.

        Args:
            reading: A BiometricReading instance (or duck-typed object with
                     .patient_id, .timestamp, and axis attributes).
        """
        patient_id = reading.patient_id

        # Lazy-initialize per-patient state
        if patient_id not in self._buffers:
            self._buffers[patient_id] = deque(maxlen=FFT_WINDOW_SIZE)
            self._sample_counters[patient_id] = 0
            self._warmed_up[patient_id] = False

        # Apply IIR filter to all 6 axes
        filtered = {'timestamp': reading.timestamp}
        for axis in AXES:
            raw = float(getattr(reading, axis))
            filtered[axis] = self.filter_bank.filter(patient_id, axis, raw)

        self._buffers[patient_id].append(filtered)
        self._sample_counters[patient_id] += 1

        # Check if it's time to run the FFT
        if (
            self._sample_counters[patient_id] >= FFT_STEP_SIZE
            and len(self._buffers[patient_id]) >= FFT_WINDOW_SIZE
        ):
            self._sample_counters[patient_id] = 0

            if not self._warmed_up[patient_id]:
                # Discard the first full window — filter hasn't settled yet
                self._warmed_up[patient_id] = True
                return

            self._run_fft_and_store(patient_id, reading)

    def _run_fft_and_store(self, patient_id: int, reading) -> None:
        """Run FFT on the current 256-sample window, store TremorMetrics, broadcast.

        Extracts dominant tremor frequency and peak amplitude for all 6 IMU axes,
        creates a TremorMetrics database record, and broadcasts a
        tremor_metrics_update message to the patient's WebSocket channel group.

        The deferred import of TremorMetrics avoids a circular import between
        realtime.filter_service and biometrics.models.
        """
        try:
            # --- Build signal arrays from the circular buffer --------------------
            buf = list(self._buffers[patient_id])   # FFT_WINDOW_SIZE dicts
            window_start = buf[0]['timestamp']
            window_end = buf[-1]['timestamp']

            # --- FFT setup -------------------------------------------------------
            hann = np.hanning(FFT_WINDOW_SIZE)
            coherent_gain = float(np.mean(hann))    # ≈ 0.5 for Hann window
            freqs = np.fft.rfftfreq(FFT_WINDOW_SIZE, d=1.0 / SAMPLE_RATE)
            band_mask = (freqs >= BANDPASS_LOW) & (freqs <= BANDPASS_HIGH)
            band_freqs = freqs[band_mask]

            # --- Per-axis FFT analysis -------------------------------------------
            axis_metrics: dict[str, dict] = {}
            for axis in AXES:
                signal = np.array([s[axis] for s in buf])
                # Amplitude-correct normalization (research.md R-003):
                #   - Factor 2.0: one-sided → two-sided spectrum recovery
                #   - coherent_gain correction: compensates Hann window attenuation
                fft_mag = (
                    2.0 * np.abs(np.fft.rfft(signal * hann))
                    / (FFT_WINDOW_SIZE * coherent_gain)
                )
                band_amp = fft_mag[band_mask]
                peak_idx = int(np.argmax(band_amp))
                peak_amplitude = float(band_amp[peak_idx])
                peak_freq = float(band_freqs[peak_idx])

                threshold = (
                    ACCEL_NO_TREMOR_THRESHOLD
                    if axis.startswith('a')
                    else GYRO_NO_TREMOR_THRESHOLD
                )
                freq_hz = peak_freq if peak_amplitude >= threshold else None
                axis_metrics[axis] = {'amplitude': peak_amplitude, 'frequency': freq_hz}

            # --- Determine dominant axis -----------------------------------------
            tremor_detected = any(
                m['frequency'] is not None for m in axis_metrics.values()
            )
            if tremor_detected:
                # Axis with the highest amplitude among detected (above-threshold) axes
                dominant_axis = max(
                    (ax for ax in AXES if axis_metrics[ax]['frequency'] is not None),
                    key=lambda ax: axis_metrics[ax]['amplitude'],
                )
            else:
                # No tremor detected — report the axis with the globally highest amplitude
                dominant_axis = max(AXES, key=lambda ax: axis_metrics[ax]['amplitude'])

            dominant_freq_hz = axis_metrics[dominant_axis]['frequency']
            dominant_amplitude = axis_metrics[dominant_axis]['amplitude']

            # --- Persist to database --------------------------------------------
            # Deferred import to avoid circular import: realtime ↔ biometrics
            from biometrics.models import TremorMetrics  # noqa: PLC0415

            TremorMetrics.objects.create(
                patient_id=patient_id,
                window_start=window_start,
                window_end=window_end,
                tremor_detected=tremor_detected,
                dominant_axis=dominant_axis,
                dominant_freq_hz=dominant_freq_hz,
                dominant_amplitude=dominant_amplitude,
                amp_aX=axis_metrics['aX']['amplitude'],
                amp_aY=axis_metrics['aY']['amplitude'],
                amp_aZ=axis_metrics['aZ']['amplitude'],
                amp_gX=axis_metrics['gX']['amplitude'],
                amp_gY=axis_metrics['gY']['amplitude'],
                amp_gZ=axis_metrics['gZ']['amplitude'],
                freq_aX=axis_metrics['aX']['frequency'],
                freq_aY=axis_metrics['aY']['frequency'],
                freq_aZ=axis_metrics['aZ']['frequency'],
                freq_gX=axis_metrics['gX']['frequency'],
                freq_gY=axis_metrics['gY']['frequency'],
                freq_gZ=axis_metrics['gZ']['frequency'],
            )

            # --- Broadcast via WebSocket ----------------------------------------
            try:
                # Compute dominant axis band spectrum for frontend FFT chart (Feature 034)
                dom_signal = np.array([s[dominant_axis] for s in buf])
                dom_fft_mag = (
                    2.0 * np.abs(np.fft.rfft(dom_signal * hann))
                    / (FFT_WINDOW_SIZE * coherent_gain)
                )
                dom_band_amp = dom_fft_mag[band_mask]

                message = {
                    'type': 'tremor_metrics_update',
                    'patient_id': patient_id,
                    'window_start': window_start.isoformat(),
                    'window_end': window_end.isoformat(),
                    'tremor_detected': tremor_detected,
                    'dominant_axis': dominant_axis,
                    'dominant_freq_hz': dominant_freq_hz,
                    'dominant_amplitude': dominant_amplitude,
                    'amplitudes': {ax: axis_metrics[ax]['amplitude'] for ax in AXES},
                    'frequencies': {ax: axis_metrics[ax]['frequency'] for ax in AXES},
                    # Full band spectrum of the dominant axis (Feature 034: SpectrumChart)
                    'dominant_band_freqs': band_freqs.tolist(),
                    'dominant_band_amplitudes': dom_band_amp.tolist(),
                }
                async_to_sync(self.channel_layer.group_send)(
                    f'patient_{patient_id}_tremor_data',
                    {'type': 'tremor_metrics_update', 'message': message},
                )
            except Exception as e:
                logger.error(
                    'TremorFilterService: WebSocket broadcast failed for patient %s: %s',
                    patient_id, e, exc_info=True,
                )

        except Exception as e:
            logger.error(
                'TremorFilterService: _run_fft_and_store failed for patient %s: %s',
                patient_id, e, exc_info=True,
            )
