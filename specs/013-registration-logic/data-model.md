# Data Model: Update Registration Logic

**Feature**: 013-registration-logic
**Date**: 2026-02-18

## No Model Changes

This feature involves no changes to database models or entities. All model-level changes were completed in E-1.1.

---

## Serializer Changes

### RegisterSerializer (authentication.serializers.RegisterSerializer)

**File**: `backend/authentication/serializers.py`
**Change type**: Bug fix in `create()` method

| Method | Before | After |
|--------|--------|-------|
| `create()` | `role=validated_data['role']` — raises `KeyError` when role omitted | `role=validated_data.get('role', 'doctor')` — defaults to `'doctor'` |

#### Why this is a bug fix, not a new feature

When `role` is absent from the request:
1. DRF marks the `role` field as `required=False` (because the model has `default='doctor'`)
2. DRF does NOT populate a serializer-level default in `validated_data`
3. The `create()` method calls `validated_data['role']` → `KeyError`
4. Fix: use `.get('role', 'doctor')` to safely retrieve the role or fall back to the model default

---

## Validation Rules (Unchanged from E-1.1)

| Rule | Enforcement |
|------|-------------|
| `role` must be `doctor` or `admin` | DRF built-in `invalid_choice` + `validate_role()` custom message |
| Empty string `""` rejected | DRF built-in `invalid_choice` |
| Wrong case (e.g., `"Doctor"`) rejected | DRF built-in `invalid_choice` |
| Missing `role` → defaults to `doctor` | Fixed in this feature via `.get('role', 'doctor')` |
