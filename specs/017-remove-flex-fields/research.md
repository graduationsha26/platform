# Research: Remove Flex Fields from BiometricReading

**Branch**: `017-remove-flex-fields` | **Date**: 2026-02-18
**Phase**: 0 — Resolve unknowns before design

---

## R-001: BiometricReading Model — Current State

**Question**: Does the `BiometricReading` model exist in the codebase? Where does it live?

**Finding**: As of 2026-02-18, `backend/biometrics/models.py` contains only `BiometricSession`. No `BiometricReading` model exists anywhere in `backend/`. No migration references it. No Python file imports or uses it.

**Decision**: The `BiometricReading` model must be **created** in `backend/biometrics/models.py` as part of this feature (or the preceding Epic 2 task). Feature 011 (`raw-feature-pipeline`) designed the model with 6 sensor fields (`aX, aY, aZ, gX, gY, gZ`). This feature (E-2.1) ensures the model is created *without* `flex_1..flex_5` and that a migration formally captures the removal of those placeholder fields.

**Rationale**: Adding the model to the existing `biometrics` app is consistent with the project structure — it already owns `BiometricSession` and all biometric data concerns.

**Alternatives considered**:
- Separate `readings` Django app: Rejected — unnecessary app proliferation; biometric readings belong with biometric sessions.
- Adding to `patients` app: Rejected — violates single-responsibility; patients app manages patient profiles, not raw sensor data.

---

## R-002: Django Migration Strategy for Dropping Columns

**Question**: What is the correct Django migration pattern to drop `flex_1` through `flex_5` columns from Supabase PostgreSQL?

**Finding**: Django provides `migrations.RemoveField` as the standard operation for dropping a model field and its corresponding database column. For 5 fields, 5 `RemoveField` operations are grouped into a single migration file.

**Decision**: Use `migrations.RemoveField` for each of the 5 flex fields in a single migration file. This is atomic at the Django migration level (all 5 drops happen in one migration transaction).

**Migration pattern**:
```python
class Migration(migrations.Migration):
    dependencies = [
        ('biometrics', '0002_add_biometricreading'),
    ]
    operations = [
        migrations.RemoveField(model_name='biometricreading', name='flex_1'),
        migrations.RemoveField(model_name='biometricreading', name='flex_2'),
        migrations.RemoveField(model_name='biometricreading', name='flex_3'),
        migrations.RemoveField(model_name='biometricreading', name='flex_4'),
        migrations.RemoveField(model_name='biometricreading', name='flex_5'),
    ]
```

**Rationale**: Single migration = single database transaction on PostgreSQL. If any `RemoveField` fails, the entire migration rolls back, satisfying FR-003 (atomic).

**Alternatives considered**:
- Raw SQL `ALTER TABLE DROP COLUMN`: Rejected — bypasses Django migration history, breaks `migrate --check` and future squash operations.
- Separate migration per field: Rejected — 5 separate migrations for 5 trivial drops is unnecessary overhead; grouping them is cleaner.
- Making fields nullable first, then dropping: Rejected — not needed when removing fields entirely; nullable-first is a safety pattern for data migration, not field removal.

---

## R-003: Code Reference Audit — Stale flex Field References

**Question**: Are there any code references to `flex_1` through `flex_5` in the backend that must be removed before the migration?

**Finding**: A comprehensive `grep` across all `backend/` Python files for `flex_1`, `flex_2`, `flex_3`, `flex_4`, `flex_5`, and `BiometricReading` returned **zero matches**. The BiometricReading model does not yet exist, and no flex field references exist anywhere in the codebase.

**Decision**: No stale reference cleanup is required at this time. The model will be created clean (without flex fields). The E-2.1 migration formally documents the removal for traceability.

**Rationale**: Since no model and no references exist, the "removal" is implemented as: (1) create the model *without* flex fields, and (2) if the preceding Epic 2 task creates the model *with* flex fields first, run the `RemoveField` migration immediately after.

**Alternatives considered**:
- Skip the RemoveField migration entirely (model created clean): This is valid but violates the spec requirement "Create and run migration" — the migration provides explicit traceability that flex fields were considered and formally excluded.

---

## R-004: Two-Migration vs. One-Migration Strategy

**Question**: Should this be a single migration (create model without flex fields) or two migrations (create with flex fields → remove flex fields)?

**Finding**: The task description explicitly says "Remove flex_1 through flex_5 FloatFields from BiometricReading model. Create and run migration." This implies the migration's *purpose* is removal — not initial creation.

**Decision**: **Two-migration strategy**:
1. `0002_add_biometricreading.py`: Creates the `BiometricReading` model including `flex_1..flex_5` (as the "before state" this feature cleans up)
2. `0003_remove_flex_fields.py`: Drops `flex_1..flex_5` (the actual E-2.1 deliverable)

This approach:
- Satisfies "Create and run migration" (the `0003` migration IS the removal migration)
- Provides a clean git history showing the flex fields were explicitly added then removed
- Matches the spec's intent: a formal migration to document the schema cleanup

**Alternatives considered**:
- Create model clean (no flex fields at all): Simpler, but doesn't satisfy "Create and run migration to REMOVE flex fields" — there's nothing to remove if they were never added.

---

## Summary of Decisions

| Research | Decision |
|----------|----------|
| R-001 | Add `BiometricReading` to `backend/biometrics/models.py` |
| R-002 | Use `migrations.RemoveField` × 5 in a single migration file |
| R-003 | No stale reference cleanup needed; no existing references found |
| R-004 | Two-migration strategy: create with flex fields → remove via `0003` |
