# Data Model: Patient List & Detail Pages

**Branch**: `033-patient-list-detail` | **Date**: 2026-02-20

---

## Overview

No new database models are introduced. This feature reads from and writes to three existing models: `Patient`, `DoctorPatientAssignment`, and `BiometricSession`. Two existing serializers are extended with computed fields.

---

## Entities Used

### Patient
*Source model: `backend/patients/models.py`*

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | integer | auto | Primary key |
| `full_name` | string (max 200) | ✅ | Validated non-empty, non-whitespace |
| `date_of_birth` | date | ✅ | Must not be in the future |
| `contact_phone` | string (max 20) | No | Regex validated if provided |
| `contact_email` | email | No | Format validated if provided |
| `medical_notes` | text | No | Free text |
| `created_by` | FK(CustomUser) | auto | Set from `request.user` on creation |
| `created_at` | datetime | auto | |
| `updated_at` | datetime | auto | |

**Computed fields added to serializers**:
- `last_session_date` — the `session_start` of the most recent `BiometricSession` for this patient, or `null` if none. Added to `PatientListSerializer`.

---

### DoctorPatientAssignment
*Source model: `backend/patients/models.py`*

| Field | Type | Notes |
|-------|------|-------|
| `doctor` | FK(CustomUser) | The assigned doctor |
| `patient` | FK(Patient) | The assigned patient |
| `assigned_at` | datetime | Auto-set |
| `assigned_by` | FK(CustomUser) | Optional; who made the assignment |

**Usage in this feature**: When a doctor creates a patient, the existing `PatientViewSet.perform_create()` automatically creates a `DoctorPatientAssignment` linking the doctor to the new patient.

---

### BiometricSession
*Source model: `backend/biometrics/models.py`*

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | Primary key |
| `patient` | FK(Patient) | Which patient the session belongs to |
| `device` | FK(Device) | Which glove device was used |
| `session_start` | datetime | Start time of the session |
| `session_duration` | duration | Length of the session |
| `ml_prediction` | JSON `{severity, confidence}` | Optional; set post-session |
| `created_at` | datetime | Auto |

**Computed field added to serializer**:
- `ml_prediction_severity` — extracts `ml_prediction.severity` (`"mild"`, `"moderate"`, `"severe"`) or `null`. Added to `BiometricSessionListSerializer`.

---

## API Response Shapes

### Patient List Item (GET /api/patients/)

```json
{
  "id": 1,
  "full_name": "Ahmed Hassan",
  "date_of_birth": "1958-03-12",
  "contact_email": "ahmed@example.com",
  "created_at": "2026-01-15T09:30:00Z",
  "last_session_date": "2026-02-18T14:22:00Z"
}
```

### Patient Detail (GET /api/patients/{id}/)

```json
{
  "id": 1,
  "full_name": "Ahmed Hassan",
  "date_of_birth": "1958-03-12",
  "contact_phone": "+201234567890",
  "contact_email": "ahmed@example.com",
  "medical_notes": "Moderate Parkinson's, right hand dominant tremor.",
  "created_by": { "id": 10, "email": "doctor@hospital.com", "first_name": "Sara", "last_name": "Ali" },
  "assigned_doctors": [{ "doctor": { "id": 10, "email": "doctor@hospital.com" }, "assigned_at": "2026-01-15T09:30:00Z" }],
  "paired_device": { "id": 5, "serial_number": "GLOVE0001AA", "status": "online" },
  "created_at": "2026-01-15T09:30:00Z",
  "updated_at": "2026-02-19T11:00:00Z"
}
```

### Session History Item (GET /api/biometric-sessions/?patient={id})

```json
{
  "id": 42,
  "patient": { "id": 1, "full_name": "Ahmed Hassan" },
  "device": { "id": 5, "serial_number": "GLOVE0001AA", "status": "online" },
  "session_start": "2026-02-18T14:22:00Z",
  "session_duration": "00:15:30",
  "created_at": "2026-02-18T14:22:00Z",
  "ml_prediction_severity": "moderate"
}
```

### Patient Create/Edit Request Body

```json
{
  "full_name": "Ahmed Hassan",
  "date_of_birth": "1958-03-12",
  "contact_phone": "+201234567890",
  "contact_email": "ahmed@example.com",
  "medical_notes": "Moderate Parkinson's, right hand dominant tremor."
}
```

---

## Frontend State Shapes

### usePatients hook
```js
{
  patients: Array<PatientListItem> | [],
  totalCount: number,
  currentPage: number,
  totalPages: number,
  loading: boolean,
  error: string | null,
  search: string,            // current search term
  setSearch: (s) => void,
  setPage: (n) => void,
}
```

### usePatient hook
```js
{
  patient: PatientDetail | null,
  sessions: Array<SessionHistoryItem> | [],
  sessionCount: number,
  sessionPage: number,
  sessionTotalPages: number,
  loading: boolean,
  sessionsLoading: boolean,
  error: string | null,
  setSessionPage: (n) => void,
}
```
