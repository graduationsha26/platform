# Research: Patient List & Detail Pages

**Branch**: `033-patient-list-detail` | **Date**: 2026-02-20

---

## Finding 1: Backend Patient API Is Fully Implemented — No New Endpoints Needed

**Decision**: Reuse all existing `PatientViewSet` endpoints. No new backend views or URLs required.

**Rationale**: The `PatientViewSet` at `/api/patients/` already provides all required operations:
- `GET /api/patients/` — paginated list (20/page) with `?name=` filter via `PatientFilter`
- `POST /api/patients/` — create patient (auto-assigns to creating doctor)
- `GET /api/patients/{id}/` — full detail with nested assigned doctors and paired device
- `PUT /api/patients/{id}/` — full update
- `PATCH /api/patients/{id}/` — partial update

Access control is already implemented: doctors see only their own created/assigned patients.

**Alternatives considered**:
- *Rewriting the patient API*: Rejected — existing implementation is correct and complete.
- *Adding a separate search endpoint*: Not needed — the list endpoint accepts `?name=` filter.

---

## Finding 2: PatientListSerializer Missing `last_session_date` — Minor Addition Required

**Decision**: Add a `SerializerMethodField` called `last_session_date` to `PatientListSerializer` in `backend/patients/serializers.py`.

**Rationale**: FR-001 requires the patient list to show each patient's most recent session date. The current `PatientListSerializer` includes `id`, `full_name`, `date_of_birth`, `contact_email`, `created_at` but not session data. Adding a computed field is the simplest approach.

**Implementation**:
```python
last_session_date = serializers.SerializerMethodField()

def get_last_session_date(self, obj):
    latest = obj.biometric_sessions.order_by('-session_start').first()
    return latest.session_start.isoformat() if latest else None
```

**N+1 Query Risk**: The `PatientViewSet.list()` must add `prefetch_related('biometric_sessions')` to the queryset (or a more targeted prefetch using `Prefetch` with a queryset limited to the latest session per patient). The simplest safe approach is `prefetch_related('biometric_sessions')` — for up to 100 patients this is acceptable.

**Alternatives considered**:
- *Computing on the frontend by calling the sessions endpoint for each patient*: Rejected — N+1 API calls, slow, complex.
- *Adding a denormalized `last_session_date` field to the Patient model*: Overkill — computed field is cleaner.

---

## Finding 3: BiometricSessionListSerializer Missing `ml_prediction_severity` — Minor Addition Required

**Decision**: Add a `SerializerMethodField` called `ml_prediction_severity` to `BiometricSessionListSerializer` in `backend/biometrics/serializers.py`.

**Rationale**: FR-008 requires each session history entry to show "ML prediction severity". The `BiometricSession.ml_prediction` is a JSONField with structure `{"severity": "mild"|"moderate"|"severe", "confidence": 0.0-1.0}`. The list serializer currently includes `id`, `patient`, `device`, `session_start`, `session_duration`, `created_at` — but not `ml_prediction`.

**Implementation**:
```python
ml_prediction_severity = serializers.SerializerMethodField()

def get_ml_prediction_severity(self, obj):
    if obj.ml_prediction:
        return obj.ml_prediction.get('severity')
    return None
```

**Alternatives considered**:
- *Exposing the full `ml_prediction` JSON*: Unnecessary — only severity is displayed; exposing confidence requires frontend logic to parse.
- *Using the detail serializer for list views*: Rejected — includes heavy `sensor_data` JSON arrays, too expensive for a list.

---

## Finding 4: Session History Uses Existing `/api/biometric-sessions/?patient={id}` Endpoint

**Decision**: Fetch session history for the detail page using `GET /api/biometric-sessions/?patient={id}&page=1&page_size=10`.

**Rationale**: The `BiometricSessionViewSet` already supports patient-scoped filtering and pagination. The list serializer (with the `ml_prediction_severity` addition from Finding 3) provides exactly the fields needed for the session history table.

**Alternatives considered**:
- *Embedding sessions in the patient detail response*: Adds pagination complexity to an already nested response; better to keep as a separate paginated endpoint.
- *A custom session history endpoint on the patient router*: Unnecessary — the existing sessions endpoint with `?patient=` filter serves this need.

---

## Finding 5: Search Strategy — Debounced Server-Side with Existing Filter

**Decision**: Implement search as a debounced input (300ms) that calls `GET /api/patients/?name=<term>` on change. The backend `PatientFilter` already provides case-insensitive ILIKE filtering on `full_name`.

**Rationale**: SC-003 requires "search results visibly update within 1 second of typing". A 300ms debounce gives responsive UX while avoiding excessive API calls. The existing `name` filter on the list endpoint handles this directly.

**Alternatives considered**:
- *Client-side filtering of already-loaded pages*: Only works for one page at a time; breaks for doctors with many patients.
- *Using the dedicated `/api/patients/search/?name=` endpoint*: Equivalent result — the list endpoint's `?name=` filter is identical in behavior and more RESTful (returns paginated results).

---

## Finding 6: Frontend Route Structure

**Decision**: Four routes under the `/doctor/patients` namespace:

| Route | Page | Notes |
|-------|------|-------|
| `/doctor/patients` | `PatientListPage` | Main list with search + pagination |
| `/doctor/patients/new` | `PatientCreatePage` | Create form |
| `/doctor/patients/:id` | `PatientDetailPage` | Profile + session history |
| `/doctor/patients/:id/edit` | `PatientEditPage` | Edit form (pre-populated) |

**Rationale**: The Sidebar already expects `/doctor/patients` as the navigation link. The `:id/edit` pattern is standard REST-flavored routing. `/new` before `/:id` prevents React Router from interpreting "new" as a patient ID.

---

## Finding 7: Shared PatientForm Component Strategy

**Decision**: Create a single `PatientForm.jsx` component used by both `PatientCreatePage` and `PatientEditPage`. It accepts an optional `initialValues` prop and an `onSubmit` callback. When `initialValues` is provided (edit mode), form fields are pre-populated.

**Rationale**: Create and edit forms share all the same fields and validation logic. A shared component eliminates duplication. The page-level components handle the API call (POST vs PATCH) and navigation-on-success.

---

## Finding 8: PatientViewSet Queryset Must Include `prefetch_related` for Sessions

**Decision**: Add `prefetch_related('biometric_sessions')` to the `PatientViewSet`'s `get_queryset()` method to avoid N+1 queries when serializing `last_session_date` for list responses.

**Rationale**: Without prefetch, each patient in the list triggers a separate query to `biometric_sessions` to find the latest session. With 20 patients per page, this is 21 queries (1 for patients + 20 for sessions). With prefetch, it's 2 queries total.

**Note**: The `PatientDetailSerializer` likely already handles its own related data; the `prefetch_related` addition targets the list action specifically.
