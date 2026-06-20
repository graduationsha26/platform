# Feature Specification: Tremor Signal Filtering & Frequency Analysis

**Feature Branch**: `026-tremor-bandpass-fft`
**Created**: 2026-02-18
**Status**: Draft
**Input**: User description: "1.2 Filter — Band-Pass Filter (3-8 Hz) + FFT Amplitude Extraction"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tremor Signal Isolation via Band-Pass Filtering (Priority: P1)

A doctor wants to monitor a Parkinson's patient's tremor without interference from the patient's voluntary hand movements or sensor noise. The system continuously filters the raw six-axis sensor stream, passing only signals in the clinically established Parkinsonian tremor frequency range (3–8 Hz). Signals below 3 Hz (voluntary reaching, walking, postural adjustment) and above 8 Hz (electronic noise, vibration artifacts) are suppressed. The result is a clean tremor signal on all six axes, ready for further analysis.

**Why this priority**: Filtering is the prerequisite for all downstream tremor analysis. Without this isolation step, tremor metrics are contaminated by voluntary motion and noise, making them clinically meaningless. This is the foundational data-quality gate.

**Independent Test**: Can be fully tested by feeding synthetic signals (a 1 Hz sine wave, a 5 Hz sine wave, and a 20 Hz sine wave) into the filter and verifying that only the 5 Hz signal passes with minimal attenuation while the other two are strongly suppressed.

**Acceptance Scenarios**:

1. **Given** the system receives a steady 5 Hz sinusoidal signal on any sensor axis, **When** the band-pass filter processes it, **Then** the output amplitude is at least 90% of the input amplitude (≤1 dB loss).
2. **Given** the system receives a 1 Hz sinusoidal signal (voluntary movement simulation), **When** the band-pass filter processes it, **Then** the output amplitude is reduced to less than 10% of the input amplitude (≥20 dB attenuation).
3. **Given** the system receives a 15 Hz sinusoidal signal (noise simulation), **When** the band-pass filter processes it, **Then** the output amplitude is reduced to less than 10% of the input amplitude (≥20 dB attenuation).
4. **Given** the system receives a composite signal containing both 2 Hz and 6 Hz components, **When** the filter processes it, **Then** only the 6 Hz component is present in the output.
5. **Given** the glove is completely stationary, **When** the filter processes the near-zero sensor output, **Then** the filtered output remains near zero with no signal amplification.

---

### User Story 2 - Real-Time Tremor Frequency & Amplitude Extraction via FFT (Priority: P2)

A doctor reviewing a patient session wants to know the dominant tremor frequency and its intensity in real time. The system analyzes the filtered sensor signal using a frequency analysis algorithm, identifies the strongest frequency component within the 3–8 Hz band, and reports it as the patient's current tremor frequency. It also computes the amplitude of that dominant frequency as a tremor severity indicator. These metrics update continuously while the patient wears the glove and are made available for real-time dashboard display and for input into severity estimation models.

**Why this priority**: Frequency and amplitude extraction transform the filtered signal into interpretable clinical metrics. Without these metrics, the band-pass output is still raw waveform data that doctors cannot directly interpret. This story completes the clinical value of the signal processing pipeline.

**Independent Test**: Can be fully tested by feeding a known 5 Hz sine wave of known amplitude into the FFT stage and verifying that the reported dominant frequency is 5 Hz (±0.5 Hz) and the reported amplitude matches the input amplitude (±10%).

**Acceptance Scenarios**:

1. **Given** the filtered signal contains a dominant 5 Hz tremor component, **When** the FFT analysis completes, **Then** the reported dominant frequency is between 4.5 Hz and 5.5 Hz.
2. **Given** the filtered signal contains a tremor at known amplitude A, **When** the FFT analysis completes, **Then** the reported amplitude is within ±10% of A.
3. **Given** the filtered signal is essentially flat (no tremor present), **When** the FFT analysis completes, **Then** the system reports a "no tremor detected" state rather than a false frequency reading.
4. **Given** the glove is operating continuously, **When** the doctor views the dashboard, **Then** tremor frequency and amplitude metrics refresh at least once per second.
5. **Given** the filtered signal contains two tremor components at 4 Hz and 7 Hz with different amplitudes, **When** the FFT analysis completes, **Then** the system reports the frequency of the stronger component as the dominant frequency.

---

### Edge Cases

