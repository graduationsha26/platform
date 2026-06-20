# Research Notes: Tremor Signal Filtering & Frequency Analysis

**Feature**: 026-tremor-bandpass-fft
**Date**: 2026-02-18
**Status**: Complete — all decisions resolved

---

## R-001: Implementation Location — Where Does Filtering Happen?

**Decision**: Backend (Django realtime pipeline), not firmware.

**Rationale**:
- The spec requires "dashboard visualization" — output must reach the Django/React stack regardless
- Doing FFT in firmware (ESP32) would require storing large intermediate buffers (256 samples × 6 axes) on a constrained microcontroller
- The backend already has the `realtime/mqtt_client.py` pipeline receiving 100Hz BiometricReading records; hooking in there is the cleanest integration point
- The existing ML inference pipeline (feature 008) already runs server-side — keeping signal processing server-side maintains consistency
- Python's `scipy` and `numpy` provide production-quality DSP primitives with no additional licensing burden

**Alternatives considered**:
- Firmware filtering (ESP32): Rejected — requires 256-sample float buffer (6 axes × 256 × 4 bytes = 6 KB SRAM), strains ESP32 memory; dashboard integration requires additional MQTT schema changes
- Hybrid (firmware filters, backend does FFT): Rejected — adds firmware complexity without corresponding benefit; introduces coupling between firmware and backend data formats

---

## R-002: Band-Pass Filter Algorithm & Order

**Decision**: 4th-order Butterworth IIR band-pass filter, implemented in Second-Order Sections (SOS) cascade form.

**scipy.signal API** (confirmed correct):
```python
from scipy.signal import butter, sosfilt, sosfilt_zi

# Design once at startup
sos = butter(N=4, Wn=[3.0, 8.0], btype='bandpass', fs=100.0, output='sos')
# sos.shape = (8, 6) — 8 biquad sections (NOT 4 — the LP→BP transform doubles the order)
# Each section contains [b0, b1, b2, a0, a1, a2]
```

**Order-doubling note**: `butter(N=4, btype='bandpass')` produces an **8th-order** filter. The lowpass prototype (order 4) is transformed to a bandpass filter, which doubles the number of poles. The SOS has 8 sections (2×4), shape `(8, 6)`. This is expected and correct.

**Real-time per-sample processing**:
```python
# Initialize state for a new device (avoids step-input transient):
zi = sosfilt_zi(sos) * first_sample_value   # shape: (8, 2) — 2 delay regs per section

# Per-sample filtering:
y_sample, zi = sosfilt(sos, [x_sample], zi=zi)
filtered_value = float(y_sample[0])
```

**Why SOS form over direct-form (ba)**:
- Direct-form coefficients for 4th-order Butterworth at 3-8 Hz / 100 Hz sample rate have very small coefficients (poles near unit circle) — prone to floating-point catastrophic cancellation
- SOS cascades 4 second-order sections, each numerically stable; scipy's SOS implementation is the recommended approach for all IIR filters above 2nd order

**Why 4th order (not 2nd)**:
- Roll-off: 4th order = 80 dB/decade (4 × 20 dB/pole-pair-octave)
- At 1 Hz (voluntary movement): attenuation ≈ `20 × 4 × log10(3/1) ≈ 38 dB` — well above 20 dB requirement
- At 15 Hz (noise): attenuation ≈ `20 × 4 × log10(15/8) ≈ 20 dB` — meets requirement at 15 Hz
- 2nd-order achieves only half this roll-off

**Why Butterworth (not Chebyshev or elliptic)**:
- Butterworth: maximally flat passband — best amplitude accuracy in 3-8 Hz band; no passband ripple
- Chebyshev Type I: faster roll-off but introduces passband ripple → amplitude errors → compromises SC-003 (±10% amplitude accuracy)
- Elliptic: fastest roll-off but both passband and stopband ripple — too complex for limited benefit in this application
- Chebyshev Type II: equiripple stopband only — viable alternative but Butterworth is simpler and sufficient

**Startup transient handling** (FR-011):
- `sosfilt_zi(sos) * initial_value` initializes the filter state as if the filter has been processing a constant signal at `initial_value` forever — this gives a zero initial transient when the input starts at `initial_value`
- A warmup period equal to one FFT window (2.56 seconds = 256 samples) is applied: the first FFT result is discarded before reporting begins

---

## R-003: FFT Configuration

**Decision**: 256-sample window, Hann windowing, 100-sample step (1 Hz metric update rate).

**Parameter derivation**:
- Frequency resolution = `fs / N` = `100 / 256` ≈ **0.39 Hz** — meets ≤0.5 Hz requirement (SC-002)
- Window duration = `256 / 100` = **2.56 seconds**
- 3-8 Hz band contains `ceil(8/0.39) - floor(3/0.39) + 1` = `21 - 8 + 1` = **14 FFT bins**
- Step size = 100 samples = 1.0 s → update rate = 1 Hz → meets FR-008 (≥1 update/s)
- Overlap = 156 samples = 61% → smooths metric transitions

**Why 256 samples (not 200 or 512)**:
- 256 is a power of 2 → optimal FFT performance (radix-2 Cooley-Tukey)
- 200 samples gives 0.5 Hz exactly but is not a power of 2 (slower FFT, only marginally worse resolution)
- 512 samples (5.12 s) gives 0.195 Hz resolution but doubles metric latency unnecessarily

**Hann window application** (reduces spectral leakage from non-integer periods):
```python
import numpy as np

hann = np.hanning(256)  # Pre-computed once
windowed = signal_array * hann  # Element-wise multiply
freqs = np.fft.rfftfreq(256, d=1.0 / 100.0)

# Correct amplitude normalization (see formula below)
coherent_gain = np.mean(hann)           # ≈ 0.5 for Hann window
fft_mag = 2.0 * np.abs(np.fft.rfft(windowed)) / (256 * coherent_gain)
```

