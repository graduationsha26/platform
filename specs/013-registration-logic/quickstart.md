# Quickstart: Update Registration Logic

**Feature**: 013-registration-logic
**Date**: 2026-02-18

## Integration Scenarios

### Scenario 1: Register without specifying role (defaults to doctor)

**Request**:
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "dr.smith@hospital.com",
  "first_name": "John",
  "last_name": "Smith",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**Expected Response (201)**:
```json
{
  "id": 1,
  "email": "dr.smith@hospital.com",
  "first_name": "John",
  "last_name": "Smith",
  "role": "doctor",
  "date_joined": "2026-02-18T10:00:00Z"
}
```

---

### Scenario 2: Register as doctor (explicit)

**Request**:
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "dr.jones@hospital.com",
  "first_name": "Jane",
  "last_name": "Jones",
  "role": "doctor",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**Expected Response (201)**: Same as Scenario 1 with role `doctor`.

---

### Scenario 3: Register as admin

**Request**:
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "admin@tremoai.com",
  "first_name": "Platform",
  "last_name": "Admin",
  "role": "admin",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**Expected Response (201)**:
```json
{
  "id": 2,
  "email": "admin@tremoai.com",
  "first_name": "Platform",
  "last_name": "Admin",
  "role": "admin",
  "date_joined": "2026-02-18T10:01:00Z"
}
```

---

### Scenario 4: Patient role rejected

**Request**:
```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "patient@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "patient",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**Expected Response (400)**:
```json
{
  "role": ["Role must be either 'doctor' or 'admin'."]
}
```

---

### Scenario 5: Wrong case rejected

**Request**: `role: "Doctor"`

**Expected Response (400)**:
```json
{
  "role": ["\"Doctor\" is not a valid choice."]
}
```
