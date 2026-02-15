# Quickstart Guide: Core Backend APIs

**Feature**: 001-core-backend-apis
**Date**: 2026-02-15
**Purpose**: Test scenarios and usage examples for TremoAI backend APIs

## Prerequisites

- Django backend running locally: `python manage.py runserver`
- Base URL: `http://localhost:8000/api`
- HTTP client (curl, Postman, or httpie)

## Test Scenario 1: User Registration and Authentication (US1)

### Step 1: Register a Doctor Account

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dr.smith@hospital.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Smith",
    "role": "doctor"
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": 1,
  "email": "dr.smith@hospital.com",
  "first_name": "John",
  "last_name": "Smith",
  "role": "doctor",
  "date_joined": "2026-02-15T10:30:00Z"
}
```

### Step 2: Login to Get JWT Tokens

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dr.smith@hospital.com",
    "password": "SecurePass123!"
  }'
```

**Expected Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "dr.smith@hospital.com",
    "first_name": "John",
    "last_name": "Smith",
    "role": "doctor"
  }
}
```

**Save the access token** for subsequent requests.

### Step 3: Test JWT Authentication

```bash
curl -X GET http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

**Expected Response** (200 OK - empty list initially):
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

### Step 4: Test Invalid Token (Unauthorized)

```bash
curl -X GET http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer invalid_token"
```

**Expected Response** (401 Unauthorized):
```json
{
  "error": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

---

## Test Scenario 2: Patient Profile Management (US2)

**Prerequisites**: Doctor authenticated from Scenario 1

### Step 1: Create Patient Record

```bash
curl -X POST http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe",
    "date_of_birth": "1965-03-15",
    "contact_phone": "+1234567890",
    "contact_email": "jane.doe@example.com",
    "medical_notes": "Diagnosed with Parkinsons in 2020. Tremors primarily in right hand."
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": 1,
  "full_name": "Jane Doe",
  "date_of_birth": "1965-03-15",
  "contact_phone": "+1234567890",
  "contact_email": "jane.doe@example.com",
  "medical_notes": "Diagnosed with Parkinsons in 2020. Tremors primarily in right hand.",
  "assigned_doctors": [],
  "paired_device": null,
  "created_by": {
    "id": 1,
    "email": "dr.smith@hospital.com"
  },
  "created_at": "2026-02-15T10:35:00Z",
  "updated_at": "2026-02-15T10:35:00Z"
}
```

### Step 2: List Patients

```bash
curl -X GET http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "full_name": "Jane Doe",
      "date_of_birth": "1965-03-15",
      "contact_email": "jane.doe@example.com",
      "created_at": "2026-02-15T10:35:00Z"
    }
  ]
}
```

### Step 3: Update Patient Record

```bash
curl -X PUT http://localhost:8000/api/patients/1/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "medical_notes": "Updated: Patient responded well to medication adjustment."
  }'
```

**Expected Response** (200 OK - full patient object with updated notes)

### Step 4: Search Patients by Name

```bash
curl -X GET "http://localhost:8000/api/patients/search/?name=jane" \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK - list of patients matching "jane")

### Step 5: Assign Another Doctor to Patient

First, register and login as a second doctor to get their ID. Then:

```bash
curl -X POST http://localhost:8000/api/patients/1/assign-doctor/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": 2
  }'
```

**Expected Response** (201 Created):
```json
{
  "doctor_id": 2,
  "patient_id": 1,
  "assigned_at": "2026-02-15T10:40:00Z"
}
```

---

## Test Scenario 3: Device Registration and Pairing (US3)

**Prerequisites**: Patient created from Scenario 2

### Step 1: Register Device

```bash
curl -X POST http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "serial_number": "GLV123456789"
  }'
```

**Expected Response** (201 Created):
```json
{
  "id": 1,
  "serial_number": "GLV123456789",
  "status": "offline",
  "last_seen": null,
  "patient": null,
  "registered_by": {
    "id": 1,
    "email": "dr.smith@hospital.com"
  },
  "registered_at": "2026-02-15T10:45:00Z"
}
```

### Step 2: Pair Device to Patient

```bash
curl -X POST http://localhost:8000/api/devices/1/pair/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1
  }'
```

**Expected Response** (200 OK):
```json
{
  "device_id": 1,
  "patient_id": 1,
  "paired_at": "2026-02-15T10:46:00Z",
  "previous_patient_id": null
}
```

### Step 3: Update Device Status to Online

```bash
curl -X PUT http://localhost:8000/api/devices/1/status/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "online"
  }'
```

**Expected Response** (200 OK):
```json
{
  "device_id": 1,
  "status": "online",
  "last_seen": "2026-02-15T10:47:00Z"
}
```

### Step 4: View Device with Patient Info

```bash
curl -X GET http://localhost:8000/api/devices/1/ \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK):
```json
{
  "id": 1,
  "serial_number": "GLV123456789",
  "status": "online",
  "last_seen": "2026-02-15T10:47:00Z",
  "patient": {
    "id": 1,
    "full_name": "Jane Doe",
    "contact_email": "jane.doe@example.com"
  },
  "registered_by": {
    "id": 1,
    "email": "dr.smith@hospital.com"
  },
  "registered_at": "2026-02-15T10:45:00Z"
}
```

### Step 5: Test Device Re-Pairing (Switch Patients)

Create a second patient, then:

```bash
curl -X POST http://localhost:8000/api/devices/1/pair/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 2
  }'
