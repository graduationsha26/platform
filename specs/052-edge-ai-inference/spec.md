# Feature Specification: On-Device Edge AI Tremor Classification

**Feature Branch**: `052-edge-ai-inference`  
**Created**: 2026-06-20  
**Status**: Draft  
**Input**: User description: "Edge AI pivot — fix label inversion (Tremor=1, Non-Tremor=0), transpile the validated LightGBM tremor classifier to ESP32-compatible C++, translate the 66-feature DSP pipeline (band-pass + statistical/FFT features) into native C++ with FFT and a sliding-window buffer, and optimize live edge inference."

## Overview

Today the validated 3-class tremor classifier (Non-Tremor / Tremor / Voluntary) runs only off-device: the glove streams raw IMU telemetry to the backend, which runs the LightGBM model. This feature **moves classification onto the glove itself** so the suppression hardware can react to tremor locally, in real time, without depending on network/backend availability. It also **guarantees the tremor/non-tremor labeling is trustworthy and consistent** end-to-end, and **preserves the validated model's accuracy** when re-hosted at the edge.

## Clarifications

### Session 2026-06-20

- Q: Where does the "label inversion" actually exist? → A: **Investigation finding** — the training pipeline (`LGBM.ipynb` and `backend/ml_models/train.py`) already maps Control→0 (Non-Tremor), Parkinson→1 (Tremor), Voluntary→2. No structural inversion exists in label *assignment*. The spec therefore treats this as a **verify-and-lock requirement** (guarantee the convention is correct and identical across training, backend serving, the on-device model, and the suppression trigger), and an investigation requirement to locate any *behavioral* inversion (e.g., in the actuation trigger or observed live output). See FR-001..FR-004.
- Q: Sampling-rate strategy for the edge model? → A: **Retrain the model natively at the device's true sample rate** so the device performs zero on-device resampling; the off-device pipeline is aligned to the same rate. (Eliminates a resampling stage at the edge.)
- Q: How is the trained model converted to device-native form? → A: A **compact data-driven tree interpreter** (trees serialized to read-only flat arrays in device storage + a small traversal routine), not generated branch-per-node code.
- Q: Should the classifier gate the suppression? → A: **Yes — suppression engages only on class Tremor (1)** and disengages for Non-Tremor and Voluntary. The gate MUST be smoothed (state machine / hysteresis / debounce / sliding-window vote) so the actuators never rapidly toggle when the classifier momentarily oscillates at a class boundary.
- Q: Fate of the off-device backend inference path (FR-012)? → A: **Backend remains authoritative for persisted/clinical records**; the on-device classifier drives only local real-time suppression. Both paths coexist; the device path is not the system of record.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy, consistent tremor labeling (Priority: P1)

A patient wears the glove. When their hand is genuinely tremoring, every part of the system — the on-device decision, the backend record, and the suppression trigger — agrees that this is "Tremor" (class 1). When the hand is still or moving voluntarily, the system does not falsely call it tremor. The labeling convention (Non-Tremor = 0, Tremor = 1, Voluntary = 2) is identical wherever a class is interpreted, so no component silently inverts the meaning.

**Why this priority**: A classifier that mislabels tremor as non-tremor (or vice-versa) is worse than no classifier — it would either fail to suppress real tremor or fight the patient's intentional movement. Correct, consistent labels are the foundation every other story depends on.

**Independent Test**: Feed a known tremor recording and a known non-tremor recording through the full chain (training labels → saved model → on-device decision → suppression trigger) and confirm the class index and its human meaning match at every stage; confirm a tremor sample never resolves to "Non-Tremor" at any stage due to a mapping mismatch.

**Acceptance Scenarios**:

1. **Given** a labeled tremor recording, **When** it is classified by the re-hosted model, **Then** the result is class 1 ("Tremor") and the suppression trigger activates.
2. **Given** a labeled non-tremor (resting) recording, **When** it is classified, **Then** the result is class 0 ("Non-Tremor") and suppression does not activate.
3. **Given** the class-to-meaning mapping in any consumer (backend, device, trigger), **When** compared against the training mapping, **Then** they are identical with no inversion.

---

### User Story 2 - Real-time on-device classification (Priority: P1)

While the glove is worn, it continuously classifies the wearer's movement locally and updates its decision several times per second, without sending raw data to a server and waiting for an answer. The suppression subsystem consumes this local decision directly.

**Why this priority**: Low-latency, network-independent classification is the entire point of the edge pivot — it lets the device decide and act on tremor even with no connectivity, and removes the round-trip delay that makes server-side inference unsuitable for closed-loop suppression.

**Independent Test**: With the device disconnected from any backend/broker, apply tremor-like motion and confirm the device produces a tremor decision and updates it at the target cadence, observable via the device's existing telemetry/log channel.

