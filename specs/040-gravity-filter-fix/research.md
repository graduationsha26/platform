# Research: Gravity Filter Fix for ML Pipeline

**Feature**: 040-gravity-filter-fix | **Date**: 2026-04-13

## R1: High-Pass Filter Design for Gravity Removal from IMU Accelerometer

### Decision
Use a 2nd-order Butterworth high-pass filter with 0.5 Hz cutoff frequency, implemented using second-order sections (SOS) representation via `scipy.signal.butter(N=2, Wn=0.5, btype='high', fs=37.0, output='sos')`.

### Rationale
- **Butterworth** chosen for maximally flat passband response — no ripple in the tremor band (3-12 Hz), ensuring tremor signal fidelity.
- **0.5 Hz cutoff** sits well below the Parkinson's tremor band (3-12 Hz), providing a safety margin of 6x. Gravity is a DC (0 Hz) component; hand orientation changes are typically <0.3 Hz. The 0.5 Hz cutoff removes both while preserving all tremor content.
- **2nd-order** balances sharpness of gravity removal against phase distortion. At 0.5 Hz cutoff and 37 Hz sampling rate, a 2nd-order filter provides -40 dB/decade rolloff, attenuating gravity by >40 dB while introducing <5° phase shift at 3 Hz.
- **SOS representation** avoids numerical instability issues that plague transfer function (b, a) form for higher-order filters. Though 2nd order is inherently stable, SOS is best practice and costs nothing.

### Alternatives Considered
| Alternative | Why Rejected |
|------------|-------------|
| Complementary filter (accel + gyro fusion) | More complex, requires gyro integration, calibration-sensitive. Butterworth is simpler and sufficient for removing gravity from training data. |
| Simple moving average subtraction | Not a proper frequency-domain filter. Introduces artifacts at window boundaries and doesn't have a clean cutoff. |
| 4th-order Butterworth | Sharper rolloff unnecessary — 0.5 Hz is already far from 3 Hz. Higher order adds more phase distortion and group delay. |
| Chebyshev Type I | Passband ripple unacceptable for tremor signal preservation. |
| filtfilt (zero-phase) for training | Would give better signal quality but breaks mathematical equivalence with live inference (which must be causal). |
| 1.0 Hz cutoff | Safe but removes less gravity artifact. 0.5 Hz is more conservative and still well below 3 Hz tremor band. |

---

## R2: Causal vs Zero-Phase Filtering for Train-Live Equivalence

### Decision
Use causal filtering (`sosfilt`) for both training and live inference. Do NOT use zero-phase filtering (`sosfiltfilt`/`filtfilt`) for training.

### Rationale
- **Mathematical equivalence** (FR-008) requires identical outputs for identical inputs between training and live pipelines.
- `filtfilt` processes data forward and backward — impossible in real-time streaming where future samples are unavailable.
- `sosfilt` processes data forward-only (causal), which is compatible with both batch (training) and streaming (live) modes.
- The phase distortion from causal filtering at the tremor band is negligible because:
  - At 3 Hz (lowest tremor frequency), a 2nd-order 0.5 Hz highpass introduces ~11° phase lag
  - At 6 Hz (typical Parkinson's tremor), phase lag drops to ~5°
  - Feature extraction functions (RMS, mean, std, skewness, kurtosis) are phase-invariant — they measure amplitude distribution, not phase
  - FFT tremor energy extraction is magnitude-based, also phase-invariant

### Alternatives Considered
| Alternative | Why Rejected |
|------------|-------------|
| filtfilt for training, sosfilt for live | Violates FR-008. Different outputs for same input. Most common source of train-serve skew in ML deployments. |
| Approximate filtfilt in live via buffered bidirectional pass | Adds latency (must buffer full window before filtering). Complex state management. Marginal benefit for phase-invariant features. |

---

## R3: Filter State Management for Live Streaming

### Decision
Use `scipy.signal.sosfilt_zi` to compute steady-state initial conditions, then maintain filter state (`zi`) across streaming chunks using the `zi` parameter of `sosfilt`.

### Rationale
- Without proper initial conditions, the filter produces a transient artifact at the start of each session (ringing as it converges from zero state).
- `sosfilt_zi(sos)` computes the initial state assuming the input has been at a constant value for a long time — perfect for gravity, which IS a constant value.
- Scaling `zi` by the first sample value (`zi * x[0]` per axis) initializes the filter as if gravity has always been present, eliminating startup transient.
- The `zi` state is updated by `sosfilt` on each call and persists across chunks, maintaining continuity.

### Alternatives Considered
| Alternative | Why Rejected |
|------------|-------------|
| Zero initial conditions | Causes ringing/transient for first ~2 seconds of data. Predictions during this period would be unreliable. |
| Discard first N samples | Wastes data and adds latency to first prediction. |
| Pre-fill filter with synthetic constant signal | Equivalent to sosfilt_zi approach but more code. |

---

## R4: Where to Insert Filter in Existing Pipeline

### Decision
Insert the gravity filter at the earliest possible point — after raw data loading and column renaming, but BEFORE normalization, windowing, and feature extraction.

### Rationale
- Gravity is a physical artifact in the raw signal. Removing it before any other processing ensures all downstream steps (normalization, feature extraction, model training) operate on gravity-free data.
- If we normalized first, the StandardScaler would learn the gravity offset as part of the mean, partially compensating but not fully removing it — and creating a dependency between normalization parameters and gravity orientation.
- The filter operates on the full continuous signal, which gives it maximum context for state estimation. Windowing after filtering is cleaner than filtering individual windows.

### Pipeline Order (updated)
```
Raw signal → Gravity high-pass filter (accel only) → Normalization → Windowing → Feature extraction → Model
```

---

## R5: Sampling Rate Handling

### Decision
Compute sampling rate dynamically from the Timestamp column using median of timestamp differences (existing approach in `4_psmad_pipeline.py`). Store the computed rate in filter parameters. Default to 37 Hz if computation fails.

### Rationale
- The PSMAD dataset has timestamps in milliseconds. The median-based computation (`1000.0 / median(diff(timestamps))`) is robust to occasional timing jitter.
- Storing the computed rate in filter params ensures the live system uses the exact same rate the filter was designed for.
- 37 Hz default matches empirical observation from the PSMAD dataset.
- The live ESP32 glove should operate at the same rate, but if it differs, the metadata makes this mismatch detectable.

---

## R6: Impact on Existing Feature Extraction

### Decision
No changes needed to `feature_extractors.py`. The existing functions (RMS, mean, std, skewness, kurtosis, FFT) operate on whatever signal they receive. Feeding them gravity-filtered signal instead of raw signal naturally produces gravity-free features.

### Rationale
- Feature extraction functions are signal-agnostic — they compute statistical properties of the input window regardless of what preprocessing has been applied.
- FFT tremor band extraction (3-12 Hz) will now correctly focus on tremor dynamics instead of being dominated by the DC gravity component.
- The `mean` feature, in particular, will become near-zero for motionless recordings (gravity removed), making it a much better indicator of actual tremor center offset.
