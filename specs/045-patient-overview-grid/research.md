# Research: Patient Overview Grid

**Branch**: `045-patient-overview-grid` | **Phase**: 0 Research | **Date**: 2026-06-14

## Decision 1 — Endpoint Location: patients app, not a new dashboard app

**Decision**: Add `GET /api/patients/overview/` as a custom view in `backend/patients/views.py`, registered in `backend/patients/urls.py`.

**Rationale**: The spec says the view belongs in `patients/views.py`. There is no existing `backend/dashboard/` Django app and creating one for a single endpoint adds unnecessary overhead. The `patients` app is the natural semantic home for a "list patients with overview data" endpoint. URL becomes `/api/patients/overview/` — more RESTful than `/api/dashboard/patients-overview/`.

**Alternatives considered**:
- `backend/analytics/views.py` at `/api/analytics/patients-overview/`: Rejected — analytics is for metrics/statistics; this returns entity list data.
- New `backend/dashboard/` app: Rejected — one endpoint does not justify a new Django app in a time-constrained project.

---

## Decision 2 — Avatar URL: Add field to Patient model

**Decision**: Add `avatar_url = models.URLField(max_length=500, blank=True, default='')` to the Patient model (`backend/patients/models.py`). A Django migration is required.

**Rationale**: The Patient model currently has no photo/avatar field. The spec requires returning `avatar_url` per patient. Adding an optional URLField to the existing model is the minimal, correct approach. An empty string (falsy in Python/JS) signals the frontend to render initials instead.

**Alternatives considered**:
- Returning `null` always and never supporting real photos: Rejected — the spec explicitly calls for photo support with initials as fallback; adding the field now keeps the door open.
- Storing avatar in a separate model: Rejected — over-engineering; a simple nullable URL field suffices.

---

## Decision 3 — device_online Derivation: Annotate with Max(last_seen), compare in Python

**Decision**: Annotate the patient queryset with `Max('devices__last_seen')` to get the most recent last_seen timestamp across all a patient's devices in a single query. Compare against `timezone.now() - timedelta(seconds=60)` in Python. `device_online = True` iff `latest_seen >= threshold`.

**Rationale**: `Device.last_seen` is already maintained by the device pairing/status update flow (confirmed in `backend/devices/views.py`). Using `annotate(latest_device_seen=Max('devices__last_seen'))` avoids N+1 queries and is a single JOIN — efficient for typical doctor cohorts (10–50 patients). The 60-second threshold is specified in the feature description (4.5).

**Alternatives considered**:
- `prefetch_related('devices')` + Python loop: Functionally equivalent but fetches all device rows; the annotation approach fetches only the aggregated timestamp.
- Using `Device.status` field ('online'/'offline'): Rejected — `Device.status` is updated by MQTT/HTTP status update calls and may lag; `last_seen` is more precise and matches the spec's 60-second rule.

---

## Decision 4 — Initials Generation: Frontend-side, from full_name

**Decision**: Compute initials in the `PatientCard` React component from the `full_name` string: split on spaces, take the first letter of each word, uppercase, limit to 2 characters (first two words' initials).

**Rationale**: The Patient model stores `full_name` as a single CharField (e.g., "Ahmed Karim Nour"). Computing initials on the frontend avoids a backend field or computed property. Limiting to 2 characters fits circular avatar sizing (e.g., "AK"). Single-word names use the first letter only.

**Alternatives considered**:
- Backend computed field on serializer: Acceptable but adds backend logic for something purely presentational.

---

## Decision 5 — Frontend Service File: patientService.js

**Decision**: Add `fetchPatientsOverview()` to `frontend/src/services/patientService.js`.

**Rationale**: A `patientService.js` file already exists (confirmed by the existing patient list pages). Patient overview data is patient data, not analytics. Keeping patient API calls in `patientService.js` and analytics calls in `analyticsService.js` preserves separation of concerns.

**Alternatives considered**:
- `analyticsService.js`: Rejected — this is an entity list, not an analytics metric.

---

## Decision 6 — Grid Placement: Below summary cards in DoctorDashboard

**Decision**: Render `<PatientOverviewGrid />` inside a new `<div className="mt-8">` block below the existing 3-card summary row in `frontend/src/pages/DoctorDashboard.jsx`.

**Rationale**: This is exactly the space vacated by the `TremorTrendChart` removed in feature 044. No layout restructuring needed — just append below the cards grid.

---

## Decision 7 — Navigation: react-router-dom Link components in PatientCard

**Decision**: "View Profile" renders as a `<Link to={`/doctor/patients/${patient.id}`}>` and "Live Monitor" renders as a `<Link to={`/doctor/patients/${patient.id}/monitor`}>`. Routes `/doctor/patients/:id` and `/doctor/patients/:id/monitor` are confirmed to exist in `frontend/src/routes/AppRoutes.jsx`.

**Alternatives considered**:
- `useNavigate()` + `onClick`: Functionally equivalent but `<Link>` provides better accessibility (right-click → new tab, hover URL preview).

---

## Decision 8 — No Django migration side-effects

The `avatar_url` migration is an additive `ALTER TABLE` (new nullable column with default `''`). On Supabase PostgreSQL, adding a nullable column with a default does not lock the table for extended periods. Existing patient records will have `avatar_url = ''` after migration. Safe to run without downtime.
