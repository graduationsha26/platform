# Tasks: Train ML Models on PSMAD Feature Dataset

**Input**: Design documents from `/specs/037-train-ml-models/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅  
**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks grouped by user story. Each story modifies a different script and is independently runnable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Maps to user story from spec.md

---

## Phase 1: Setup

**Purpose**: Verify prerequisites before any script changes.

- [x] T001 Confirm `backend/ml_data/processed/ready_for_training_features.csv` exists and has 43 columns (run `py -c "import pandas as pd; df=pd.read_csv('backend/ml_data/processed/ready_for_training_features.csv'); print(df.shape, list(df.columns[-3:]))"` from repo root)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No shared infrastructure changes are needed — both training scripts are modified independently. This phase is intentionally empty; proceed directly to US1.

**⚠️ NOTE**: US1 (RF) and US2 (SVM) touch different files and can theoretically be done in parallel, but are sequenced P1 → P2 by priority. Complete US1 and run it successfully before starting US2.

---

## Phase 3: User Story 1 — Retrain Random Forest (Priority: P1) 🎯 MVP Start

**Goal**: Update `train_random_forest.py` to load 42-feature PSMAD data, train, save `rf_model_v1.pkl` + metrics, and delete old RF files.

**Independent Test**: Run `py backend/ml_models/scripts/train_random_forest.py` from repo root and verify: (1) `backend/ml_models/models/rf_model_v1.pkl` exists, (2) `backend/ml_models/rf_model_metrics_v1.json` exists with `feature_count: 42`, (3) old RF files are absent.

- [x] T002 [US1] Replace `--input-dir` CLI argument with `--input` in `backend/ml_models/scripts/train_random_forest.py`: change `parse_arguments()` so `--input` defaults to `'backend/ml_data/processed/ready_for_training_features.csv'` and remove `--output-dir` (hardcode output paths instead)
- [x] T003 [US1] Replace two-file data loading with single-CSV + stratified split in `backend/ml_models/scripts/train_random_forest.py`: add `from sklearn.model_selection import train_test_split` import, load `df = pd.read_csv(args.input)`, assert `len(df.columns) == 43` and `'label' in df.columns`, then split: `X_train, X_test, y_train, y_test = train_test_split(df.drop('label',axis=1).values, df['label'].values, test_size=0.2, random_state=args.random_state, stratify=df['label'].values)`
- [x] T004 [US1] Update `validate_data()` in `backend/ml_models/scripts/train_random_forest.py`: change both `X_train.shape[1] != 30` checks to `!= 42` and update the error messages to say "Expected 42 features"
- [x] T005 [US1] Update model name, output paths, and metadata in `backend/ml_models/scripts/train_random_forest.py`: (a) in `save_model()` call change `model_name="random_forest"` to `model_name="rf_model_v1"`, `output_dir` to `"backend/ml_models/models"`, (b) after `save_model()` write metrics JSON separately: `import json; metrics_path = "backend/ml_models/rf_model_metrics_v1.json"; json.dump(metadata, open(metrics_path,'w'), indent=2)`, (c) add `"feature_count": int(X_train.shape[1])` and `"dataset_source": os.path.basename(args.input)` to `training_info` dict passed to `create_metadata()`
- [x] T006 [US1] Add `cleanup_old_rf_files()` function to `backend/ml_models/scripts/train_random_forest.py`: delete the following files if they exist using `os.remove()` wrapped in `if os.path.exists()`: from `backend/ml_models/models/` — `random_forest.pkl`, `random_forest.json`, `rf_model.pkl`, `rf_model.json`; from `backend/ml_models/` — `random_forest.pkl`, `random_forest.json`, `rf_model.pkl`, `rf_model.json`, `rf_model_metrics.json`; log each deletion with `logger.info(f"Removed: {path}")`
- [x] T007 [US1] Wire `cleanup_old_rf_files()` into `main()` in `backend/ml_models/scripts/train_random_forest.py`: call it immediately after the `logger.info(f"Metadata saved: {metadata_path}")` line (Step 9 in main), so cleanup only runs after new files are confirmed written
- [x] T008 [US1] Run `py backend/ml_models/scripts/train_random_forest.py` from repo root and confirm: exit code 0, `backend/ml_models/models/rf_model_v1.pkl` created, `backend/ml_models/rf_model_metrics_v1.json` created, accuracy reported in console

**Checkpoint**: RF training complete. Verify `rf_model_metrics_v1.json` has `"feature_count": 42` and accuracy ≥ 85%.

---

## Phase 4: User Story 2 — Retrain SVM (Priority: P2)

**Goal**: Update `train_svm.py` to load 42-feature PSMAD data, add StandardScaler, train, save `svm_model_v1.pkl` + metrics, and delete old SVM files.

**Independent Test**: Run `py backend/ml_models/scripts/train_svm.py` from repo root and verify: (1) `backend/ml_models/models/svm_model_v1.pkl` exists, (2) `backend/ml_models/svm_model_metrics_v1.json` exists with `feature_count: 42`, (3) old SVM files are absent.

- [x] T009 [US2] Replace `--input-dir` CLI argument with `--input` in `backend/ml_models/scripts/train_svm.py`: same change as T002 — `--input` defaulting to `'backend/ml_data/processed/ready_for_training_features.csv'`
- [x] T010 [US2] Replace two-file data loading with single-CSV + stratified split in `backend/ml_models/scripts/train_svm.py`: same logic as T003 — `train_test_split` with `test_size=0.2, stratify=y`
- [x] T011 [US2] Add `StandardScaler` to `backend/ml_models/scripts/train_svm.py`: add `from sklearn.preprocessing import StandardScaler` import, then after the split: `scaler = StandardScaler(); X_train_scaled = scaler.fit_transform(X_train); X_test_scaled = scaler.transform(X_test)` — use `X_train_scaled` / `X_test_scaled` in `validate_data()` call, `grid_search.fit()`, and `evaluate_model()` (the unscaled `X_train`/`X_test` are only used for shape checks)
- [x] T012 [US2] Update `validate_data()` in `backend/ml_models/scripts/train_svm.py`: change both `!= 30` checks to `!= 42`
- [x] T013 [US2] Update model name, output paths, and metadata in `backend/ml_models/scripts/train_svm.py`: change `model_name="svm_rbf"` to `model_name="svm_model_v1"`, write metrics separately to `"backend/ml_models/svm_model_metrics_v1.json"`, add `"feature_count": int(X_train.shape[1])` and `"dataset_source"` to `training_info`
- [x] T014 [US2] Add `cleanup_old_svm_files()` function to `backend/ml_models/scripts/train_svm.py`: delete if they exist — from `backend/ml_models/models/`: `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`; from `backend/ml_models/`: `svm_model.pkl`, `svm_model.json`, `svm_rbf.pkl`, `svm_rbf.json`, `svm_model_metrics.json`
- [x] T015 [US2] Wire `cleanup_old_svm_files()` into `main()` in `backend/ml_models/scripts/train_svm.py`: call immediately after metrics JSON is confirmed written (after Step 9)
- [x] T016 [US2] Run `py backend/ml_models/scripts/train_svm.py` from repo root and confirm: exit code 0, `backend/ml_models/models/svm_model_v1.pkl` created, `backend/ml_models/svm_model_metrics_v1.json` created, accuracy reported in console

**Checkpoint**: SVM training complete. Verify `svm_model_metrics_v1.json` has `"feature_count": 42` and accuracy ≥ 75%.

---

## Phase 5: Polish & Verification

**Purpose**: Confirm all spec success criteria are met end-to-end.

- [x] T017 Spot-check both metrics JSON files: open `backend/ml_models/rf_model_metrics_v1.json` and `svm_model_metrics_v1.json`, confirm both have `"feature_count": 42`, `"accuracy"` > 0.75, `"confusion_matrix"` is a 2×2 list, and `"hyperparameters"` is non-empty
- [x] T018 Verify all superseded files are absent: confirm none of the following exist — `backend/ml_models/models/random_forest.pkl`, `rf_model.pkl`, `svm_model.pkl`, `svm_rbf.pkl` and their `.json` counterparts; `backend/ml_models/rf_model_metrics.json`, `svm_model_metrics.json`
- [x] T019 Validate model I/O: run quick sanity check from repo root — `py -c "import joblib, numpy as np; rf=joblib.load('backend/ml_models/models/rf_model_v1.pkl'); svm=joblib.load('backend/ml_models/models/svm_model_v1.pkl'); x=np.zeros((1,42)); print('RF:', rf.predict(x), '| SVM:', svm.predict(x))"` — both predictions should be 0 or 1 without error

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Empty — no blocking prerequisites beyond Phase 1
- **US1 (Phase 3)**: Depends on Phase 1 (CSV confirmed)
- **US2 (Phase 4)**: Depends on Phase 3 completing (same data, verify RF works before SVM)
- **Polish (Phase 5)**: Depends on US1 + US2 both complete

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 1
- **US2 (P2)**: Starts after US1 successfully runs (same input data, same pattern — validate pattern works on RF first)

### Within Each User Story

- T002→T003→T004→T005→T006→T007→T008 (sequential — each builds on previous change)
- T009→T010→T011→T012→T013→T014→T015→T016 (sequential — same pattern)

### Parallel Opportunities

- T002–T007 (US1 changes) and T009–T015 (US2 changes) are in different files — they **could** run in parallel, but sequential execution is recommended to validate the pattern works on RF first before replicating to SVM
- T017, T018, T019 (Polish) can run in parallel once T016 completes

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: Verify CSV
2. Complete Phase 3 T002–T007: Modify RF script
3. Run T008: Execute RF training
4. **STOP and VALIDATE**: confirm `rf_model_v1.pkl` exists and metrics look correct

### Full Delivery

1. Setup → US1 (RF works) → US2 (SVM same pattern) → Polish
2. Commit after T019 (all verification passes)

---

## Notes

- Run all `py` commands from the **repository root** (`C:\Data from HDD\Graduation Project\Platform\`), not from inside `backend/`
- The `validate_data()` function in each script receives the raw (unscaled) arrays for shape/NaN checks; only SVM uses scaled arrays for actual model training
- `model_io.py::save_model()` saves both `.pkl` AND `.json` to the same dir — we only use it for the `.pkl`; the metrics JSON is written separately to `backend/ml_models/` (one level up from `models/`)
- Commit after Phase 5 T019 passes successfully
