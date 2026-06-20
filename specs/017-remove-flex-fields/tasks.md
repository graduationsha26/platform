# Tasks: Remove Flex Fields from BiometricReading

**Input**: Design documents from `/specs/017-remove-flex-fields/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.
- **US1** (P1): Clean Biometric Data Model — model code contains no flex fields
- **US2** (P2): Safe Schema Migration — database schema updated atomically

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths are relative to the repository root

---

## Phase 1: Setup (Pre-flight Audit)

**Purpose**: Confirm baseline state before making any changes

- [X] T001 Audit all files in `backend/` for any existing references to `flex_1`, `flex_2`, `flex_3`, `flex_4`, or `flex_5` (expected: zero matches) — use `grep -r "flex_[1-5]" backend/`

---

## Phase 2: Foundational (BiometricReading Model Creation)

**Purpose**: Create the BiometricReading model as the "before state" that this feature cleans up — **MUST complete before US1 and US2 begin**

**⚠️ CRITICAL**: Both user stories depend on the BiometricReading model and its initial migration existing

- [X] T002 Add `BiometricReading` Django model class to `backend/biometrics/models.py` with fields: `patient` (ForeignKey → patients.Patient, CASCADE), `timestamp` (DateTimeField), `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` (FloatFields), `flex_1`, `flex_2`, `flex_3`, `flex_4`, `flex_5` (FloatFields), and Meta: `db_table = 'biometric_readings'`, `ordering = ['-timestamp']`, indexes on `['patient', 'timestamp']` and `['timestamp']`
- [X] T003 Generate Django migration for BiometricReading model creation: run `python manage.py makemigrations biometrics --name add_biometricreading` in `backend/` — verify file created at `backend/biometrics/migrations/0002_add_biometricreading.py`

**Checkpoint**: `BiometricReading` model class exists in `backend/biometrics/models.py` and migration `0002` exists in `backend/biometrics/migrations/` — US1 and US2 can now proceed

---

## Phase 3: User Story 1 — Clean Biometric Data Model (Priority: P1) 🎯 MVP

**Goal**: BiometricReading model code contains no flex_1 through flex_5 fields

**Independent Test**: `grep -n "flex_" backend/biometrics/models.py` returns zero matches; `BiometricReading` class defines exactly 9 fields (id auto, patient, timestamp, aX, aY, aZ, gX, gY, gZ)

### Implementation for User Story 1

- [X] T004 [US1] Remove `flex_1`, `flex_2`, `flex_3`, `flex_4`, `flex_5` FloatField definitions from the `BiometricReading` class in `backend/biometrics/models.py` — the class body should retain only `patient`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` and the `Meta` inner class

**Checkpoint**: `BiometricReading` in `backend/biometrics/models.py` has no flex fields — User Story 1 is independently verifiable via grep

---

## Phase 4: User Story 2 — Safe Schema Migration (Priority: P2)

**Goal**: Database schema updated atomically to drop flex_1..flex_5 columns; all existing operations continue to work

**Independent Test**: Run `python manage.py migrate biometrics` in `backend/` — both migrations apply without errors; `biometric_readings` table has no flex columns (verify via quickstart.md Scenario 3)

### Implementation for User Story 2

- [X] T005 [US2] Generate Django removal migration: run `python manage.py makemigrations biometrics --name remove_flex_fields` in `backend/` — verify file created at `backend/biometrics/migrations/0003_remove_flex_fields.py` and that it contains 5 `RemoveField` operations (one per flex field)
- [X] T006 [US2] Apply all biometrics migrations: run `python manage.py migrate biometrics` in `backend/` — verify output shows `0002_add_biometricreading... OK` and `0003_remove_flex_fields... OK`

**Checkpoint**: Database schema on Supabase PostgreSQL no longer contains flex_1..flex_5 columns — User Story 2 independently verifiable via quickstart.md Scenario 3

---

## Phase 5: Polish & Validation

**Purpose**: Final verification across all success criteria

- [X] T007 [P] Verify database schema using Django shell per quickstart.md Scenario 3: introspect `biometric_readings` table columns and assert `flex_1` through `flex_5` are absent
- [X] T008 [P] Verify a `BiometricReading` record can be created and saved per quickstart.md Scenario 4: `BiometricReading.objects.create(patient=..., timestamp=..., aX=..., aY=..., aZ=..., gX=..., gY=..., gZ=...)` completes without errors
- [X] T009 Perform final audit: run `grep -r "flex_[1-5]" backend/` — confirm zero references remain anywhere in `backend/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS both user stories**
- **US1 (Phase 3)**: Depends on Foundational (T002, T003 complete)
- **US2 (Phase 4)**: Depends on US1 completion (T004 must be done before generating migration — model must match clean state)
- **Polish (Phase 5)**: Depends on US2 completion (migration must have run)

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on US2
- **US2 (P2)**: Depends on US1 — migration must reflect the clean model (without flex fields)

### Within Each Phase

- T002 → T003 (sequential: model must exist before makemigrations)
- T003 → T004 (sequential: foundational migration must exist before model cleanup)
- T004 → T005 (sequential: model must be clean before generating removal migration)
- T005 → T006 (sequential: migration file must exist before applying)
- T007, T008 can run in parallel after T006
- T009 after T008 (final audit)

---

## Parallel Opportunities

```bash
# Phase 5 — T007 and T008 can run in parallel:
Task: "Verify database schema (quickstart.md Scenario 3)"
Task: "Verify record creation (quickstart.md Scenario 4)"
```

---

## Implementation Strategy

### MVP (US1 Only — Model Code Clean)

1. Complete Phase 1: Pre-flight audit (T001)
2. Complete Phase 2: Create BiometricReading model + migration 0002 (T002, T003)
3. Complete Phase 3: Remove flex fields from model code (T004)
4. **STOP and VALIDATE**: `grep -n "flex_" backend/biometrics/models.py` → zero matches ✅
5. Proceed to US2 to apply the schema change

### Full Delivery (US1 + US2)

1. Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
2. Each step sequentially (this is a small, linear feature)
3. Total: 9 tasks, all sequential except T007/T008 in Phase 5

---

## Notes

- This is a **pure backend** feature — no frontend tasks
- No new libraries or Django apps required
- `makemigrations` auto-detects the model delta — do not write migration files by hand
- The two-migration approach (0002 creates with flex fields → 0003 removes them) satisfies the spec requirement "Create and run migration" for the removal step
- Verify `python manage.py migrate --check` returns clean after Phase 4
