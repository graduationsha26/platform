# Tasks: PSMAD Dataset Preprocessing Pipeline

**Input**: Design documents from `/specs/036-psmad-data-prep/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅  
**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks grouped by user story. Each phase is independently deliverable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Maps to user story from spec.md

---

## Phase 1: Setup

**Purpose**: Create the output directory and document the new dependency.

- [x] T001 Create output directory `backend/ml_data/processed/` if it does not exist (can be created via `os.makedirs(..., exist_ok=True)` in the script, but ensure parent path `backend/ml_data/` exists)
- [x] T002 Add `openpyxl` to the project's Python dependencies so `pandas.read_excel()` can parse `AdditionalData.xlsx` — document in `backend/requirements.txt` (or equivalent dependency file in `backend/`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the pipeline script skeleton with CLI arguments and constants. All user story phases add functions into this file.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Create `backend/ml_data/scripts/4_psmad_pipeline.py` with: `argparse` CLI accepting `--parkinson-dir`, `--control-dir`, `--metadata`, `--output` (with sensible defaults pointing to `DataParkinson/` at repo root and `backend/ml_data/processed/ready_for_training_features.csv`), a `main()` function body that is a stub calling placeholder functions, and `if __name__ == "__main__": main()` guard
- [x] T004 Define all pipeline constants at the top of `backend/ml_data/scripts/4_psmad_pipeline.py`: `WINDOW_SIZE = 100`, `AXIS_NAMES = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`, `TREMOR_BAND_LOW_HZ = 3.0`, `TREMOR_BAND_HIGH_HZ = 12.0`, `COLUMN_RENAME_MAP = {'T': 'Timestamp', 'AX': 'aX', 'AY': 'aY', 'AZ': 'aZ', 'GX': 'gX', 'GY': 'gY', 'GZ': 'gZ'}`
- [x] T005 Add sys.path append at top of `backend/ml_data/scripts/4_psmad_pipeline.py` so utils imports work: `sys.path.append(str(Path(__file__).parent.parent))`, then import `from utils.windowing import create_windows`, `from utils.feature_extractors import extract_features_all_axes, get_feature_names`

**Checkpoint**: `python backend/ml_data/scripts/4_psmad_pipeline.py --help` should print usage without errors.

---

## Phase 3: User Story 1 — Filter and Format-Align PSMAD Raw Data (Priority: P1) 🎯 MVP Start

**Goal**: Load valid recordings from both PSMAD group folders, skip functional validation files, and produce column-renamed DataFrames ready for windowing.

**Independent Test**: Run only the loading phase on a small subset and verify: (1) files ending in `00.csv` are absent from the loaded set, (2) every loaded DataFrame has exactly the columns `Timestamp, aX, aY, aZ, gX, gY, gZ`, (3) the `sampling_rate_hz` attribute computed from Timestamp median diff is a finite positive float (~37 Hz).

- [x] T006 [US1] Implement `load_metadata(metadata_path)` in `backend/ml_data/scripts/4_psmad_pipeline.py`: reads `AdditionalData.xlsx` with `pandas.read_excel()`, prints participant count to stdout, and returns the DataFrame (used as a reference/log only — labels come from folders)
- [x] T007 [US1] Implement `discover_recordings(folder_path, label)` in `backend/ml_data/scripts/4_psmad_pipeline.py`: uses `pathlib.Path(folder_path).glob('*.csv')` to find all CSV files, filters out any file whose stem ends with `'00'` (e.g. `ID01010100` → last two chars of stem == `'00'`), logs count of skipped and valid files, returns list of `(path, label)` tuples
- [x] T008 [US1] Implement `load_recording(filepath)` in `backend/ml_data/scripts/4_psmad_pipeline.py`: reads CSV with `pd.read_csv()`, renames columns using `COLUMN_RENAME_MAP` (`df.rename(columns=COLUMN_RENAME_MAP, inplace=True)`), computes `sampling_rate_hz = 1000.0 / df['Timestamp'].diff().dropna().median()` (T column is in milliseconds), and returns `(df, sampling_rate_hz)`
- [x] T009 [US1] Wire T006, T007, T008 into `main()` in `backend/ml_data/scripts/4_psmad_pipeline.py`: call `load_metadata()`, call `discover_recordings()` for each group, iterate valid recordings calling `load_recording()` for each, accumulate list of `(df, sampling_rate_hz, label)` tuples

**Checkpoint**: After T009, add a temporary `print(f"Loaded {len(recordings)} recordings")` to verify ~108 files load without column errors.

---

## Phase 4: User Story 2 — Segment Data into Fixed-Size Windows (Priority: P2)

**Goal**: Slice each loaded recording into non-overlapping 100-record windows. Recordings with fewer than 100 samples are skipped with a warning.

**Independent Test**: Pass a synthetic DataFrame of 250 rows through the windowing step and verify exactly 2 windows are produced (rows 0–99, 100–199) and the 50-row remainder is discarded.

- [x] T010 [US2] Implement `window_recording(df, sampling_rate_hz, label, window_size)` in `backend/ml_data/scripts/4_psmad_pipeline.py`: extract the 6 sensor axis columns only (`df[AXIS_NAMES].values`), check `len(data) < window_size` and if so log a warning and return empty list, otherwise call `create_windows(data, window_size=window_size, stride=window_size)` (stride == window_size = non-overlapping), return list of `(window_array, label, sampling_rate_hz)` tuples
- [x] T011 [US2] Wire T010 into `main()` in `backend/ml_data/scripts/4_psmad_pipeline.py`: replace the recording accumulator with a windows accumulator — for each recording call `window_recording()` and extend the windows list, log total window count per group after all recordings are processed

**Checkpoint**: Log output should show ~237 Control windows and ~87 Parkinson windows (exact counts vary by recording length).

---

## Phase 5: User Story 3 — Extract Time-Domain and Frequency-Domain Features (Priority: P3)

**Goal**: Compute 30 time-domain + 12 FFT tremor-band features for every window, producing a fixed-length numeric feature vector per window.

**Independent Test**: Pass a single 100-row, 6-column numpy array through both extractors and verify the combined dict has exactly 42 keys, all values are finite floats, and `tremor_energy_*` keys are non-negative.

- [x] T012 [P] [US3] Add `extract_fft_features_single_axis(window, sampling_rate_hz, low_hz=3.0, high_hz=12.0)` to `backend/ml_data/utils/feature_extractors.py`: compute `np.fft.rfft(window)`, get `freqs = np.fft.rfftfreq(N, d=1.0/sampling_rate_hz)`, create `band_mask = (freqs >= low_hz) & (freqs <= high_hz)`, if no bins in band return `{'dominant_freq': 0.0, 'tremor_energy': 0.0}`, otherwise return `{'dominant_freq': float(band_freqs[np.argmax(band_magnitudes)]), 'tremor_energy': float(np.sum(np.abs(fft_vals[band_mask])**2))}`
- [x] T013 [P] [US3] Add `extract_fft_features_all_axes(window, axis_names, sampling_rate_hz, low_hz=3.0, high_hz=12.0)` to `backend/ml_data/utils/feature_extractors.py`: loop over axes (same pattern as existing `extract_features_all_axes()`), call `extract_fft_features_single_axis()` per axis, prefix keys as `dominant_freq_{axis_name}` and `tremor_energy_{axis_name}`, return combined dict
- [x] T014 [US3] Add `get_fft_feature_names(axis_names)` to `backend/ml_data/utils/feature_extractors.py`: return list in order `['dominant_freq_aX', 'tremor_energy_aX', 'dominant_freq_aY', ...]` (2 features × 6 axes = 12 names), following the same pattern as existing `get_feature_names()`
- [x] T015 [US3] Update import in `backend/ml_data/scripts/4_psmad_pipeline.py` to also import `extract_fft_features_all_axes` and `get_fft_feature_names` from `utils.feature_extractors`
- [x] T016 [US3] Implement `extract_window_features(window, sampling_rate_hz, axis_names)` in `backend/ml_data/scripts/4_psmad_pipeline.py`: call `extract_features_all_axes(window, axis_names)` for time-domain features, call `extract_fft_features_all_axes(window, axis_names, sampling_rate_hz)` for FFT features, merge both dicts into one combined feature dict and return it
- [x] T017 [US3] Wire T016 into `main()` in `backend/ml_data/scripts/4_psmad_pipeline.py`: for each `(window_array, label, sampling_rate_hz)` in the windows list, call `extract_window_features()`, add `'label': label` to the feature dict, append to a rows list

**Checkpoint**: After T017, `print(len(rows[0]))` should show `43` (42 feature keys + `label`).

---

## Phase 6: User Story 4 — Compile and Save Final Training-Ready CSV (Priority: P1)

**Goal**: Assemble all feature rows into a DataFrame, validate for NaN/Inf, and write `ready_for_training_features.csv` to `backend/ml_data/processed/`.

**Independent Test**: After running the full pipeline, open the output CSV and verify: file exists and is non-empty, exactly 43 columns present (last column is `label`), `label` column contains only 0 and 1, no NaN or Inf values in any cell, row count > 0.

- [x] T018 [US4] Implement output assembly in `backend/ml_data/scripts/4_psmad_pipeline.py`: build `pd.DataFrame(rows)`, enforce column order using `time_cols = get_feature_names(AXIS_NAMES)` + `fft_cols = get_fft_feature_names(AXIS_NAMES)` + `['label']`, reorder with `df = df[time_cols + fft_cols + ['label']]`, cast label column to int
- [x] T019 [US4] Implement output validation in `backend/ml_data/scripts/4_psmad_pipeline.py`: assert `not df.isnull().any().any()` (no NaN), assert `not np.isinf(df.select_dtypes(include=np.number).values).any()` (no Inf), assert `set(df['label'].unique()).issubset({0, 1})` (valid labels), assert `len(df.columns) == 43` (correct column count) — raise `ValueError` with descriptive message if any assertion fails
- [x] T020 [US4] Implement file save in `backend/ml_data/scripts/4_psmad_pipeline.py`: call `os.makedirs(output_dir, exist_ok=True)`, call `df.to_csv(output_path, index=False)`, then print the completion summary report: total files processed, total windows generated, label distribution (count per class), total features per window, output file path and size in KB

**Checkpoint**: At this point the full pipeline should be runnable end-to-end.

---

## Phase 7: Polish & Verification

**Purpose**: End-to-end pipeline execution, output verification, and cleanup.

- [x] T021 Wire all pipeline phases into the correct call order in `main()` of `backend/ml_data/scripts/4_psmad_pipeline.py`: `load_metadata` → `discover_recordings` (both groups) → loop `load_recording` → loop `window_recording` → loop `extract_window_features` → `assemble_output` → `validate_output` → `save_output`
- [x] T022 Run the full pipeline end-to-end from `backend/ml_data/scripts/`: `python 4_psmad_pipeline.py` and confirm `backend/ml_data/processed/ready_for_training_features.csv` is created, is non-empty, has 43 columns, and the terminal shows the completion summary with file count, window count, and label distribution
- [x] T023 [P] Open `ready_for_training_features.csv` and spot-check: confirm no NaN/Inf values, confirm `label` column has both 0s and 1s, confirm column names match `get_feature_names(AXIS_NAMES) + get_fft_feature_names(AXIS_NAMES) + ['label']`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story phases
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 3 (needs loaded recordings)
- **US3 (Phase 5)**: T012 and T013 [P] can start after Phase 2; T015–T017 depend on T012–T014
- **US4 (Phase 6)**: Depends on Phase 5 completion
- **Polish (Phase 7)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational
- **US2 (P2)**: Depends on US1 (needs loaded DataFrames)
- **US3 (P3)**: FFT helper functions (T012, T013) can start after Foundational in parallel with US1/US2; pipeline integration (T015–T017) depends on US2 completion
- **US4 (P1)**: Depends on US3 completion

### Within Each User Story

- Functions can be implemented and tested individually before wiring into `main()`
- Wire each function into `main()` only after it is verified standalone
- Core function before pipeline integration

### Parallel Opportunities

- **T012 and T013** (FFT functions in `feature_extractors.py`) can run in parallel with each other and with US1/US2 tasks — different files
- **T022 and T023** (final verification) can run independently once T021 completes
- All tasks within the `feature_extractors.py` extension (T012, T013, T014) are in a different file from `4_psmad_pipeline.py` — can be developed in parallel with pipeline skeleton tasks

---

## Parallel Example: User Story 3 (Feature Extraction)

```bash
# After Phase 2 (Foundational) is complete, these can run in parallel:
Task T012: "Add extract_fft_features_single_axis() to backend/ml_data/utils/feature_extractors.py"
Task T013: "Add extract_fft_features_all_axes() to backend/ml_data/utils/feature_extractors.py"

