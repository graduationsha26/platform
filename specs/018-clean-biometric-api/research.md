# Research: Remove Flex Fields from BiometricReading API Layer

**Branch**: `018-clean-biometric-api` | **Date**: 2026-02-18
**Phase**: 0 — Resolve unknowns before design

---

## R-001: Existing BiometricReadingSerializer — Current State

**Question**: Does a `BiometricReadingSerializer` exist in `backend/biometrics/serializers.py`?

**Finding**: `backend/biometrics/serializers.py` contains four serializers:
- `BiometricSessionListSerializer`
- `BiometricSessionDetailSerializer`
- `BiometricSessionCreateSerializer`
- `BiometricAggregationSerializer`

No `BiometricReadingSerializer` or any `BiometricReading`-related serializer exists.

**Decision**: Create `BiometricReadingSerializer` from scratch in `backend/biometrics/serializers.py`. Since the model (post E-2.1) has no flex fields, the serializer is simply created without them — no field removal needed.

**Rationale**: The serializer is new code; creating it clean is simpler and more correct than creating it with flex fields and then removing them.

**Alternatives considered**:
- Create in a new `reading_serializers.py` file: Rejected — unnecessary file proliferation; existing pattern puts all biometrics serializers in one file.

---

## R-002: Existing BiometricReading ViewSet — Current State

**Question**: Does a `BiometricReadingViewSet` exist in `backend/biometrics/views.py`?

**Finding**: `backend/biometrics/views.py` contains only `BiometricSessionViewSet`. No `BiometricReading`-related view or viewset exists.

**Decision**: Create `BiometricReadingViewSet` from scratch in `backend/biometrics/views.py`. It follows the same permission and queryset pattern as `BiometricSessionViewSet` (see R-004), but is read-only (list + retrieve only — write operations come from the MQTT pipeline).

**Alternatives considered**:
- Read-write ViewSet with POST endpoint: Rejected — BiometricReading records are created by the MQTT pipeline, not by REST consumers. A REST write endpoint is out of scope.

---

## R-003: URL Routing Strategy

**Question**: How should `/api/biometric-readings/` be routed given that the biometrics app is already mounted at `/api/biometric-sessions/`?

**Finding**: `backend/tremoai_backend/urls.py` includes `biometrics.urls` at path `api/biometric-sessions/`. The biometrics `urls.py` has a single DRF router registered at `r''` (root), which mounts `BiometricSessionViewSet` at that root. There is no way to add a second resource at a different prefix using the same `urlpatterns` list without restructuring.

**Decision**: Create a new `backend/biometrics/reading_urls.py` file containing a dedicated router for `BiometricReadingViewSet`, and add a second include in `tremoai_backend/urls.py`:
```
path('api/biometric-readings/', include('biometrics.reading_urls'))
```

This approach:
- Does not touch existing biometrics/urls.py (zero risk of breaking /api/biometric-sessions/)
- Is additive and minimal
- Follows the established pattern (each URL prefix maps to a dedicated urlpatterns module)

**Alternatives considered**:
- Merge into existing biometrics/urls.py with multiple routers: Rejected — complex and fragile; requires exporting multiple urlpatterns variables.
- Nest under sessions (`/api/biometric-sessions/{id}/readings/`): Rejected — readings are not semantically nested under sessions; they are independently queryable by patient.
- Add to a generic `api/` catch-all router: Rejected — no such pattern exists in the project.

---

## R-004: Permission Pattern

**Question**: What permission classes should `BiometricReadingViewSet` use?

**Finding**: `BiometricSessionViewSet` uses `[IsAuthenticated, IsOwnerOrDoctor]`. Patients see only their own data; doctors see data for their assigned patients. This is the appropriate access control model for biometric reading data as well.

**Decision**: Use `[IsAuthenticated, IsOwnerOrDoctor]` — the same permission classes as `BiometricSessionViewSet`.

**Decision (queryset)**: Doctors see readings for their accessible patients; patients see only their own readings. Follow the same `Q(created_by=user) | Q(doctor_assignments__doctor=user)` pattern used in `BiometricSessionViewSet.get_queryset()`.

---

## R-005: Serializer Field Scope

**Question**: What fields should `BiometricReadingSerializer` include?

**Finding**: The BiometricReading model (post E-2.1) has: `id`, `patient` (FK), `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`. No flex fields.

**Decision**: `BiometricReadingSerializer` fields = `['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']`. All fields read-only (consistent with read-only ViewSet). `patient_id` is exposed as an integer (not nested) to keep the serializer simple and lightweight.

**Alternatives considered**:
- Nested patient object: Rejected for this feature scope — adds complexity without adding value for the current use case (MQTT pipeline reads, not user-facing detail views).
- Include statistical computed fields: Rejected — not part of the model; computed aggregates belong in analytics, not the raw reading serializer.

---

## Summary of Decisions

| Research | Decision |
|----------|----------|
| R-001 | Create `BiometricReadingSerializer` in `backend/biometrics/serializers.py` |
| R-002 | Create `BiometricReadingViewSet` (read-only) in `backend/biometrics/views.py` |
| R-003 | Create `backend/biometrics/reading_urls.py`; add entry to `tremoai_backend/urls.py` |
| R-004 | Use `[IsAuthenticated, IsOwnerOrDoctor]` permissions; mirror session queryset pattern |
| R-005 | Fields: `id, patient_id, timestamp, aX, aY, aZ, gX, gY, gZ` — all read-only |