**Amplitude normalization — full derivation**:
1. `rfft` output for a real sinusoid of amplitude A: single-sided magnitude = `A × N / 2` (one-sided → multiply by 2 to recover both sides)
2. Dividing by `N` normalizes by sample count → back to amplitude A
3. The Hann window attenuates the signal: its coherent gain is `mean(hann) ≈ 0.5` → divide by 0.5 (or multiply by 2) to correct

**Complete formula**:
```python
fft_mag = 2.0 * np.abs(np.fft.rfft(windowed)) / (N * np.mean(hann))
# For N=256 and Hann: fft_mag ≈ np.abs(rfft(windowed)) * 4.0 / 256
```

Without the `coherent_gain` correction, Hann-windowed amplitudes are underestimated by ~2× compared to the true physical amplitude. This would cause the "no tremor" threshold to incorrectly classify mild tremors as absent.
```

---

## R-004: "No Tremor" Detection Threshold

**Decision**: Amplitude threshold applied to the peak FFT magnitude in the 3-8 Hz band.

| Axis type | Threshold | Rationale |
|---|---|---|
| Accelerometer (aX, aY, aZ) | 0.005 m/s² | ~0.5 mg; above MPU9250 noise floor (~0.3 mg RMS in 3-8 Hz band at ±2g range, 41 Hz DLPF) |
| Gyroscope (gX, gY, gZ) | 0.1 °/s | ~6× gyro noise floor; distinguishes tremor from thermal drift |

**Noise floor derivation**:
- MPU9250 datasheet: accel noise spectral density ≈ 300 μg/√Hz at ±2g
- Over 3-8 Hz band (5 Hz bandwidth): integrated noise = 300 μg × √5 ≈ 671 μg ≈ 0.0066 m/s²
- Threshold = 0.005 m/s² is slightly below the noise floor — by design, tunable via config constant

**Configuration**: Both thresholds are module-level constants in `filter_service.py`, easily adjustable for empirical calibration.

---

## R-005: Database Storage Strategy

**Decision**: Store one `TremorMetrics` row per FFT window update (~1 row/second per active patient). Do NOT store the filtered signal itself.

**Rationale**:
- Filtered signal at 100 Hz: 6 axes × 4 bytes × 100 samples/s = 2.4 KB/s = 207 MB/day per patient — impractical
- TremorMetrics at 1 row/s: ~14 columns × 8 bytes × 86,400 s/day ≈ 10 MB/day per patient — manageable
- Raw BiometricReading is already stored and can be replayed through the filter pipeline offline if needed

**Model placement**: `biometrics` Django app (TremorMetrics is derived from BiometricReading, same domain).

**Per-axis storage**: Store all 6 axis amplitudes and 6 axis frequencies (nullable) in flat columns. This allows SQL aggregation queries without JSON parsing.

---

## R-006: In-Memory Filter State Management

**Decision**: Per-patient filter state (scipy IIR filter zi) stored in a Python dictionary within the `TremorFilterService` singleton in the MQTT client process.

**Structure**:
```
filter_bank._states: Dict[patient_id: int, Dict[axis: str, zi: np.ndarray]]
tremor_service._buffers: Dict[patient_id: int, deque(maxlen=256)]
tremor_service._sample_counters: Dict[patient_id: int, int]
tremor_service._warmed_up: Dict[patient_id: int, bool]
```

**Lifecycle**:
- State created lazily on first reading from a patient
- State persists until MQTT client restarts (acceptable for local development)
- State resets automatically if MQTT client reconnects (filter re-warms over 2.56 s)
- No Redis or database persistence needed for filter state

**Why in-memory (not Redis/DB)**:
- Filter state is real-time ephemeral (stale state after restart produces a ~2.56 s warmup period, not data corruption)
- Local development only — no multi-process deployment requiring shared state

---

## R-007: WebSocket Integration

**Decision**: Broadcast `tremor_metrics_update` messages to the existing `patient_{patient_id}_tremor_data` Django Channels group.

**Message type**: `tremor_metrics_update` — a new type alongside the existing `tremor_data` messages.

**Consumer**: The existing WebSocket consumer in `realtime/consumers.py` must add a handler for `tremor_metrics_update`. Frontend connects to the same channel and receives both message types.

**Broadcast frequency**: ~1 Hz (per FFT update), much lower than the 100 Hz BiometricReading stream.

---

## R-008: scipy/numpy Dependency Status

**Decision**: No new pip dependencies required. `scipy` and `numpy` are already transitive dependencies of `scikit-learn` (which is in the ML pipeline). Explicit imports in `filter_service.py` suffice.

**Verification**: `import scipy.signal; import numpy` will work in any environment where scikit-learn is installed.

---

## Constitution Compliance

| Principle | Status | Notes |
|---|---|---|
| Monorepo Architecture | ✅ PASS | All new code in `backend/` |
| Tech Stack Immutability | ✅ PASS | scipy/numpy are transitive scikit-learn deps |
| Database Strategy | ✅ PASS | TremorMetrics in Supabase PostgreSQL |
| Authentication | ✅ PASS | TremorMetrics API uses JWT via IsAuthenticated |
| Security-First | ✅ PASS | No new secrets; all config in existing .env |
| Real-time (Channels) | ✅ PASS | tremor_metrics_update via Django Channels |
| MQTT Integration | ✅ PASS | Hooks into existing _handle_reading_message |
| AI Model Serving | N/A | DSP math, not ML model serving |
| API Standards | ✅ PASS | REST + JSON, snake_case |
| Development Scope | ✅ PASS | Local dev only |

**Overall**: ✅ PASS — no constitution violations.
