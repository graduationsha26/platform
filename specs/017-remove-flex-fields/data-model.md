# Data Model: Remove Flex Fields from BiometricReading

**Branch**: `017-remove-flex-fields` | **Date**: 2026-02-18
**Phase**: 1 — Entity design from spec + research

---

## Entity: BiometricReading (Django Model)

**Location**: `backend/biometrics/models.py`
**Database table**: `biometric_readings`

### Final Field Definition (after E-2.1)

| Field       | Type             | Constraints             | Description                        |
|-------------|------------------|-------------------------|------------------------------------|
| `id`        | BigAutoField     | PK, auto               | Django default primary key         |
| `patient`   | ForeignKey       | → patients.Patient, CASCADE | Patient this reading belongs to |
| `timestamp` | DateTimeField    | not null                | UTC timestamp of sensor reading    |
| `aX`        | FloatField       | not null                | Accelerometer X-axis value         |
| `aY`        | FloatField       | not null                | Accelerometer Y-axis value         |
| `aZ`        | FloatField       | not null                | Accelerometer Z-axis value         |
| `gX`        | FloatField       | not null                | Gyroscope X-axis value             |
| `gY`        | FloatField       | not null                | Gyroscope Y-axis value             |
| `gZ`        | FloatField       | not null                | Gyroscope Z-axis value             |

**Fields explicitly excluded** (the subject of this feature):

| Field    | Why excluded |
|----------|-------------|
| `flex_1` | Unused placeholder — no sensor maps to this field |
| `flex_2` | Unused placeholder — no sensor maps to this field |
| `flex_3` | Unused placeholder — no sensor maps to this field |
| `flex_4` | Unused placeholder — no sensor maps to this field |
| `flex_5` | Unused placeholder — no sensor maps to this field |

### Validation Rules

- All 6 sensor fields (`aX`, `aY`, `aZ`, `gX`, `gY`, `gZ`) must be non-null numerics (enforced by `FloatField`)
- `patient` FK must reference an existing `Patient` record
- `timestamp` must be a valid datetime (past or present)

### Indexes

```python
class Meta:
    db_table = 'biometric_readings'
    ordering = ['-timestamp']
    indexes = [
        models.Index(fields=['patient', 'timestamp']),
        models.Index(fields=['timestamp']),
    ]
```

### Relationships

- `BiometricReading` → `Patient` (ForeignKey, many-to-one): many readings per patient
- `BiometricReading` is independent of `BiometricSession` — it represents individual MQTT-sourced sensor samples, not aggregated sessions

---

## Migration Plan

### Migration 0002: `0002_add_biometricreading.py`

**Purpose**: Creates the `BiometricReading` model including the five flex placeholder fields (transitional state).

**Operations**:
```python
migrations.CreateModel(
    name='BiometricReading',
    fields=[
        ('id', models.BigAutoField(..., primary_key=True)),
        ('patient', models.ForeignKey('patients.Patient', ...)),
        ('timestamp', models.DateTimeField()),
        ('aX', models.FloatField()),
        ('aY', models.FloatField()),
        ('aZ', models.FloatField()),
        ('gX', models.FloatField()),
        ('gY', models.FloatField()),
        ('gZ', models.FloatField()),
        ('flex_1', models.FloatField()),
        ('flex_2', models.FloatField()),
        ('flex_3', models.FloatField()),
        ('flex_4', models.FloatField()),
        ('flex_5', models.FloatField()),
    ],
    options={
        'db_table': 'biometric_readings',
        'ordering': ['-timestamp'],
    },
)
```

### Migration 0003: `0003_remove_flex_fields.py` ← **E-2.1 deliverable**

**Purpose**: Drops `flex_1` through `flex_5` columns — the formal removal migration.

**Operations**:
```python
migrations.RemoveField(model_name='biometricreading', name='flex_1'),
migrations.RemoveField(model_name='biometricreading', name='flex_2'),
migrations.RemoveField(model_name='biometricreading', name='flex_3'),
migrations.RemoveField(model_name='biometricreading', name='flex_4'),
migrations.RemoveField(model_name='biometricreading', name='flex_5'),
```

**Dependency**: `('biometrics', '0002_add_biometricreading')`

---

## State Transitions

```
Model created (with flex fields, migration 0002)
    ↓
Migration 0003 applied
    ↓
BiometricReading (clean — 6 sensor fields only)
    ↓
Sensor readings stored via MQTT ingestion
```

---

## Storage Estimate

| State               | Row size (approx) | Notes                            |
|---------------------|-------------------|----------------------------------|
| With flex fields    | ~120 bytes        | 11 FloatFields + id + FK + ts    |
| After E-2.1         | ~80 bytes         | 6 FloatFields + id + FK + ts     |
| Savings per row     | ~40 bytes (33%)   | 5 × 8-byte double precision cols |