```

**Expected Response** (200 OK):
```json
{
  "device_id": 1,
  "patient_id": 2,
  "paired_at": "2026-02-15T10:50:00Z",
  "previous_patient_id": 1
}
```

---

## Test Scenario 4: Biometric Data Storage and Retrieval (US4)

**Prerequisites**: Device paired to patient from Scenario 3

### Step 1: Store Biometric Session Data

```bash
curl -X POST http://localhost:8000/api/biometric-sessions/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "device_id": 1,
    "session_start": "2026-02-15T11:00:00Z",
    "session_duration": "PT5M30S",
    "sensor_data": {
      "tremor_intensity": [0.5, 0.7, 0.6, 0.8, 0.9, 0.7, 0.6, 0.5],
      "timestamps": [0, 20, 40, 60, 80, 100, 120, 140],
      "frequency": 50,
      "metadata": {
        "firmware_version": "1.2.3",
        "battery_level": 85
      }
    }
  }'
```

**Expected Response** (201 Created - full session object)

### Step 2: Retrieve Sessions by Date Range

```bash
curl -X GET "http://localhost:8000/api/biometric-sessions/?patient_id=1&start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK):
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "patient": {
        "id": 1,
        "full_name": "Jane Doe"
      },
      "device": {
        "id": 1,
        "serial_number": "GLV123456789"
      },
      "session_start": "2026-02-15T11:00:00Z",
      "session_duration": "PT5M30S",
      "created_at": "2026-02-15T11:05:35Z"
    }
  ]
}
```

### Step 3: Get Full Session Details with Sensor Data

```bash
curl -X GET http://localhost:8000/api/biometric-sessions/1/ \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK - includes full sensor_data JSON)

### Step 4: Get Aggregated Metrics

```bash
curl -X GET "http://localhost:8000/api/biometric-sessions/aggregate/?patient_id=1&start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer {access_token}"
```

**Expected Response** (200 OK):
```json
{
  "patient_id": 1,
  "date_range": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28"
  },
  "metrics": {
    "session_count": 1,
    "total_duration": "PT5M30S",
    "average_tremor_intensity": 0.675,
    "min_tremor_intensity": 0.5,
    "max_tremor_intensity": 0.9
  }
}
```

### Step 5: Test Device-Patient Pairing Validation

Try to store data for unpaired device:

```bash
curl -X POST http://localhost:8000/api/biometric-sessions/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "device_id": 999,
    "session_start": "2026-02-15T12:00:00Z",
    "session_duration": "PT5M",
    "sensor_data": {...}
  }'
```

**Expected Response** (400 Bad Request):
```json
{
  "error": "Device not found",
  "code": "not_found"
}
```

---

## Test Scenario 5: Role-Based Access Control

### Step 1: Register Patient User Account

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.doe@example.com",
    "password": "PatientPass123!",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "patient"
  }'
```

### Step 2: Login as Patient

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.doe@example.com",
    "password": "PatientPass123!"
  }'
```

**Save patient access token**

### Step 3: Test Patient Can't Create Patients

```bash
curl -X POST http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {patient_access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Patient",
    "date_of_birth": "1970-01-01"
  }'
```

**Expected Response** (403 Forbidden):
```json
{
  "error": "You do not have permission to perform this action",
  "code": "permission_denied"
}
```

### Step 4: Test Patient Can View Own Data

Link patient user to patient profile (in implementation), then:

```bash
curl -X GET http://localhost:8000/api/biometric-sessions/?patient_id=1 \
  -H "Authorization: Bearer {patient_access_token}"
```

**Expected Response** (200 OK - patient's own data only)

---

## Integration Test Workflow

Complete end-to-end workflow:

1. **Doctor registers** → Gets JWT tokens
2. **Doctor creates patient** → Patient ID = 1
3. **Doctor registers device** → Device ID = 1
4. **Doctor pairs device to patient** → Device linked to Patient
5. **Device goes online** → Status updated to "online"
6. **Device transmits sensor data** → Biometric session created
7. **Doctor retrieves patient data** → Views sessions and aggregations
8. **Patient registers** → Gets JWT tokens
9. **Patient views own data** → Sees only own biometric sessions
10. **Patient attempts to view other patient** → 403 Forbidden

---

## Error Scenarios to Test

### Duplicate Email Registration

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dr.smith@hospital.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Smith",
    "role": "doctor"
  }'
```

**Expected**: 400 Bad Request - "User with this email already exists"

### Invalid JWT Token

```bash
curl -X GET http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer invalid_token_here"
```

**Expected**: 401 Unauthorized - "Given token not valid"

### Expired JWT Token

Wait 24 hours or manually set short expiry in settings, then:

```bash
curl -X GET http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {expired_token}"
```

**Expected**: 401 Unauthorized - "Token is expired"

### Missing Required Fields

```bash
curl -X POST http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "date_of_birth": "1970-01-01"
  }'
```

**Expected**: 400 Bad Request - "full_name: This field is required"

### Future Date of Birth

```bash
curl -X POST http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Patient",
    "date_of_birth": "2030-01-01"
  }'
```

**Expected**: 400 Bad Request - "Date of birth cannot be in the future"

---

## Performance Testing

### Test Pagination

Create 100 patients, then:

```bash
curl -X GET "http://localhost:8000/api/patients/?page=1&page_size=20" \
  -H "Authorization: Bearer {access_token}"
```

**Expected**: 200 OK with 20 patients and pagination links

### Test Date Range Query Performance

Store 1000 biometric sessions, then query date range:

```bash
time curl -X GET "http://localhost:8000/api/biometric-sessions/?patient_id=1&start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer {access_token}"
```

**Expected**: Response time < 2 seconds (per spec success criteria SC-007)

---

## Next Steps

After validating all scenarios:

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Execute tasks via `/speckit.implement`
3. Run integration tests to validate all acceptance scenarios
4. Frontend integration (separate feature)
