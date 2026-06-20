# Quickstart: Update User Model Roles

**Feature**: 012-update-user-roles
**Date**: 2026-02-18

## Integration Scenarios

### Scenario 1: Register a Doctor (Default Role)

After this change, creating a doctor account no longer requires explicitly passing `role`.

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

### Scenario 2: Register an Admin

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

### Scenario 3: Rejected Patient Role Registration

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

## Migration Steps

When applying this feature to the Supabase PostgreSQL database:

```bash
# From backend/ directory:
python manage.py makemigrations authentication
python manage.py migrate
```

The migration updates the `role` field choices and adds the `'doctor'` default. No existing data is modified.

---

## JWT Token Payload After Change

JWT tokens now include `role` values of `doctor` or `admin` only:

```json
{
  "token_type": "access",
  "user_id": 1,
  "email": "dr.smith@hospital.com",
  "role": "doctor",
  "first_name": "John",
  "last_name": "Smith"
}
```

---

## Checking Role in Code (Updated Helpers)

```python
# Available after this feature:
user.is_doctor()   # True if role == 'doctor'
user.is_admin()    # True if role == 'admin'  (NEW)

# Removed after this feature:
# user.is_patient()  -- no longer exists
```