**Acceptance Scenarios**:

1. **Given** the glove is powered and worn but offline, **When** the wearer's hand tremors, **Then** the device emits a "Tremor" decision within the target latency budget.
2. **Given** continuous wear, **When** movement changes from tremor to rest, **Then** the on-device decision updates to "Non-Tremor" within the target refresh interval.
3. **Given** the device is classifying, **When** a new decision is produced, **Then** it is available to the suppression subsystem without a network round-trip.

---

### User Story 3 - Accuracy parity with the validated model (Priority: P2)

The on-device classifier reaches the same conclusions as the validated reference model on the same inputs. Moving to the edge does not meaningfully degrade how well tremor is detected.

**Why this priority**: The off-device model was validated to ~0.88 macro precision. If the edge version diverges (because features are computed differently, or the model was shrunk too far), the clinical value is lost. Parity is what makes the edge version trustworthy, but it is P2 because a working, correctly-labeled edge path (US1+US2) is the deliverable MVP even before parity is fully tuned.

**Independent Test**: Run the same set of held-out recordings through both the reference model and the edge implementation and compare per-window decisions; agreement must meet the parity threshold defined in Success Criteria.

**Acceptance Scenarios**:

1. **Given** a held-out validation set, **When** classified by both the reference and edge implementations, **Then** their per-window decisions agree at or above the parity threshold.
2. **Given** the edge feature computation, **When** compared to the reference feature values on identical windows, **Then** the values match within a small numerical tolerance.

---

### User Story 4 - Fits the device with maintainable headroom (Priority: P3)

The classifier and its signal-processing code fit comfortably within the glove controller's limited memory and storage, leaving room for the existing firmware responsibilities (sensing, suppression control, communication) to keep running reliably.

**Why this priority**: An edge model that doesn't fit, or that starves the rest of the firmware of memory, can't ship. Headroom also keeps the system maintainable. It is P3 because it is a constraint to satisfy rather than user-visible behavior, and it is only meaningful once US1–US3 define what must fit.

**Independent Test**: Build the firmware with the edge classifier included and confirm storage and memory usage stay within defined headroom limits, and that existing firmware tasks continue to meet their timing.

**Acceptance Scenarios**:

1. **Given** the firmware including the edge classifier, **When** built, **Then** flash and RAM usage remain within the defined headroom budget.
2. **Given** the running firmware, **When** the classifier runs at the target cadence, **Then** existing real-time tasks (sensing, suppression, communication) still meet their deadlines.

---

### Edge Cases

- **Warm-up / insufficient data**: What does the device decide before it has collected a full analysis window of samples? (Expected: withhold a decision / report "not ready" rather than emit a garbage class.)
- **Sample-rate drift or dropped IMU samples**: How is a window handled when fewer samples than expected arrived in the last interval?
- **Out-of-range / saturated IMU readings**: How is a window containing implausible values treated before it influences a suppression decision?
- **Low-confidence prediction**: When no class clearly dominates, does the device act, hold the previous decision, or default to "do not suppress"?
- **Class meaning drift**: How is a future change to the class set or order prevented from silently inverting the suppression trigger?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a single canonical class mapping — Non-Tremor = 0, Tremor = 1, Voluntary = 2 — and apply it identically in training, backend serving, the on-device model, and the suppression trigger.
- **FR-002**: The system MUST verify, against the validated reference pipeline, that the canonical mapping is the one actually used (no inverted assignment) and record the verification result.
- **FR-003**: The system MUST locate and correct any *behavioral* inversion (e.g., a suppression trigger or output mapping that treats class 1 as non-tremor), if one exists, so that a confirmed tremor always drives suppression and only suppression.
- **FR-003a**: The suppression subsystem MUST be gated by the on-device class: active suppression engages only for class Tremor (1) and disengages for Non-Tremor (0) and Voluntary (2), replacing today's unconditional always-on suppression.
- **FR-003b**: The gate MUST smooth class transitions (via a state machine / hysteresis / debounce / sliding-window vote) so the actuators do not rapidly toggle when the classifier momentarily oscillates between classes at a boundary; engaging and disengaging suppression MUST be a safe, damped transition rather than an abrupt per-cycle switch.
- **FR-004**: The on-device classifier MUST classify movement into the three canonical classes from live IMU data without requiring a backend or network connection.
- **FR-005**: The on-device signal processing MUST reproduce the validated analysis pipeline — resampling/windowing, band-pass filtering, and the same statistical and frequency-domain features — so that on-device feature values match the reference within a defined numerical tolerance.
- **FR-006**: The on-device classifier MUST maintain a sliding analysis window over incoming IMU samples and refresh its decision at the defined cadence (not only once per full window).
- **FR-007**: The on-device decision MUST be made available to the suppression subsystem locally, without a network round-trip.
- **FR-008**: The system MUST keep the edge model's accuracy within a defined parity threshold of the validated reference model on held-out data.
- **FR-009**: The edge classifier and its signal-processing code MUST fit within the device's storage and memory headroom budget while the existing firmware responsibilities continue to operate.
- **FR-010**: The edge classifier MUST run at its target cadence without causing existing real-time firmware tasks (sensing, suppression control, communication) to miss their deadlines.
- **FR-011**: The system MUST handle the warm-up period and incomplete/implausible windows gracefully, withholding or defaulting the decision rather than emitting an unreliable class.
- **FR-012**: The system MUST keep a single source of truth for the feature definition and class mapping so the backend, the on-device implementation, and the model artifact cannot drift apart. The off-device backend inference path REMAINS authoritative for persisted/clinical records; the on-device classifier drives only local real-time suppression and is not the system of record. Both paths coexist and MUST use the same canonical mapping and feature definition.
- **FR-013**: The conversion of the trained model and feature pipeline into device-native form MUST be reproducible from the trained artifact (re-running the conversion on the same model yields an equivalent device implementation).