- What happens when the patient's hand is completely still? The system must report "no tremor" without generating spurious frequency readings from noise.
- What happens when the tremor frequency drifts over time (e.g., from 4 Hz to 6 Hz across a session)? The reported dominant frequency must track the drift, not lock onto the initial value.
- What happens at system startup (filter initialization)? The first few output samples may be affected by the filter's initialization transient; the system must wait for the filter to stabilize before reporting metrics.
- What happens when tremor amplitude is extremely high (sensor near saturation)? The system must still report a valid frequency even if amplitude accuracy degrades.
- What happens when multiple axes have different dominant frequencies? The system must handle per-axis reporting or select a representative axis without discarding valid cross-axis data.
- What happens when the 100 Hz data stream has a temporary gap (e.g., MQTT packet loss)? The filter must handle missing samples without producing large output spikes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST apply band-pass filtering to the frequency band 3–8 Hz on all six sensor axes (three accelerometer, three gyroscope).
- **FR-002**: The filter MUST attenuate signals below 3 Hz by at least 20 dB (voluntary movement rejection).
- **FR-003**: The filter MUST attenuate signals above 8 Hz by at least 20 dB (noise rejection).
- **FR-004**: The filter MUST pass signals within the 3–8 Hz band with no more than 1 dB of attenuation at the center of the passband.
- **FR-005**: The filter MUST operate in real-time, processing each new sensor sample as it arrives without introducing more than 200 ms of additional latency.
- **FR-006**: The system MUST compute a frequency analysis (FFT or equivalent) on the filtered sensor signal to identify the dominant tremor frequency within the 3–8 Hz band.
- **FR-007**: The system MUST extract the peak amplitude corresponding to the dominant tremor frequency.
- **FR-008**: The system MUST update tremor frequency and amplitude metrics at least once per second during continuous glove operation.
- **FR-009**: When the amplitude within the 3–8 Hz band is below a defined minimum threshold, the system MUST report a "no tremor detected" state rather than a spurious frequency reading.
- **FR-010**: Tremor frequency and amplitude metrics MUST be made available for downstream consumption by the real-time dashboard and severity estimation components.
- **FR-011**: The filter MUST handle the startup initialization period gracefully, suppressing output until the filter has reached steady-state operation.
- **FR-012**: The system MUST process all six sensor axes independently, maintaining separate filtered signals and frequency metrics per axis.

### Key Entities

- **Filtered Sensor Reading**: A processed version of the raw six-axis sensor reading after band-pass filtering. Retains the original timestamp and axis labels. Represents only the tremor-frequency component of motion.
- **Tremor Metrics**: A computed result derived from frequency analysis of the filtered signal. Contains: dominant tremor frequency (Hz), peak amplitude (in the same units as the filtered signal), detection status (tremor detected / no tremor), and timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When tested with synthetic single-frequency signals, signals at 5 Hz pass with less than 1 dB attenuation; signals at 1 Hz and 15 Hz are attenuated by at least 20 dB, verified through offline signal injection testing.
- **SC-002**: The dominant tremor frequency reported by the system is within ±0.5 Hz of the true frequency for steady-state sinusoidal tremor inputs.
- **SC-003**: Tremor amplitude is reported within ±10% of the true amplitude for known-amplitude test signals in the 3–8 Hz range.
- **SC-004**: Tremor metrics (frequency and amplitude) update at least once per second during continuous glove operation.
- **SC-005**: The total latency from raw sensor sample arrival to updated tremor metric availability is under 2 seconds under normal operating conditions.
- **SC-006**: The system correctly reports "no tremor detected" when presented with signals entirely outside the 3–8 Hz band or below the noise floor, with a false-positive rate below 5%.

## Assumptions

- The raw six-axis sensor stream is available at 100 Hz from the glove hardware (established by feature 025-imu-kalman-fusion).
- The 3–8 Hz range is the clinically validated frequency range for Parkinsonian resting tremor.
- A Butterworth filter design provides sufficient passband flatness and roll-off for this application; other filter types (Chebyshev, elliptic) may be evaluated during planning.
- The FFT window size will be chosen during planning to balance frequency resolution (minimum 0.5 Hz requires at least 2-second window at 100 Hz) against metric update latency.
- The "no tremor" detection threshold will be defined during planning based on sensor noise floor measurements.
- All six axes are filtered independently; cross-axis fusion for a single severity score is out of scope for this feature.
- The filtered signal and derived metrics are intended for use by downstream components (dashboard, severity models); persistence to a database is out of scope for this feature unless required by those consumers.

## Out of Scope

- Selecting or applying the tremor severity classification model (handled by existing ML inference pipeline).
- Displaying tremor metrics on the dashboard UI (a separate frontend feature).
- Adaptive filter tuning based on patient-specific tremor characteristics.
- Yaw axis estimation or magnetometer fusion (no magnetometer is used in the glove hardware).
- Tremor suppression or actuation commands sent back to the glove.
