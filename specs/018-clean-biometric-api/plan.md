# Implementation Plan: Remove Flex Fields from BiometricReading API Layer

**Branch**: `018-clean-biometric-api` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-clean-biometric-api/spec.md`

## Summary

Create a `BiometricReadingSerializer` and a `BiometricReadingViewSet` in `backend/biometrics/` that expose only the six sensor fields (`aX, aY, aZ, gX, gY, gZ`) plus metadata — no flex fields. Wire the viewset into the existing URL router. Because neither the serializer nor the view exists yet (confirmed by codebase audit), this feature creates them clean from the start rather than removing flex fields from existing code.

This is a pure backend REST API layer feature — no database changes, no frontend changes, no new libraries.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: N/A (no frontend changes)
**Database**: Supabase PostgreSQL (remote) — `BiometricReading` model already exists (Feature E-2.1)
**Authentication**: JWT via SimpleJWT — `IsAuthenticated` + `IsOwnerOrDoctor` (same pattern as `BiometricSessionViewSet`)
**Testing**: pytest (backend) — not requested in spec
**Project Type**: web (monorepo: `backend/` only for this feature)
**Real-time**: N/A
**Integration**: N/A (readings created via MQTT, not via REST POST — ViewSet is read-only at this stage)
**AI/ML**: N/A
**Performance Goals**: Standard API response targets (consistent with BiometricSessionViewSet)
**Constraints**: Local development only; no Docker/CI
**Scale/Scope**: Read-only ViewSet (list + retrieve); no create/update/delete via REST

**Key findings from research (see research.md)**:
- No `BiometricReadingSerializer` exists — must be created
- No `BiometricReading` ViewSet or URL entry exists — must be created and wired
- No flex field references exist outside migrations — no cleanup required, only "create clean"
- Permissions pattern: follow existing `BiometricSessionViewSet` (IsAuthenticated + IsOwnerOrDoctor)
- URL pattern: add to existing `backend/biometrics/urls.py` router

## Constitution Check

- [x] **Monorepo Architecture**: All changes in `backend/biometrics/` — no new apps or directories
- [x] **Tech Stack Immutability**: DRF `ModelSerializer` + `ReadOnlyModelViewSet` — no new libraries
- [x] **Database Strategy**: BiometricReading model on Supabase PostgreSQL (already migrated)
- [x] **Authentication**: JWT via `IsAuthenticated` + `IsOwnerOrDoctor` — same as existing ViewSets
- [x] **Security-First**: No secrets; no `.env` changes needed
- [x] **Real-time Requirements**: N/A — not a real-time feature
- [x] **MQTT Integration**: N/A — readings ingested via MQTT separately; this is a read API only
- [x] **AI Model Serving**: N/A
- [x] **API Standards**: REST + JSON, snake_case keys, standard HTTP codes, `/api/biometric-readings/`
- [x] **Development Scope**: Local development only; no Docker/CI

**Result**: ✅ PASS — no constitutional violations

## Project Structure

### Documentation (this feature)

```text
specs/018-clean-biometric-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── biometric-readings.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files to create or modify)

```text
backend/
└── biometrics/
    ├── serializers.py    # MODIFY: add BiometricReadingSerializer
    ├── views.py          # MODIFY: add BiometricReadingViewSet
    └── urls.py           # MODIFY: register biometric-readings router entry
```

**Structure Decision**: All changes are additions to existing files in `backend/biometrics/`. No new files, no new apps. The `BiometricReadingViewSet` is registered at `/api/biometric-readings/` via the existing DRF router in `urls.py`. The ViewSet is read-only (list + retrieve) — write operations come from the MQTT pipeline, not from the REST API.

## Complexity Tracking

No constitutional violations — no complexity tracking required.
