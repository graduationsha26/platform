# Data Model: Update User Model Roles

**Feature**: 012-update-user-roles
**Date**: 2026-02-18

## Modified Entities

### CustomUser (authentication.models.CustomUser)

**File**: `backend/authentication/models.py`
**Change type**: Field update + method removal

#### Field Changes

| Field | Before | After |
|-------|--------|-------|
| `role` choices | `[('doctor', 'Doctor'), ('patient', 'Patient')]` | `[('doctor', 'Doctor'), ('admin', 'Admin')]` |
| `role` default | *(none)* | `'doctor'` |
| `role` help_text | `'User role: doctor or patient'` | `'User role: doctor or admin'` |

#### Method Changes

| Method | Before | After |
|--------|--------|-------|
| `is_doctor()` | Returns `self.role == 'doctor'` | No change |
| `is_patient()` | Returns `self.role == 'patient'` | **Removed** |
| `is_admin()` | *(did not exist)* | **Added**: Returns `self.role == 'admin'` |

#### Unchanged Fields

All other fields (`email`, `first_name`, `last_name`, `is_superuser`, `is_staff`, `is_active`, `date_joined`, `last_login`, `groups`, `user_permissions`) remain unchanged.

#### REQUIRED_FIELDS

`REQUIRED_FIELDS = ['first_name', 'last_name', 'role']` — unchanged.

---

## Serializer Changes

### RegisterSerializer (authentication.serializers.RegisterSerializer)

**File**: `backend/authentication/serializers.py`
**Change type**: Validation update

| Method | Before | After |
|--------|--------|-------|
| `validate_role` | Accepts `'doctor'` or `'patient'` | Accepts `'doctor'` or `'admin'` |

---

## Migration

### 0002_alter_customuser_role

**File**: `backend/authentication/migrations/0002_alter_customuser_role.py`
**Type**: `AlterField`

Changes on the `role` field:
- `choices` updated to `[('doctor', 'Doctor'), ('admin', 'Admin')]`
- `default` added: `'doctor'`
- `help_text` updated: `'User role: doctor or admin'`

> Note: Django `choices` validation is Python-level only; no database constraint changes. The `default` addition is schema-registered by Django but PostgreSQL already has no NOT NULL constraint issue since existing rows already have valid data.

---

## Validation Rules

| Rule | Constraint |
|------|------------|
| `role` must be one of the valid choices | Enforced at model level (Django choices) and serializer level (`validate_role`) |
| `role` defaults to `'doctor'` if not provided | Enforced at model level via `default='doctor'` |
| `patient` is rejected as an invalid role | Enforced by updated `validate_role` in `RegisterSerializer` |
