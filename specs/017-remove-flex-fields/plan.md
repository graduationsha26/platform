# Implementation Plan: Remove Flex Fields from BiometricReading

**Branch**: `017-remove-flex-fields` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/017-remove-flex-fields/spec.md`

## Summary

Remove the five unused placeholder FloatFields (`flex_1` through `flex_5`) from the `BiometricReading` model in `backend/biometrics/`. This is a pure backend schema cleanup: update the model definition to exclude those fields, generate a Django migration to drop the corresponding database columns on Supabase PostgreSQL, and scan for any stale code references (serializers, views, MQTT handlers) that must be removed before applying the migration.

No new endpoints, no frontend changes, no new libraries.

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: N/A (no frontend changes)
**Database**: Supabase PostgreSQL (remote) — migration applied via `python manage.py migrate`
**Authentication**: N/A (not touched)
**Testing**: pytest (backend)
**Project Type**: web (monorepo: `backend/` only for this feature)
**Real-time**: N/A
**Integration**: N/A (MQTT handler may reference BiometricReading — must audit)
**AI/ML**: N/A
**Performance Goals**: Migration executes in under 5 seconds on an empty/small table
**Constraints**: Local development only; Supabase remote DB; no Docker/CI
**Scale/Scope**: 5 column drops on `biometric_readings` table; zero API surface area change

**Key unknowns resolved (see research.md)**:
- BiometricReading model location: `backend/biometrics/models.py` (to be added alongside `BiometricSession`)
- Migration strategy: standard `RemoveField` operations in a single migration file
- Reference audit: no flex field references currently exist in the codebase (clean slate)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Feature is contained entirely in `backend/biometrics/` — no new apps or directories
- [x] **Tech Stack Immutability**: Uses only Django's built-in migrations framework — no new libraries
- [x] **Database Strategy**: Uses Supabase PostgreSQL via standard Django migrations — no local DB, no other systems
- [x] **Authentication**: Not touched
- [x] **Security-First**: No secrets involved; no `.env` changes needed
- [x] **Real-time Requirements**: Not applicable — no WebSocket changes
- [x] **MQTT Integration**: MQTT handler audited for stale references (see research.md — none found currently)
- [x] **AI Model Serving**: Not applicable
- [x] **API Standards**: No new endpoints — existing endpoints unaffected
- [x] **Development Scope**: Local development only; migration run via `python manage.py migrate`

**Result**: ✅ PASS — no constitutional violations

## Project Structure

### Documentation (this feature)

```text
specs/017-remove-flex-fields/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files to create or modify)

```text
backend/
└── biometrics/
    ├── models.py                          # MODIFY: add BiometricReading without flex fields
    └── migrations/
        └── 0002_add_biometricreading.py   # CREATE: adds BiometricReading model
        └── 0003_remove_flex_fields.py     # CREATE: drops flex_1..flex_5 columns
```

> **Note**: Because BiometricReading does not yet exist in the codebase, two migrations are required:
> 1. `0002` creates the BiometricReading model (this may include flex fields as a transitional step if the epic requires it, or may skip them entirely if the model is created clean from the start)
> 2. `0003` drops the flex columns (satisfies the formal "create and run migration" requirement of E-2.1)
>
> If the model is created clean (without flex fields in the first place), only `0002` is needed and the task is to ensure flex fields are never introduced.

**Structure Decision**: All changes are in `backend/biometrics/`. No serializer, view, or URL changes needed because BiometricReading has no REST API surface at this stage (sensor data is ingested via MQTT, not via a user-facing endpoint). If a serializer is later added, it simply omits flex fields.

## Complexity Tracking

No constitutional violations — no complexity tracking required.
