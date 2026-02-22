# Data Model: Remove Flex Fields from BiometricReading API Layer

**Branch**: `018-clean-biometric-api` | **Date**: 2026-02-18
**Phase**: 1 — API layer design (no new database entities; model already exists from E-2.1)

---

## Serializer: BiometricReadingSerializer

**Location**: `backend/biometrics/serializers.py`
**Model**: `BiometricReading` (already exists in `backend/biometrics/models.py`)

### Fields

| Field        | Type    | Direction  | Description                        |
|--------------|---------|------------|------------------------------------|
| `id`         | integer | output     | Auto-generated primary key         |
| `patient_id` | integer | output     | Foreign key to Patient             |
| `timestamp`  | datetime| output     | UTC timestamp of sensor reading    |
| `aX`         | float   | output     | Accelerometer X-axis value         |
| `aY`         | float   | output     | Accelerometer Y-axis value         |
| `aZ`         | float   | output     | Accelerometer Z-axis value         |
| `gX`         | float   | output     | Gyroscope X-axis value             |
| `gY`         | float   | output     | Gyroscope Y-axis value             |
| `gZ`         | float   | output     | Gyroscope Z-axis value             |

**Fields explicitly excluded** (the subject of this feature):

| Field    | Why excluded |
|----------|-------------|
| `flex_1` | Removed from model in E-2.1 — not present, must not be added |
| `flex_2` | Removed from model in E-2.1 — not present, must not be added |
| `flex_3` | Removed from model in E-2.1 — not present, must not be added |
| `flex_4` | Removed from model in E-2.1 — not present, must not be added |
| `flex_5` | Removed from model in E-2.1 — not present, must not be added |

**All fields are read-only** — this serializer is used only for output (GET responses).

### Implementation Sketch

```python
class BiometricReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricReading
        fields = ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
        read_only_fields = fields
```

---

## ViewSet: BiometricReadingViewSet

**Location**: `backend/biometrics/views.py`
**Type**: Read-only (list + retrieve only)

### Operations

| Operation | HTTP Method | URL Pattern | Description |
|-----------|-------------|-------------|-------------|
| list      | GET         | `/api/biometric-readings/` | Returns paginated list of readings for accessible patients |
| retrieve  | GET         | `/api/biometric-readings/{id}/` | Returns a single reading by ID |

### Access Control

- **Authenticated**: JWT token required for all requests
- **Doctors**: See readings for all patients they created or are assigned to
- **Patients**: See only their own readings
- **Unauthenticated**: 401 Unauthorized

### Queryset Logic

```python
def get_queryset(self):
    user = self.request.user
    if user.role == 'doctor':
        accessible_patients = Patient.objects.filter(
            Q(created_by=user) | Q(doctor_assignments__doctor=user)
        ).distinct()
        return BiometricReading.objects.filter(
            patient__in=accessible_patients
        ).select_related('patient')
    # Patient role: own readings only
    return BiometricReading.objects.filter(
        patient__user=user
    ).select_related('patient')
```

### Implementation Sketch

```python
class BiometricReadingViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]
    serializer_class = BiometricReadingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient']

    def get_queryset(self):
        ...  # see above
```

---

## URL Routing: reading_urls.py

**Location**: `backend/biometrics/reading_urls.py` (new file)
**Mounted at**: `/api/biometric-readings/` (registered in `backend/tremoai_backend/urls.py`)

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BiometricReadingViewSet

router = DefaultRouter()
router.register(r'', BiometricReadingViewSet, basename='biometric-reading')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## Response Shape

### List Response (`GET /api/biometric-readings/`)

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/biometric-readings/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "patient_id": 5,
      "timestamp": "2026-02-18T12:00:00Z",
      "aX": 0.12,
      "aY": -0.05,
      "aZ": 9.81,
      "gX": 0.01,
      "gY": 0.02,
      "gZ": -0.01
    }
  ]
}
```

### Retrieve Response (`GET /api/biometric-readings/{id}/`)

```json
{
  "id": 1,
  "patient_id": 5,
  "timestamp": "2026-02-18T12:00:00Z",
  "aX": 0.12,
  "aY": -0.05,
  "aZ": 9.81,
  "gX": 0.01,
  "gY": 0.02,
  "gZ": -0.01
}
```

**Confirmed absent**: `flex_1`, `flex_2`, `flex_3`, `flex_4`, `flex_5`
