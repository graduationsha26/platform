# Implementation Plan: On-Device Edge AI Tremor Classification

**Branch**: `052-edge-ai-inference` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/052-edge-ai-inference/spec.md`

## Summary

Move the validated 3-class LightGBM tremor classifier (Non-Tremor=0, Tremor=1, Voluntary=2) from off-device backend serving onto the ESP32 glove firmware, so suppression can be driven locally and in real time. The classifier is **transpiled to a compact flat-array tree interpreter** (trees serialized from the trained `.pkl` into read-only C arrays + a small iterative traversal), and the 66-feature DSP pipeline is **re-implemented natively in C++** (causal biquad band-pass + 128-point radix-2 FFT for spectral peaks + per-window statistics over a sliding ring buffer). The model is **retrained at the device's native 100 Hz** so the device performs zero resampling. A new **classification task on Core 0** produces a decision every 100 ms, which **gates the existing PID suppression** through a smoothed state machine (hysteresis + sliding-window vote) so actuators never chatter at class boundaries. The off-device backend inference path is **retained as the authoritative source for persisted/clinical records**; the device path drives only local suppression. Parity between the Python reference and the C++ port is enforced by a host-side test harness before any firmware integration.

## Technical Context

**Primary surface**: `firmware/` (ESP32 C++, PlatformIO, Arduino-ESP32 framework) — new code for DSP, the tree interpreter, the classification task, and the suppression gate.
**Secondary surface**: `backend/ml_models/` (Python) — native-rate retrain + a model→C exporter + a host parity harness; the backend `inference`/feature definition realigns to the new native rate.
**Target hardware**: ESP32dev, dual-core Xtensa LX6 @ 240 MHz, single-precision hardware FPU; 4 MB flash (~3.2–3.5 MB free), 520 KB SRAM (~480 KB free). IMU: MPU6500 over SPI, 100 Hz ODR, ±2 g / ±250 °/s, 6 axes (aX,aY,aZ,gX,gY,gZ).
**Existing firmware tasks** (must not regress): SensorTask (Core 1, 100 Hz), ControlTask (Core 1, 200 Hz, sensor→actuation <70 ms hard budget), MqttTask (Core 0, 30 Hz). Core 1 saturated → classification goes on **Core 0**.
**DSP libraries**: esp-dsp (Espressif, Xtensa-optimized FFT/biquad) — primary candidate; arduinoFFT as fallback. *(Exact PlatformIO entry + API confirmed in research.md.)*
**Model transpilation**: flat-array tree interpreter generated from `LGBMClassifier.booster_.dump_model()`; m2cgen used only as a milestone-1 correctness oracle. *(Confirmed in research.md.)*
**Numeric type**: float32 throughout (hardware FPU); no fixed-point.
**Window/FFT**: 128-sample analysis window @ 100 Hz (1.28 s), 128-point radix-2 FFT, refreshed every 10 samples (100 ms). Reference Python feature extractor realigned to identical window/FFT length for exact parity.
**Filter**: causal IIR band-pass (cascaded biquads, single forward pass, streamed per-sample) — chosen over zero-phase `filtfilt` for O(1) streaming and trivial exact parity; the reference model is **retrained with the same causal filter**. `filtfilt`-over-window is the documented fallback if accuracy parity (SC-005) is not met.
**Performance goals**: decision refresh ≥10 Hz (≤100 ms, SC-002); one full window→features→decision cycle within the Core-0 budget without ControlTask missing its <70 ms deadline (SC-003); offline operation (SC-004).
**Accuracy goals**: edge per-window decisions agree with the retrained reference ≥95% and within 3 pts accuracy (SC-005); feature values within numerical tolerance (SC-006); retrained 100 Hz model retains macro precision comparable to the 66.67 Hz reference (~0.88).
**Footprint goals**: firmware+model within flash/RAM headroom; existing tasks meet deadlines (SC-007).
**Testing**: host-side Python↔C parity harness (features + tree outputs) before integration; on-device timing/footprint validation; pytest for the exporter/retrain on the backend side.
**Project Type**: monorepo (firmware/ + backend/).
**Constraints**: local development only; no Docker/CI/CD; secrets in `.env`/`config.h` (gitignored).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Work stays within `firmware/` and `backend/`; no new repos.
- [ ] **Tech Stack Immutability**: ⚠️ Adds firmware DSP dependency (esp-dsp) and a model→C exporter (LightGBM dump + optional m2cgen). Firmware C/C++ is constitutionally permitted, but these are new libraries → **VIOLATION, justified below**.
- [x] **Database Strategy**: No DB changes; backend remains on Supabase PostgreSQL.
- [x] **Authentication**: Unchanged (JWT/SimpleJWT); feature is device-local + backend training.
- [ ] **Security-First**: Firmware secrets remain in `config.h` (gitignored) per existing pattern; no new secrets. The trained `.pkl`/exported C arrays are model artifacts, not secrets. *(Compliant; flagged for awareness.)*
- [x] **Real-time Requirements**: Live tremor data still flows to the frontend via the existing Channels WebSocket from the backend; unchanged by this feature.
- [x] **MQTT Integration**: Existing MQTT telemetry unchanged; the device may additionally publish its on-device class over the same channel (no new transport).
- [ ] **AI Model Serving**: ⚠️ The constitution requires model inference **server-side via the Django `inference` app, never outside the backend**. This feature **runs inference on the device** → **VIOLATION, justified below** (this is the explicit purpose of the Edge AI pivot). Mitigated: the backend `inference` path is retained as the **authoritative record-of-truth**; the device runs a *derived* copy of the same model for local real-time suppression only.
- [x] **API Standards**: No new REST surface required by the MVP; if the device class is surfaced, it reuses existing REST/JSON snake_case conventions.
- [x] **Development Scope**: Local development only; firmware flashed via PlatformIO, no CI/CD.

**Result**: ⚠️ VIOLATIONS REQUIRE JUSTIFICATION (see Complexity Tracking). Recommend a constitution amendment ratifying on-device inference + firmware DSP/transpilation tooling for the Edge AI direction.

## Project Structure

### Documentation (this feature)

```text
specs/052-edge-ai-inference/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (on-device + exporter contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
firmware/
├── include/
│   ├── edge_features.h        # NEW — DSP + 66-feature API (ring buffer, biquad, FFT, stats)
│   ├── tremor_model.h         # NEW — generated flat-array tree interpreter (model arrays + traversal decl)
│   ├── classifier.h           # NEW — high-level classify(window)->{class, proba}
│   ├── suppression_gate.h     # NEW — smoothed gate state machine (hysteresis + vote)
│   └── config.h.example       # MODIFIED — edge classifier constants (window, hop, gate thresholds)
├── src/
│   ├── edge_features.cpp       # NEW — DSP/feature implementation
│   ├── tremor_model.cpp        # NEW — GENERATED model arrays + interpreter (do not hand-edit)
│   ├── classifier.cpp          # NEW — feature->interpreter->softmax->class
│   ├── suppression_gate.cpp    # NEW — gate logic consumed by ControlTask
│   ├── task_scheduler.cpp      # MODIFIED — add ClassificationTask (Core 0); ControlTask consults gate
│   └── pid_controller.cpp      # MODIFIED — engage/disengage driven by gate (control law unchanged)
└── platformio.ini             # MODIFIED — add esp-dsp dependency

backend/
├── ml_models/
│   ├── features_lgbm.py        # MODIFIED — native-rate (100 Hz) + 128-window/FFT, causal filter option
│   ├── train.py                # MODIFIED — retrain at native rate (pinned params)
│   ├── export_to_c.py          # NEW — dump LightGBM trees -> firmware/src/tremor_model.cpp/.h
│   └── parity_harness.py       # NEW — Python<->C feature & prediction parity check
└── tests/
    └── test_edge_parity.py     # NEW — pytest wrapper around the parity harness
```

**Structure Decision**: This is a **firmware-primary** feature with a backend tooling tail. New firmware modules implement DSP (`edge_features`), the transpiled model (`tremor_model`, generated), the classifier glue (`classifier`), and the smoothed gate (`suppression_gate`); `task_scheduler` and `pid_controller` are modified to add the Core-0 classification task and gate the control law. On the backend, `features_lgbm.py`/`train.py` realign to the native 100 Hz / 128-sample pipeline, a new `export_to_c.py` generates the device model, and a parity harness guarantees the C++ port matches the Python reference within tolerance before integration.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| On-device ML inference (vs constitution's backend-only `inference` app) | The entire purpose of the Edge AI pivot: closed-loop tremor suppression needs a local, network-independent decision within the <70 ms control budget; a backend round-trip cannot meet this latency or work offline. | Keeping inference backend-only was rejected because network latency + connectivity dependence make it unusable for real-time hardware suppression. Mitigation: backend `inference` stays authoritative for stored/clinical records. |
| New firmware libraries: esp-dsp (DSP) + LightGBM→C exporter (dump/m2cgen) | The 66-feature pipeline needs FFT + IIR filtering on-device; the model must become C. No existing firmware lib provides these. | Hand-writing an unoptimized FFT was rejected for performance/correctness risk; shipping the raw `.pkl` was rejected because the device cannot run Python/joblib. |
| Native-rate (100 Hz) retrain changing the canonical pipeline rate from 66.67 Hz | Eliminates on-device resampling (latency + complexity) and aligns the reference to the true sensor rate. | Decimating 100→66.67 Hz on-device was rejected as a needless non-integer resample stage on a real-time MCU. |
