# Data Model: Update Patient API Permissions (E-1.4)

**Branch**: `015-patient-permissions`
**Date**: 2026-02-18

---

## Overview

This feature introduces **no database schema changes**. All Patient, DoctorPatientAssignment, and CustomUser models remain unchanged. The change is entirely in the permission and access-control layer.

---

## Permission Classes (before → after)

### `backend/authentication/permissions.py`

| Class | Before | After |
|-------|--------|-------|
| `IsDoctor` | Allows `role == 'doctor'` | **Unchanged** |
| `IsPatient` | Allows `role == 'patient'` | **Removed** (dead code — no patient role exists) |
| `IsDoctorOrAdmin` | Does not exist | **Added** — allows `role in ('doctor', 'admin')` |
| `IsOwnerOrDoctor` | Allows owner or doctor | **Unchanged** |

---

## ViewSet Access Rules (before → after)

### `PatientViewSet` in `backend/patients/views.py`

| Aspect | Before | After |
|--------|--------|-------|
| `permission_classes` | `[IsAuthenticated, IsDoctor]` | `[IsAuthenticated, IsDoctorOrAdmin]` |
| Admin `get_queryset()` | Returns `objects.none()` (blocked) | Returns `Patient.objects.all()` (full access) |
| Doctor `get_queryset()` | Returns scoped queryset | **Unchanged** |
| Other roles `get_queryset()` | Returns `objects.none()` | **Unchanged** |

---

## Access Matrix (after this change)

| User Role | Can Access Patient API | Patients Visible |
|-----------|----------------------|-----------------|
| `doctor` | Yes | Only created_by=self OR assigned to self |
| `admin` | Yes | All patients in the system |
| Any other / unauthenticated | No (401/403) | None |

---

## Entities (unchanged)

### Patient

No field changes. Remains a data-only model (no link to user accounts since E-1.3).

| Field | Type | Notes |
|-------|------|-------|
| `id` | Auto PK | |
| `full_name` | CharField | Required |
| `date_of_birth` | DateField | Required |
| `contact_phone` | CharField | Optional |
| `contact_email` | EmailField | Optional |
| `medical_notes` | TextField | Optional |
| `created_by` | FK → CustomUser | The doctor who created this record |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

### DoctorPatientAssignment (unchanged)

| Field | Type | Notes |
|-------|------|-------|
| `doctor` | FK → CustomUser | Must have `role == 'doctor'` |
| `patient` | FK → Patient | |
| `assigned_at` | DateTimeField | Auto |
| `assigned_by` | FK → CustomUser | nullable |

### CustomUser (unchanged)

No changes to the user model. `ROLE_CHOICES = [('doctor', 'Doctor'), ('admin', 'Admin')]` established in E-1.1.
