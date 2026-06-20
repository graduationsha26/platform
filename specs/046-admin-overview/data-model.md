# Data Model: Admin Global Overview

**Branch**: `046-admin-overview`

---

## No New Entities

This feature introduces no new database tables or model fields. All data is derived from existing models using aggregate counts.

---

## Existing Models Used (Read-Only)

### CustomUser (`backend/authentication/models.py`)

| Field  | Type        | Notes                                   |
|--------|-------------|------------------------------------------|
| `id`   | AutoField   | Primary key                              |
| `role` | CharField   | `'doctor'` or `'admin'` (used to filter) |

**Usage**: `CustomUser.objects.filter(role='doctor').count()` → `total_doctors`

### Patient (`backend/patients/models.py`)

| Field | Type      | Notes                        |
|-------|-----------|------------------------------|
| `id`  | AutoField | Primary key (counted only)   |

**Usage**: `Patient.objects.count()` → `total_patients`

---

## API Response Shape

### `GET /api/analytics/admin-stats/`

```json
{
  "total_doctors": 5,
  "total_patients": 23
}
```

| Field           | Type    | Description                                      |
|-----------------|---------|--------------------------------------------------|
| `total_doctors` | integer | Count of all `CustomUser` records with role=doctor |
| `total_patients`| integer | Count of all `Patient` records in the system      |

Both values are always non-negative integers. The endpoint returns 0 counts (never null) when the system has no doctors or patients.
