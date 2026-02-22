# Quickstart: Update Patient Model

**Feature**: 014-update-patient-model
**Date**: 2026-02-18

---

## Integration Scenarios

### Scenario 1: Create a patient without any user account (US1 + US2)

Doctors can create patient records with only clinical data — no user account needed or allowed.

**Request**:
```http
POST /api/patients/
Authorization: Bearer <doctor_jwt_token>
Content-Type: application/json

{
  "full_name": "Ahmed Al-Rashidi",
  "date_of_birth": "1965-03-22",
  "contact_phone": "+966501234567",
  "medical_notes": "Stage 2 Parkinson's. Right-hand tremor dominant."
}
```

**Expected Response (201)**:
```json
{
  "id": 1,
  "full_name": "Ahmed Al-Rashidi",
  "date_of_birth": "1965-03-22",
  "contact_phone": "+966501234567",
  "contact_email": "",
  "medical_notes": "Stage 2 Parkinson's. Right-hand tremor dominant.",
  "created_by": {
    "id": 5,
    "email": "dr.ali@hospital.com",
    "first_name": "Ali",
    "last_name": "Al-Farsi"
  },
  "created_at": "2026-02-18T10:00:00Z",
  "updated_at": "2026-02-18T10:00:00Z"
}
```

**Note**: No `user` field in the response. Patient records contain only clinical data.

---

### Scenario 2: Create a patient with only required fields

Phone and notes are optional.

**Request**:
```http
POST /api/patients/
Authorization: Bearer <doctor_jwt_token>
Content-Type: application/json

{
  "full_name": "Sara Khalid",
  "date_of_birth": "1972-08-15"
}
```

**Expected Response (201)**: Patient created with empty `contact_phone` and `medical_notes`. No error.

---

### Scenario 3: Retrieve a patient — no user field (US1)

**Request**:
```http
GET /api/patients/1/
Authorization: Bearer <doctor_jwt_token>
```

**Expected Response (200)**: Patient detail with `id`, `full_name`, `date_of_birth`, `contact_phone`, `contact_email`, `medical_notes`, `created_by`, timestamps. **No `user` field appears.**

---

### Scenario 4: Update patient clinical notes (US2)

**Request**:
```http
PATCH /api/patients/1/
Authorization: Bearer <doctor_jwt_token>
Content-Type: application/json

{
  "medical_notes": "Follow-up: tremor reduced after therapy. Next visit in 4 weeks."
}
```

**Expected Response (200)**: Patient detail with updated `medical_notes`. All other fields unchanged.

---

### Scenario 5: Doctor-patient assignment still works (US3)

**Request**:
```http
POST /api/patients/1/assign-doctor/
Authorization: Bearer <doctor_jwt_token>
Content-Type: application/json

{
  "doctor_id": 7
}
```

**Expected Response (201)**: Assignment created. The absence of a user account link on the patient does not affect assignment functionality.

---

### Scenario 6: Legacy data — patient record with previous user link is still accessible

If any patient records existed with a `user` field value before the migration, after the migration runs those records must still be fully readable with all clinical data intact. No data loss.

**Verification**: `GET /api/patients/{id}/` for a previously-linked patient returns the same `full_name`, `date_of_birth`, `contact_phone`, and `medical_notes` as before the migration. The response no longer contains a `user` field (it has been removed from the model and API).