# T014 depends on T012+T013, T015 depends on T014
```

---

## Implementation Strategy

### MVP First (US1 + US4 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (script skeleton + constants)
3. Complete Phase 3: US1 (load, filter, rename) — verify ~108 files load correctly
4. Skip to Phase 6: US4 (output assembly stub) to confirm end-to-end plumbing works
5. **STOP and VALIDATE**: confirm script runs without error before adding windowing/features

### Full Incremental Delivery

1. Setup → Foundational → US1 (loading works) → commit
2. Add US2 (windowing) → verify window counts → commit
3. Add US3 FFT helpers → integrate into pipeline → verify 42 features per row → commit
4. Add US4 (output CSV) → run end-to-end → verify `ready_for_training_features.csv` → commit

---

## Notes

- [P] tasks = different files or no shared dependencies — safe to parallelize
- The entire feature is a single Python script + small extension to `feature_extractors.py`
- All existing `ml_data/` scripts (`1_preprocess.py`, `2_feature_engineering.py`, `run_all.py`) are untouched
- The `windowing.py` file is used as-is with `stride=WINDOW_SIZE` — no modification needed
- Folder names use Unicode characters: Control Group uses regular hyphen, Parkinson's Group uses curly apostrophe (`'`) — use `pathlib` or `os.fspath` to handle paths robustly rather than hardcoding strings
- Commit after Phase 7 T022 passes successfully
