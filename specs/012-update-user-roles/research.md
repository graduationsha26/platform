# Research: Update User Model Roles

**Feature**: 012-update-user-roles
**Date**: 2026-02-18
**Status**: Complete — no external unknowns

## Decision Log

### D-001: Role Choices Final Set

**Decision**: Valid roles will be `doctor` (display: "Doctor") and `admin` (display: "Admin").

**Rationale**: Directly specified in the feature description. Patients are not direct users of the TremoAI web platform (they use the wearable hardware). The `admin` role is added for platform administration.

**Alternatives considered**: None — this is a prescribed change.

---

### D-002: Default Role Value

**Decision**: `default='doctor'` added to the `role` field on `CustomUser`.

**Rationale**: Directly specified in the feature description. Doctors are the primary users of the platform; defaulting to `doctor` simplifies account creation for the common case.

**Alternatives considered**: `default='admin'` — rejected because admin is a privileged role and should not be assigned by default.

---

### D-003: Migration Strategy

**Decision**: Use `AlterField` migration to update the `choices` list and add `default` on the `role` CharField.

**Rationale**: Django's choices list is a Python-level validation constraint, not a database-level constraint. Changing `choices` alone does not alter the database schema. However, adding `default=` does register in migrations. A single `AlterField` migration handles both.

**Alternatives considered**:
- Edit `0001_initial.py` directly — rejected because the database is already created (Supabase PostgreSQL remote). Editing the initial migration would break `migrate` for fresh environments.
- `RunSQL` with data migration — not needed as no existing data must be patched within this feature's scope.

---

### D-004: Scope of `role == 'patient'` Code References

**Decision**: Scope of this feature is limited to the `authentication` app only:
- `authentication/models.py` — update `ROLE_CHOICES`, `default`, remove `is_patient()`, update/rename `is_patient()` to reflect the new role set.
- `authentication/serializers.py` — update `validate_role` to accept `doctor` and `admin`.
- `authentication/migrations/` — create new `AlterField` migration.

**Out of scope** (handled in a follow-up feature):
- `analytics/views.py` — 2 references to `user.role == 'patient'` (dead branches after this change).
- `biometrics/views.py` — 2 references to `user.role == 'patient'`.
- `realtime/consumers.py` — 1 reference to `user.role == 'patient'`.
- `authentication/permissions.py` — `IsPatient`, `IsOwnerOrDoctor` classes.
- `authentication/management/commands/create_test_users.py` — creates test users with `patient` role.
- `backend/create_test_users.py` — creates test users with `patient` role.

**Rationale**: The spec scopes the change to the User model roles only. Dead-branch cleanup in other apps is a separate concern. Those branches will simply never match after the role is removed but will not cause runtime errors.

---

### D-005: `is_patient()` Method

**Decision**: Remove `is_patient()` method from `CustomUser`. Optionally add `is_admin()` helper.

**Rationale**: `is_patient()` returns `self.role == 'patient'` which will always be `False` after the role is removed. Keeping it is misleading. An `is_admin()` helper is the natural counterpart to `is_doctor()`.

**Alternatives considered**: Keep `is_patient()` returning `False` always — rejected as dead code and misleading.

---

### D-006: `max_length` on Role Field

**Decision**: Keep `max_length=10`. Both `doctor` (6 chars) and `admin` (5 chars) fit within this limit.

**Rationale**: No change needed. Increasing `max_length` would require an additional unnecessary migration.

---

### D-007: `REQUIRED_FIELDS` on CustomUser

**Decision**: Keep `role` in `REQUIRED_FIELDS` for management commands (`createsuperuser`).

**Rationale**: Even though a default is added, keeping `role` in `REQUIRED_FIELDS` ensures administrators explicitly confirm the role when using management commands. This is a safety measure.

**Note**: With `default='doctor'` on the field, the `role` field is no longer strictly required at the database level, but the management command still prompts for it.

---

### D-008: Constitution Amendment

**Decision**: The constitution (Principle IV) must be updated to reflect the new role set.

**Rationale**: Constitution IV states "Two roles: `patient` and `doctor`". This feature changes the valid roles to `doctor` and `admin`. The constitution must be updated as part of the implementation to keep documentation consistent.

**Action**: Update `.specify/memory/constitution.md` Principle IV to state "Two roles: `doctor` and `admin`".
