# Quickstart: Remove Flex Fields from BiometricReading

**Branch**: `017-remove-flex-fields` | **Date**: 2026-02-18

This guide shows how to verify the feature is correctly implemented.

---

## Scenario 1: Verify the Model Has No Flex Fields

After implementation, confirm `BiometricReading` in `backend/biometrics/models.py` contains exactly 6 sensor fields and no flex fields.

**Check**:
```bash
grep -n "flex_" backend/biometrics/models.py
# Expected: no output (zero matches)
```

**Expected field list** on the model class:
```
patient, timestamp, aX, aY, aZ, gX, gY, gZ
```

---

## Scenario 2: Run the Migrations

```bash
cd backend
python manage.py migrate biometrics
```

**Expected output** (abbreviated):
```
Running migrations:
  Applying biometrics.0002_add_biometricreading... OK
  Applying biometrics.0003_remove_flex_fields... OK
```

---

## Scenario 3: Confirm Database Schema

After migrations, the `biometric_readings` table should have columns:
`id, patient_id, timestamp, aX, aY, aZ, gX, gY, gZ`

No `flex_1`, `flex_2`, `flex_3`, `flex_4`, or `flex_5` columns should exist.

**Django shell verification**:
```python
# python manage.py shell
from django.db import connection
columns = [col.name for col in connection.introspection.get_table_description(
    connection.cursor(), 'biometric_readings'
)]
print(columns)
# Expected: ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
assert 'flex_1' not in columns
assert 'flex_5' not in columns
print("PASS: No flex fields in database schema")
```

---

## Scenario 4: Create a BiometricReading Record

```python
# python manage.py shell
from biometrics.models import BiometricReading
from patients.models import Patient
from django.utils import timezone

patient = Patient.objects.first()  # assumes at least one patient exists
reading = BiometricReading.objects.create(
    patient=patient,
    timestamp=timezone.now(),
    aX=0.12, aY=-0.05, aZ=9.81,
    gX=0.01, gY=0.02, gZ=-0.01,
)
print(f"Created BiometricReading {reading.pk}")
# Expected: no errors, record saved with 6 sensor fields only
```

---

## Scenario 5: Migration Rollback (Optional Sanity Check)

```bash
cd backend
python manage.py migrate biometrics 0002  # roll back to before removal
python manage.py migrate biometrics       # re-apply 0003
```

**Expected**: Both directions succeed without errors.
