# Tasks: Remove Flex Fields from BiometricReading API Layer

**Input**: Design documents from `/specs/018-clean-biometric-api/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.
- **US1** (P1): Clean Data Contract — `BiometricReadingSerializer` exposes no flex fields
- **US2** (P2): Clean Request Handling — `BiometricReadingViewSet` and URL routing contain no flex references

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- All paths are relative to the repository root

---

## Phase 1: Setup (Pre-flight Audit)

**Purpose**: Confirm baseline state — no flex references exist in the application layer before changes begin

- [X] T001 Audit `backend/biometrics/serializers.py` and `backend/biometrics/views.py` for any existing `flex_1`–`flex_5` references: `grep -n "flex_" backend/biometrics/serializers.py backend/biometrics/views.py` (expected: zero matches)

---

## Phase 2: Foundational (Dependency Verification)

**Purpose**: Confirm that Feature E-2.1 (model cleanup) is complete before building the API layer on top of it

**⚠️ CRITICAL**: The serializer and viewset depend on `BiometricReading` existing in `backend/biometrics/models.py` without flex fields

- [X] T002 Verify `BiometricReading` model exists in `backend/biometrics/models.py` with exactly the fields: `patient`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ` and no flex fields: `grep -n "class BiometricReading\|flex_" backend/biometrics/models.py` (expected: class found, zero flex lines)

**Checkpoint**: BiometricReading model confirmed clean — US1 and US2 implementation can begin

---

## Phase 3: User Story 1 — Clean Data Contract (Priority: P1) 🎯 MVP

**Goal**: `BiometricReadingSerializer` is created in `backend/biometrics/serializers.py` with exactly 9 fields (`id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`) and no flex fields

**Independent Test**: Run quickstart.md Scenario 4 — Django shell assertion that serializer fields == expected set with zero flex fields present

### Implementation for User Story 1

- [X] T003 [US1] Add import for `BiometricReading` model at the top of `backend/biometrics/serializers.py`: add `from .models import BiometricSession, BiometricReading` (update the existing import line)
- [X] T004 [US1] Append `BiometricReadingSerializer` class to the bottom of `backend/biometrics/serializers.py` as a `ModelSerializer` with `model = BiometricReading`, `fields = ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`, and `read_only_fields = fields` — no flex fields

**Checkpoint**: `BiometricReadingSerializer` exists in `backend/biometrics/serializers.py` with no flex fields — independently verifiable via quickstart.md Scenario 4

---

## Phase 4: User Story 2 — Clean Request Handling (Priority: P2)

**Goal**: `BiometricReadingViewSet` exists in `backend/biometrics/views.py`, is routed at `/api/biometric-readings/`, and contains no flex field references in any logic

**Independent Test**: Run quickstart.md Scenario 5 — `reverse('biometric-reading-list')` resolves to `/api/biometric-readings/`; quickstart.md Scenario 3 — GET `/api/biometric-readings/` returns 200 with no flex fields in response

### Implementation for User Story 2

- [X] T005 [US2] Add `BiometricReadingSerializer` to the imports at the top of `backend/biometrics/views.py`: update the serializer import line to also include `BiometricReadingSerializer`
- [X] T006 [US2] Add `BiometricReading` model to the imports in `backend/biometrics/views.py` (alongside `BiometricSession`)
- [X] T007 [US2] Append `BiometricReadingViewSet` class to the bottom of `backend/biometrics/views.py` as a `ReadOnlyModelViewSet` with `permission_classes = [IsAuthenticated, IsOwnerOrDoctor]`, `serializer_class = BiometricReadingSerializer`, `filter_backends = [DjangoFilterBackend]`, `filterset_fields = ['patient']`, and `get_queryset()` that returns readings for accessible patients (doctors) or own readings (patients) — no flex field references anywhere in the class
- [X] T008 [US2] Create new file `backend/biometrics/reading_urls.py` with a `DefaultRouter` that registers `BiometricReadingViewSet` at `r''` with `basename='biometric-reading'`, and a `urlpatterns = [path('', include(router.urls))]`
- [X] T009 [US2] Add `path('api/biometric-readings/', include('biometrics.reading_urls'))` to the `urlpatterns` list in `backend/tremoai_backend/urls.py` (after the existing biometric-sessions entry)

**Checkpoint**: GET `/api/biometric-readings/` returns HTTP 200 with no flex fields — User Story 2 independently verifiable

---

## Phase 5: Polish & Validation

**Purpose**: Final audit and end-to-end verification across all success criteria

- [X] T010 [P] Final audit — confirm zero flex references in all modified files: `grep -n "flex_" backend/biometrics/serializers.py backend/biometrics/views.py backend/biometrics/reading_urls.py` (expected: zero matches)
- [X] T011 [P] Django shell serializer field check per quickstart.md Scenario 4: import `BiometricReadingSerializer`, assert `set(fields.keys()) == {'id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'}` and no flex fields present
- [X] T012 Django shell URL check per quickstart.md Scenario 5: `reverse('biometric-reading-list')` resolves without error to `/api/biometric-readings/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **confirms E-2.1 is done**
- **US1 (Phase 3)**: Depends on Foundational (T002 complete) — serializer needs clean model
- **US2 (Phase 4)**: Depends on US1 (T004 complete) — ViewSet needs `BiometricReadingSerializer`
- **Polish (Phase 5)**: Depends on US2 (T009 complete) — all code and routing must be in place

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — independent of US2
- **US2 (P2)**: Depends on US1 — `BiometricReadingViewSet` imports and uses `BiometricReadingSerializer`

### Within Each Phase

- T003 → T004 (sequential: import before class definition)
- T005 → T006 → T007 (sequential: imports before class)
- T007 → T008 (sequential: ViewSet must exist before URL registration)
- T008 → T009 (sequential: reading_urls.py must exist before including it in main urls.py)
- T010, T011 can run in parallel after T009
- T012 after T011 (URL check after serializer check)

---

## Parallel Opportunities

```bash
# Phase 5 — T010 and T011 can run in parallel:
Task: "Final grep audit (zero flex refs)"
Task: "Django shell serializer field assertion"
```

---

## Implementation Strategy

### MVP (US1 Only — Serializer Clean)

1. Complete Phase 1: Pre-flight audit (T001)
2. Complete Phase 2: Confirm E-2.1 done (T002)
3. Complete Phase 3: Create `BiometricReadingSerializer` (T003, T004)
4. **STOP and VALIDATE**: quickstart.md Scenario 4 → `PASS: BiometricReadingSerializer has no flex fields` ✅
5. Proceed to US2 for ViewSet and URL wiring

### Full Delivery (US1 + US2)

1. Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
2. Sequential execution (serializer → viewset → urls → wiring)
3. Total: 12 tasks, T010/T011 parallel in Phase 5

---

## Notes

- This is a **pure backend** feature — no frontend changes, no database changes, no migrations
- No new libraries required — uses existing DRF, authentication, and filter backends
- `BiometricReadingViewSet` is **read-only** (`ReadOnlyModelViewSet`) — write operations come from MQTT pipeline
- The flex fields are absent from the model (E-2.1) — this feature ensures they are also absent from every layer above the model
- API contract reference: `specs/018-clean-biometric-api/contracts/biometric-readings.yaml`
