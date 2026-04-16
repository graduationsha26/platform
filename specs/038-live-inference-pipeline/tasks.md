# Tasks: Live Inference Pipeline (Sliding Window)

**Input**: Design documents from `/specs/038-live-inference-pipeline/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅  
**Tests**: Not requested — no test tasks generated.

**Organization**: Single user story (US1). All tasks create or modify `backend/live_glove_test.py` sequentially.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Maps to user story from spec.md

---

## Phase 1: Setup

**Purpose**: Verify prerequisites before writing the script.

- [x] T001 Confirm `backend/ml_models/models/rf_model_v1.pkl` exists and loads correctly (run `py -c "import joblib; m=joblib.load('backend/ml_models/models/rf_model_v1.pkl'); print('n_features_in_:', m.n_features_in_)"` from repo root — expect `n_features_in_: 42`)
- [x] T002 Confirm `paho-mqtt` is installed (run `py -c "import paho.mqtt.client; print('paho-mqtt OK')"` from repo root)
- [x] T003 Confirm `feature_extractors.py` is importable from `backend/` (run `py -c "import sys; sys.path.insert(0,'backend'); from ml_data.utils.feature_extractors import extract_features_all_axes, extract_fft_features_all_axes; print('feature_extractors OK')"` from repo root)

---

## Phase 2: Foundational

**Purpose**: No shared infrastructure needed — proceeds directly to US1.

*(Empty — no blocking prerequisites beyond Phase 1)*

---

## Phase 3: User Story 1 — Create Live Inference Script (Priority: P1) 🎯 MVP

**Goal**: Create `backend/live_glove_test.py` that subscribes to MQTT, maintains a 100-sample sliding window, extracts 42 features, and prints TREMOR/NORMAL at 30Hz.

**Independent Test**: Run `py backend/live_glove_test.py --help` (expect usage message, exit 0). With live hardware: connect ESP32, run script, verify predictions print at ~30Hz after ~3.3s warm-up. Without hardware: verify model loads and MQTT connection error is handled gracefully.

- [x] T004 [US1] Create `backend/live_glove_test.py` with module docstring, `import` block (os, sys, json, argparse, time, collections.deque, numpy, joblib, paho.mqtt.client, datetime), and sys.path setup: `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` then `from ml_data.utils.feature_extractors import extract_features_all_axes, extract_fft_features_all_axes`
- [x] T005 [US1] Add constants block to `backend/live_glove_test.py`: `AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`, `WINDOW_SIZE = 100`, `TREMOR_BAND_LOW_HZ = 3.0`, `TREMOR_BAND_HIGH_HZ = 12.0`, and logging setup: `logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s'); logger = logging.getLogger(__name__)`
- [x] T006 [US1] Add `parse_args()` function to `backend/live_glove_test.py` with these arguments: `--broker` (default `'192.168.137.1'`), `--port` (default `1883`, type int), `--topic` (default `'tremo/sensors/+'`), `--model` (default `None`, optional override for model path), `--sampling-rate` (default `30.0`, type float, help `'Sensor sampling rate in Hz (default: 30.0 for ESP32)'`)
- [x] T007 [US1] Add model loading block to `main()` in `backend/live_glove_test.py`: resolve `MODEL_PATH` as `args.model if args.model else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models', 'models', 'rf_model_v1.pkl')`; wrap `joblib.load(MODEL_PATH)` in try/except `FileNotFoundError` — on error log `[ERROR] Model file not found: {MODEL_PATH}` and `sys.exit(1)`; on success log `[OK] Model loaded: {MODEL_PATH} (n_features_in_={model.n_features_in_})`
- [x] T008 [US1] Add sliding window deque to `main()` in `backend/live_glove_test.py`: `window = deque(maxlen=WINDOW_SIZE)` and log `[INFO] Sliding window: {WINDOW_SIZE} samples @ {args.sampling_rate}Hz (~{WINDOW_SIZE/args.sampling_rate:.1f}s warm-up)`
- [x] T009 [US1] Add `on_connect(client, userdata, flags, rc)` callback to `backend/live_glove_test.py`: if `rc == 0` log `[OK] Connected to {userdata['broker']}:{userdata['port']}` and call `client.subscribe(userdata['topic'])`; log `[OK] Subscribed to {userdata['topic']}`; log `[INFO] Waiting for {WINDOW_SIZE} samples... Press Ctrl+C to stop`; else log `[ERROR] MQTT connection failed with code {rc}` and `sys.exit(1)`
- [x] T010 [US1] Add `on_message(client, userdata, msg)` callback to `backend/live_glove_test.py` with: (a) JSON parse in try/except `(json.JSONDecodeError, KeyError, ValueError)` — on exception log `[WARN] Skipping malformed message: {e}` and return; (b) extract `row = [float(data['aX']), float(data['aY']), float(data['aZ']), float(data['gX']), float(data['gY']), float(data['gZ'])]` and `window.append(row)`; (c) if `len(window) < WINDOW_SIZE: return` (window still filling — no prediction yet)
- [x] T011 [US1] Add feature extraction and prediction block inside `on_message()` in `backend/live_glove_test.py` (runs only when `len(window) == WINDOW_SIZE`): (a) `win_array = np.array(window)` → shape (100, 6); (b) `time_feats = extract_features_all_axes(win_array, AXIS_NAMES)`; (c) `fft_feats = extract_fft_features_all_axes(win_array, AXIS_NAMES, sampling_rate_hz=userdata['sampling_rate'], low_hz=TREMOR_BAND_LOW_HZ, high_hz=TREMOR_BAND_HIGH_HZ)`; (d) `feature_vector = np.array(list(time_feats.values()) + list(fft_feats.values())).reshape(1, -1)` — assert shape is (1, 42); (e) `pred = model.predict(feature_vector)[0]`; (f) `ts = datetime.now().strftime('%H:%M:%S.%f')[:12]`; (g) print `f"[{ts}] ⚠️  TREMOR DETECTED (1)"` if pred==1 else `f"[{ts}] ✅  NORMAL (0)"` — use `model` from closure via `userdata['model']`
- [x] T012 [US1] Add MQTT client setup and `main()` wiring in `backend/live_glove_test.py`: create `client = mqtt.Client(userdata={'broker': args.broker, 'port': args.port, 'topic': args.topic, 'sampling_rate': args.sampling_rate, 'model': model})`; assign `client.on_connect = on_connect` and `client.on_message = on_message`; wrap `client.connect(args.broker, args.port, keepalive=60)` in try/except `(ConnectionRefusedError, OSError)` — on error log `[ERROR] Cannot connect to {args.broker}:{args.port} — is the broker running?` and `sys.exit(1)`; then call `client.loop_forever()` wrapped in `try/except KeyboardInterrupt` — on interrupt log `[INFO] Stopping live inference. Goodbye.`
- [x] T013 [US1] Add `if __name__ == '__main__': args = parse_args(); main(args)` entrypoint to `backend/live_glove_test.py`
- [x] T014 [US1] Run `py backend/live_glove_test.py --help` from repo root and confirm: exit code 0, usage message shows `--broker`, `--port`, `--topic`, `--model`, `--sampling-rate`