### Key Entities *(include if feature involves data)*

- **Canonical class mapping**: The authoritative correspondence between class index (0/1/2) and meaning (Non-Tremor / Tremor / Voluntary); referenced by every component that interprets a prediction.
- **Trained reference model**: The validated classifier artifact produced by the training pipeline; the source of truth for what the edge version must reproduce.
- **Edge classifier**: The device-native form of the trained model that runs on the glove controller.
- **Analysis window**: A fixed-duration span of recent IMU samples over which features are computed; advanced as a sliding buffer.
- **Feature vector**: The set of statistical and frequency-domain values computed per window that the classifier consumes; must be identical in definition across all hosts.
- **On-device decision**: The current class (and confidence) produced locally and consumed by the suppression subsystem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A confirmed tremor input resolves to "Tremor" (class 1) and a confirmed resting input resolves to "Non-Tremor" (class 0) at 100% of the verification checkpoints (training mapping, model output, suppression trigger) — i.e., zero inversions anywhere in the chain.
- **SC-002**: The device produces and refreshes a classification decision at least 10 times per second (≤100 ms between updates) under normal operation.
- **SC-003**: A full on-device classification cycle (window → features → decision) completes within the per-cycle time budget that allows the target refresh rate while the rest of the firmware meets its deadlines.
- **SC-004**: The device classifies with no network/backend connection present (verified offline).
- **SC-005**: The edge classifier's per-window decisions agree with the validated reference model on held-out data at least 95% of the time, and per-window decision accuracy stays within 3 percentage points of the reference model's accuracy.
- **SC-006**: On-device feature values match the reference feature values within a defined small numerical tolerance on identical windows.
- **SC-007**: The firmware including the edge classifier fits within the device's storage and memory with defined headroom remaining (storage and RAM both within budget) and all pre-existing real-time tasks still meet their deadlines.
- **SC-008**: The edge implementation is reproducible — regenerating it from the same trained model yields an equivalent device classifier.
- **SC-009**: When the classifier oscillates between classes at a boundary, the suppression gate does not toggle the actuators more than a defined safe rate (i.e., a sustained class change is required before suppression engages/disengages), verified by feeding alternating borderline windows and observing no per-cycle actuator chatter.

## Assumptions

- The validated LightGBM 3-class model from Feature 051 is the reference model to be re-hosted at the edge; its training labels (Control=0/Non-Tremor, Parkinson=1/Tremor, Voluntary=2) are correct and are the canonical mapping.
- The glove controller is the existing ESP32-class device already running the sensing and suppression firmware; the edge classifier is added to that firmware rather than to new hardware.
- The IMU already sampled by the firmware provides the same 6 axes (3-axis accelerometer + 3-axis gyroscope) used by the reference feature pipeline.
- "Real-time" for suppression means decisions refreshed on the order of 100 ms; this matches the existing off-device live-validation cadence.
- Reducing model size (e.g., fewer trees / shallower depth) is acceptable **only** insofar as it stays within the accuracy parity threshold (SC-005); accuracy parity takes precedence over maximal size reduction.
- The model is **retrained at the device's native sample rate** so the device does no resampling; the off-device pipeline is realigned to the same rate. The previously chosen 66.67 Hz was an artifact of the source recordings, not the live sensor rate.
- Suppression gating replaces the firmware's current unconditional always-on damping; the existing PID control law itself is unchanged — only *whether* it is engaged becomes class-driven (with smoothing).
- The backend training and serving pipeline from Feature 051 remains the place where the model is trained; this feature adds the edge target, it does not change how the model is trained (beyond locking the label convention).
