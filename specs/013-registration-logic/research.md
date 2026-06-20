# Research: Update Registration Logic

**Feature**: 013-registration-logic
**Date**: 2026-02-18
**Status**: Complete

## Current State Analysis

This feature overlaps with E-1.1 (Update User Model Roles). Before planning implementation, the current serializer behaviour was inspected to determine what is already done and what remains.

### What E-1.1 Already Completed

| Concern | Status | Detail |
|---------|--------|--------|
| `ROLE_CHOICES` restricted to doctor/admin | ✅ Done | E-1.1 T001 |
| `validate_role()` rejects `patient` | ✅ Done | E-1.1 T003 |
| Model `default='doctor'` | ✅ Done | E-1.1 T004 |
| Migration applied | ✅ Done | E-1.1 T005/T006 |

### Gap Identified: `create()` Method KeyError on Omitted Role

**Finding**: Runtime inspection of `RegisterSerializer` confirms:
- `role` field is `required=False` (DRF picks this up from the model's `default='doctor'`)
- However, the DRF-level `default` for the field is `empty` — NOT `'doctor'`
- When `role` is omitted from a request, `validated_data` does NOT contain `role`
- The current `create()` method calls `role=validated_data['role']` which will raise `KeyError`

**Reproduction**: `RegisterSerializer(data={...no role...}).is_valid()` → `validated_data` keys = `['email', 'password', 'password_confirm', 'first_name', 'last_name']` — `role` absent.

**Impact**: US2 (default to doctor when role omitted) is currently broken at the API level even though the model default is set correctly.

---

## Decision Log

### D-001: Fix Strategy for Default Role in `create()`

**Decision**: Change `role=validated_data['role']` to `role=validated_data.get('role', 'doctor')` in `RegisterSerializer.create()`.

**Rationale**: This is the minimal, correct fix. It mirrors the model default and handles the case where role is absent from `validated_data`. No other changes are needed.

**Alternatives considered**:
- Set explicit `default='doctor'` on the serializer `role` field in `extra_kwargs` — this would work but requires understanding DRF's field-level vs validated_data defaults. The `.get()` fix is simpler and achieves the same result.
- Add `role` to `REQUIRED_FIELDS` in `extra_kwargs` to force it to always be present — rejected because this would break US2 (we want role to be optional).

---

### D-002: `validate_role()` vs Built-in Choices Validation

**Finding**: DRF's built-in choices validation already rejects values not in `ROLE_CHOICES` with an `invalid_choice` error before `validate_role()` is even called. So `validate_role()` only adds a custom error message for values that are in neither the choices nor the built-in rejection.

**Decision**: Keep `validate_role()` for its cleaner, domain-specific error message (`"Role must be either 'doctor' or 'admin'."`) but note it is supplementary to built-in validation.

**Verification**:
- `role: ""` → `'"" is not a valid choice.'` (built-in choices validation)
- `role: "Doctor"` → `'"Doctor" is not a valid choice.'` (built-in choices validation)
- `role: "patient"` → `"Role must be either 'doctor' or 'admin'."` (validate_role — patient is no longer in choices, so built-in would catch it too, but validate_role fires first due to field-level validation order)

---

### D-003: Scope Boundary

**Decision**: E-1.2 implementation is confined to one line change in `RegisterSerializer.create()`. All other requirements are already met.

**Rationale**: The spec's FR-001 through FR-005 are all satisfied by E-1.1 + built-in DRF validation, EXCEPT for FR-002 (default role when none provided), which has the KeyError bug.

**Out of scope**: No view changes, no URL changes, no frontend changes.