---

## Phase 4: Polish & Verification

**Purpose**: Confirm correct behavior under normal and error conditions.

- [x] T015 Test model-not-found error: temporarily rename `backend/ml_models/models/rf_model_v1.pkl` to `rf_model_v1.pkl.bak`, run `py backend/live_glove_test.py`, confirm `[ERROR] Model file not found` is printed and exit code is 1, then rename back
- [x] T016 Test broker-unreachable error: run `py backend/live_glove_test.py --broker 127.0.0.1 --port 9999` (no broker on that port), confirm `[ERROR] Cannot connect` is printed and process exits cleanly within 5 seconds
- [x] T017 Verify feature extraction consistency: run `py -c "import sys; sys.path.insert(0,'backend'); import numpy as np; from ml_data.utils.feature_extractors import extract_features_all_axes, extract_fft_features_all_axes; win=np.zeros((100,6)); t=extract_features_all_axes(win,['aX','aY','aZ','gX','gY','gZ']); f=extract_fft_features_all_axes(win,['aX','aY','aZ','gX','gY','gZ'],sampling_rate_hz=30.0); v=list(t.values())+list(f.values()); import joblib; m=joblib.load('backend/ml_models/models/rf_model_v1.pkl'); print('features:', len(v), '| pred:', m.predict([v]))"` from repo root — expect `features: 42` and prediction `[0]` or `[1]` without error

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Empty — no blocking prerequisites
- **US1 (Phase 3)**: Depends on Phase 1 (prerequisites confirmed)
- **Polish (Phase 4)**: Depends on US1 complete (T013)

### Within User Story 1

- T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 (sequential — each builds on the previous in the same file)

### Parallel Opportunities

- T001, T002, T003 (Setup) are independent — run in parallel
- T015, T016, T017 (Polish) are independent — run in parallel
- All US1 tasks (T004–T013) are sequential — same file

---

## Implementation Strategy

### MVP (minimum to verify the pipeline works)

1. Complete Phase 1 (T001–T003)
2. Complete T004–T013 (full script)
3. Run T014 (`--help` smoke test)
4. **STOP and test with live hardware** or MQTT simulator

### Full Verification

1. Setup → US1 script → `--help` test → broker-unreachable test → model-not-found test → feature consistency check
2. Connect ESP32 and verify live predictions at 30Hz
3. Commit after T017 passes

---

## Notes

- Run all `py` commands from the **repository root** (`C:\Data from HDD\Graduation Project\Platform\`), not from inside `backend/`
- The `model` object is passed to callbacks via `userdata` dict — this avoids global variables and makes the script testable
- `on_message` uses `len(window) < WINDOW_SIZE: return` to silently skip predictions during warm-up — no log spam for 100 initial messages
- Feature extraction is always done on the FULL deque (100 samples) — the deque auto-slides, so this is always the most recent 100 samples
- T011 includes an assert on feature vector shape: if `feature_vector.shape[1] != 42`, something went wrong with imports or feature extraction — better to fail loudly than silently produce wrong predictions
