# Research: Live Inference Pipeline (Sliding Window)

**Branch**: `038-live-inference-pipeline` | **Date**: 2026-04-07

---

## Decision 1: Script File Location

**Decision**: `backend/live_glove_test.py` (at the root of the `backend/` directory)

**Rationale**: The script uses artifacts from two subdirectories of `backend/` — the ML model from `backend/ml_models/models/` and feature extractors from `backend/ml_data/utils/`. Placing it at `backend/` root mirrors how standalone batch scripts are organized in this repo (see `record_patient.py` at repo root). It stays inside `backend/` per the monorepo constitution, and `sys.path.insert(0, os.path.dirname(__file__))` makes all `ml_data` and `ml_models` imports resolve cleanly without the `backend.` prefix.

**Alternatives considered**:
- `backend/ml_models/scripts/live_glove_test.py` — alongside training scripts; rejected because it implies ML model management rather than hardware integration
- Repo root `live_glove_test.py` — like `record_patient.py`; rejected because the file directly depends on `backend/` internal structure (model path, import path)

---

## Decision 2: Sliding Window — deque vs Manual Array

**Decision**: `collections.deque(maxlen=100)`

**Rationale**: Python's `deque(maxlen=N)` automatically discards the oldest element when a new one is appended beyond capacity — no manual index tracking or clearing needed. Appending is O(1). Converting to numpy with `np.array(deque)` is O(N) but N=100 is negligible at 30Hz. The deque is modified only from the `on_message` MQTT callback; with `loop_forever()` the callback runs in the same thread, so thread safety is not a concern.

**Alternatives considered**:
- Circular numpy buffer with manual index — more complex, no benefit at 30Hz scale
- `np.roll()` on a fixed array — less readable, same O(N) overhead

---

## Decision 3: Feature Extraction Pipeline Reuse

**Decision**: Import and call `extract_features_all_axes` + `extract_fft_features_all_axes` directly from `backend/ml_data/utils/feature_extractors.py`

**Rationale**: The RF model was trained using these exact functions in `4_psmad_pipeline.py::extract_window_features()`. To guarantee zero feature divergence between training and live inference, the same code path must be used. Rewriting feature extraction inline would risk subtle differences (e.g., different skewness convention, different FFT normalization).

**Feature order** (must match training CSV column order):
1. `extract_features_all_axes(window, AXIS_NAMES)` → 30 features: `RMS_aX, mean_aX, std_aX, skewness_aX, kurtosis_aX, RMS_aY, ...` (5 × 6 axes)
2. `extract_fft_features_all_axes(window, AXIS_NAMES, ...)` → 12 features: `dominant_freq_aX, tremor_energy_aX, dominant_freq_aY, ...` (2 × 6 axes)
3. Combined: `{**time_features, **fft_features}` → `list(combined.values())` → 42-element array

This matches exactly how `build_output_dataframe()` in `4_psmad_pipeline.py` assembles the feature matrix.

**Alternatives considered**:
- Inline reimplementation — rejected: risk of divergence
- Using `extract_features_batch()` — designed for batch mode (multiple windows), overkill for single-window live inference

---

## Decision 4: Sampling Rate for FFT (30Hz vs 37Hz)

**Decision**: Use `sampling_rate_hz=30.0` for live inference from ESP32

**Rationale**: The FFT bin frequency axis is computed as `np.fft.rfftfreq(N, d=1/Fs)`. If `Fs` doesn't match the actual data rate, frequency values are scaled incorrectly. The PSMAD dataset had `Fs≈37Hz` (inferred from variable timestamps). The ESP32 targets `30Hz`. Using the correct rate ensures `dominant_freq` values are in real Hz units and `tremor_energy` captures energy in the correct 3–12Hz band.

**Impact analysis**: Both 30Hz and 37Hz have Nyquist frequency well above 12Hz (15Hz and 18.5Hz respectively), so the tremor band is fully captured at either rate. The absolute feature values will differ between training (37Hz) and live (30Hz) for the same motion, but the model has learned relative patterns — this is acceptable for proof-of-concept use. For production use, retraining on data collected at 30Hz would eliminate this systematic difference.

**Alternatives considered**:
- Use `37.0` to "match training" — incorrect: distorts actual frequency bins for 30Hz data, making the FFT features meaningless
- Make sampling rate a CLI argument — good extensibility option; included in `parse_args()` as `--sampling-rate`

---

## Decision 5: paho-mqtt Threading Model

**Decision**: Use `client.loop_forever()` (blocking main thread loop)

**Rationale**: `loop_forever()` runs the MQTT network loop in the main thread and dispatches `on_message` callbacks synchronously. Since our inference is fast (~5ms for 42-feature extraction + RF predict on a 100-sample window), there is no risk of blocking the next message. The alternative `loop_start()` (background thread) would require thread-safe access to the deque — unnecessary complexity for a single-threaded design.

**Thread safety note**: `deque.append()` is thread-safe in CPython (GIL). But since we use `loop_forever()` (single thread), no concurrent access occurs regardless.

**Alternatives considered**:
- `loop_start()` + inference in main thread — unnecessary complexity
- `asyncio` with `asyncio-mqtt` — overkill; paho's synchronous API is sufficient

---

## Decision 6: MQTT Connection Error Handling

**Decision**: Wrap `client.connect()` in try/except `ConnectionRefusedError`; exit with code 1 on failure

**Rationale**: If the broker is not running or unreachable, paho raises `ConnectionRefusedError` synchronously on `connect()`. We catch this and print a helpful error rather than letting Python dump a traceback. We do not implement automatic reconnection — this is a manual test tool, not a production daemon.

**Alternatives considered**:
- Implement reconnect with `on_disconnect` callback — overkill for a test script
- Let it crash — bad UX; confusing traceback

---

## Decision 7: No Warm-Up Message Throttling

**Decision**: Print every prediction once the window is full (30 predictions/second)

**Rationale**: The user explicitly requested 30Hz output — "the script will output a live prediction 30 times per second with every new MQTT message." Throttling would defeat the purpose. Console output at 30Hz is fast but manageable.

**Alternatives considered**:
- Print every Nth prediction (e.g., every 10th = 3Hz) — available as CLI option `--print-every N` for future use, but default is 1 (every prediction)
- Add timestamps to output — helpful; included in output format: `[HH:MM:SS.mmm] ⚠️ TREMOR DETECTED (1)`
