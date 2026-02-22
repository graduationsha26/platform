# Implementation Plan: Biometric 6-Axis Field Cleanup

**Branch**: `020-biometric-6-axis` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-biometric-6-axis/spec.md`

---

## Summary

Feature 020 audits and finalizes the 6-axis-only structure of the `BiometricReading` model and API. The model was designed from scratch with only the 6 active sensor axes (aX, aY, aZ, gX, gY, gZ); the magnetometer fields (mX, mY, mZ) were never added to the model or the database.

**Key research finding**: mX/mY/mZ exist only in the raw ML training CSV (`Dataset.csv`) where they are correctly dropped before feature extraction. No migration to remove them from `BiometricReading` is needed. The actual work is:

1. Apply pending migrations (0002 + 0003) to create the `biometric_readings` table
2. Clean up stale inline comments in `serializers.py` and `views.py` (they reference "Feature E-2.1" and "flex_1 through flex_5" — outdated history)

---

## Technical Context

**Backend Stack**: Django 5.x + Django REST Framework
**Frontend Stack**: React 18+ + Vite + Tailwind CSS + Recharts
**Database**: Supabase PostgreSQL (remote)
**Authentication**: JWT (SimpleJWT) with roles (doctor/patient)
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Project Type**: web (monorepo: backend/ and frontend/)
**Real-time**: Django Channels WebSocket for live tremor data
**Integration**: MQTT subscription for glove sensor data
**AI/ML**: scikit-learn (.pkl) and TensorFlow/Keras (.h5) served via Django
**Performance Goals**: Standard API response times (<500ms for list/detail)
**Constraints**: Local development only; no Docker/CI/CD
**Scale/Scope**: Small team (~10 doctors, ~100 patients)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Monorepo Architecture**: Changes confined to `backend/biometrics/` — fits within monorepo
- [x] **Tech Stack Immutability**: No new frameworks or libraries introduced
- [x] **Database Strategy**: Uses Supabase PostgreSQL via Django migrations (no SQLite, no other DBs)
- [x] **Authentication**: `BiometricReadingViewSet` enforces `IsAuthenticated` + `IsOwnerOrDoctor` (JWT roles)
- [x] **Security-First**: No hardcoded credentials; access control at endpoint level
- [x] **Real-time Requirements**: Feature does not add new real-time functionality (N/A)
- [x] **MQTT Integration**: MQTT client already uses 6-axis-only format; no changes needed
- [x] **AI Model Serving**: Feature does not affect ML model serving (N/A); ML training data pipeline handles mX/mY/mZ correctly and independently
- [x] **API Standards**: REST + JSON; `BiometricReadingSerializer` uses snake_case-style field names native to the hardware protocol
- [x] **Development Scope**: Local development only; no deployment artifacts

**Result**: ✅ PASS — no constitution violations

---

## Project Structure

### Documentation (this feature)

```text
specs/020-biometric-6-axis/
├── plan.md              # This file
├── research.md          # Phase 0 output — field audit findings
├── data-model.md        # Phase 1 output — BiometricReading entity
├── quickstart.md        # Phase 1 output — integration scenarios
├── contracts/
│   └── biometric-readings.yaml   # Phase 1 output — OpenAPI spec
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (files touched by this feature)

```text
backend/
├── biometrics/
│   ├── models.py             # [NO CHANGE] — already has 6 axes only
│   ├── serializers.py        # [COMMENT CLEANUP] — update stale "E-2.1" / "flex" references
│   ├── views.py              # [COMMENT CLEANUP] — update stale "flex" references in docstrings
│   ├── reading_urls.py       # [NO CHANGE] — already registered
│   └── migrations/
│       ├── 0002_add_biometricreading.py   # [APPLY] — creates table with aX-gZ + flex fields
│       └── 0003_remove_flex_fields.py     # [APPLY] — drops flex_1 through flex_5
└── tremoai_backend/
    └── urls.py               # [NO CHANGE] — /api/biometric-readings/ already registered
```

**Files explicitly NOT touched**:
- `backend/ml_data/utils/data_loader.py` — magnetometer handling in ML pipeline is intentional and correct
- `backend/realtime/mqtt_client.py` — already uses 6-axis-only format
- `backend/realtime/validators.py` — already uses 6-axis-only validation

---

## Phase 0: Research Findings

See [research.md](research.md) for full details. Summary:

| Question | Answer |
|---|---|
| Do mX/mY/mZ exist in BiometricReading? | No. Never existed. Model was created 6-axis-only. |
| Do migrations need to remove mX/mY/mZ? | No. Existing migrations 0002+0003 handle only flex fields. |
| Is the serializer correct? | Yes. Exposes exactly the 6 axis fields. Comments are stale. |
| Is the MQTT client correct? | Yes. Creates BiometricReading with exactly 6 fields. |
| Are the validators correct? | Yes. Require only aX/aY/aZ/gX/gY/gZ. |
| Is the URL routing complete? | Yes. /api/biometric-readings/ is registered. |
| Should ML data pipeline be changed? | No. mX/mY/mZ in Dataset.csv are handled correctly. |

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) for full entity definition.

**BiometricReading** (final schema after migrations 0002 + 0003):

| Field | Type | Notes |
|---|---|---|
| `id` | BigInt PK | Auto-generated |
| `patient` | FK → Patient | CASCADE delete |
| `timestamp` | DateTime | From MQTT payload |
| `aX` | Float | Accelerometer X |
| `aY` | Float | Accelerometer Y |
| `aZ` | Float | Accelerometer Z |
| `gX` | Float | Gyroscope X |
| `gY` | Float | Gyroscope Y |
| `gZ` | Float | Gyroscope Z |

No magnetometer or flex fields in the database.

### API Contract

See [contracts/biometric-readings.yaml](contracts/biometric-readings.yaml).

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/biometric-readings/` | GET | JWT (doctor/patient) | List readings (paginated, filtered by patient) |
| `/api/biometric-readings/{id}/` | GET | JWT (doctor/patient) | Retrieve single reading |

Both endpoints use `BiometricReadingSerializer` which exposes exactly:
`id`, `patient_id`, `timestamp`, `aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`

### Integration Scenarios

See [quickstart.md](quickstart.md) for full integration examples.

---

## Implementation Tasks

Feature 020 has minimal code changes. The two tasks:

### Task 1: Apply Pending Migrations

Run migrations 0002 and 0003 to create and finalize the `biometric_readings` table.

```bash
python manage.py migrate biometrics
```

Verify:
```bash
python manage.py showmigrations biometrics
# Expected: all three migrations marked [X]
```

### Task 2: Update Stale Inline Comments

**File**: `backend/biometrics/serializers.py` (lines 196-206)

Current (stale):
```python
"""Read-only serializer for individual BiometricReading records.

Exposes only the six raw sensor fields plus metadata.
flex_1 through flex_5 are intentionally excluded (removed in Feature E-2.1).
"""
```

Target (accurate):
```python
"""Read-only serializer for individual BiometricReading records.

Exposes exactly the six raw IMU sensor fields (accelerometer + gyroscope) plus metadata.
The BiometricReading model was designed with only these 6 axes from inception.
No magnetometer fields (mX, mY, mZ) or flex fields are part of this model.
"""
```

**File**: `backend/biometrics/views.py` (lines 209-224, BiometricReadingViewSet docstring)

Current (stale):
```
flex_1 through flex_5 are intentionally absent from all responses
(removed from the model in Feature E-2.1).
```

Target (accurate):
```
The BiometricReadingViewSet exposes only the 6 active IMU sensor axes (aX, aY, aZ, gX, gY, gZ).
No magnetometer or flex fields were ever part of the BiometricReading model.
```

---

## Complexity Tracking

No constitution violations. No complexity additions.
