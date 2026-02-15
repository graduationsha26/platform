# Research: Core Backend APIs

**Feature**: 001-core-backend-apis
**Date**: 2026-02-15
**Status**: Complete

## Purpose

Research technical decisions and best practices for implementing Django REST APIs with JWT authentication, patient management, device registration, and biometric data storage. Since the TremoAI constitution predefines the tech stack (Django 5.x, DRF, SimpleJWT, Supabase PostgreSQL), this research focuses on implementation patterns rather than technology selection.

## Research Areas

### 1. Django Project Structure for Multi-Domain APIs

**Decision**: Four Django apps (authentication, patients, devices, biometrics)

**Rationale**:
- Django best practice: one app per domain/bounded context
- Clear separation of concerns: each app owns its models, views, serializers, tests
- Independent testability: can test authentication without patient logic
- Aligns with spec user stories: US1→authentication, US2→patients, US3→devices, US4→biometrics
- Future extensibility: new features can add new apps without modifying existing code

**Alternatives Considered**:
- **Single monolithic app**: Rejected - all models in one app leads to tight coupling, harder testing, violates single responsibility
- **Django projects per domain**: Rejected - violates monorepo constitution principle, unnecessary deployment complexity
- **Blueprint/namespace structure**: Rejected - Django apps are the native Django approach

**Implementation Notes**:
- Each app has: models.py, serializers.py, views.py, urls.py, permissions.py, tests/
- Root urls.py includes app URLs with /api/ prefix
- Shared utilities (if needed) go in tremoai_backend/utils/

---

### 2. JWT Authentication with Django SimpleJWT

**Decision**: djangorestframework-simplejwt with custom user model extending AbstractUser

**Rationale**:
- Constitutional requirement: JWT tokens for authentication
- SimpleJWT is official DRF-recommended JWT library
- Access tokens (24h expiry) + refresh tokens (7 day expiry) balance security and UX
- Custom user model with role field (patient/doctor) enables role-based permissions
- Token payload can include user_id, email, role for frontend state management

**Configuration**:
```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
}
```

**Custom Claims**:
- Add role to token payload via custom TokenObtainPairSerializer
- Frontend can decode JWT to get user role without API call

**Alternatives Considered**:
- **Session-based auth**: Rejected - violates JWT constitutional requirement
- **OAuth2**: Rejected - unnecessary complexity for MVP, constitution specifies JWT
- **Third-party auth (Auth0, Firebase)**: Rejected - constitution requires Django SimpleJWT

---

### 3. Role-Based Access Control Implementation

**Decision**: Custom DRF permission classes (IsDoctor, IsPatient, IsOwnerOrDoctor)

**Rationale**:
- DRF permission classes are composable and testable
- Clear permission names express intent (IsDoctor reads better than lambda checks)
- Reusable across views: apply same permission to multiple endpoints
- Constitutional requirement: role-based access at API endpoint level

**Permission Classes**:
- `IsDoctor`: Requires user.role == 'doctor'
- `IsPatient`: Requires user.role == 'patient'
- `IsOwnerOrDoctor`: Allows patient to access own data, or any doctor
- `IsAuthenticated`: DRF built-in, requires valid JWT token

**Usage Pattern**:
```python
class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDoctor]  # Only doctors can CRUD patients

class BiometricSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrDoctor]  # Patients see own, doctors see all
```

**Alternatives Considered**:
- **Django built-in permissions**: Rejected - designed for admin UI, not API role-based access
- **View-level permission checks**: Rejected - scattered logic, harder to test, less reusable
- **Decorator-based permissions**: Rejected - DRF classes are more idiomatic and composable

---

### 4. Patient Search Implementation

**Decision**: django-filter with Q objects for case-insensitive partial name search

**Rationale**:
- DRF integrates django-filter out of the box (FilterBackend)
- PostgreSQL ILIKE operator for case-insensitive search (via icontains lookup)
- Q objects enable complex queries (search first_name OR last_name)
- Performant for <10k patient records (expected scale per constitution)
- Simple implementation, no external search service

**Implementation**:
```python
# patients/filters.py
class PatientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')

    def filter_name(self, queryset, name, value):
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )
```

**Alternatives Considered**:
- **PostgreSQL full-text search**: Rejected - overkill for name-only search, adds index complexity
- **Elasticsearch**: Rejected - out of scope for local development (violates constitution)
- **Frontend filtering**: Rejected - requires loading all patients, doesn't scale, poor UX

---

### 5. Device Status Tracking

**Decision**: Status field (CharField with choices: 'online'/'offline') + last_seen DateTimeField

**Rationale**:
- Simple model design: two fields capture all requirements
- Status field queryable: `Device.objects.filter(status='online')`
- last_seen enables "last seen 5 minutes ago" UX
- Future MQTT integration can POST to /api/devices/{id}/status/ to update
- No background job needed: device connection triggers status update

**Model Design**:
```python
class Device(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(null=True, blank=True)
```

**Status Update Flow**:
1. Device connects → MQTT handler calls DeviceStatusUpdateView
2. View updates: `device.status = 'online', device.last_seen = now()`
3. Device disconnects → MQTT handler calls DeviceStatusUpdateView with status='offline'

**Alternatives Considered**:
- **Separate DeviceStatus table**: Rejected - unnecessary 1-to-1 relationship, complicates queries
- **Time-based status inference**: Rejected - requires background job (out of scope), less accurate
- **Redis for status**: Rejected - adds dependency, local development constraint (constitution)

---

### 6. Biometric Data Storage Format

**Decision**: PostgreSQL JSONField for sensor measurements in BiometricSession model

**Rationale**:
- PostgreSQL native JSON support (queryable with JSON operators: @>, ->, ->>, #>)
- Flexible schema: sensor data format can evolve without migrations
- Store measurements as: `{"tremor_intensity": [0.5, 0.7, ...], "timestamps": [...], "frequency": 50}`
- Future analytics can query JSON fields: `WHERE sensor_data->>'tremor_intensity' > 0.8`
- Constitution requires PostgreSQL (has JSON), so no compatibility concerns

**Model Design**:
```python
class BiometricSession(models.Model):
    sensor_data = models.JSONField()  # PostgreSQL JSONField
    session_start = models.DateTimeField()
    session_duration = models.DurationField()
```

**Data Validation**:
- Serializer validates JSON structure before save
- Required keys: tremor_intensity (list), timestamps (list), frequency (int)
- Frontend can POST flexible sensor data as evolution happens

**Alternatives Considered**:
- **Separate SensorMeasurement table**: Rejected - complex queries for time-series, 10x more rows, slower aggregation
- **Binary blob (BinaryField)**: Rejected - not queryable, harder debugging, no JSON operators
- **Time-series database (TimescaleDB)**: Rejected - out of scope for MVP, local development constraint

---

### 7. API Pagination Strategy

**Decision**: DRF PageNumberPagination (50 items/page for biometric sessions, 20 for patients)

**Rationale**:
- REST standard: `?page=2&page_size=50`
- DRF built-in support: PageNumberPagination class
- User-friendly: page numbers match UI pagination components
- Spec requirement: FR-039 mandates pagination for biometric data (50 sessions/page)
- Works with django-filter: paginate after filtering

**Configuration**:
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

**Per-View Override**:
```python
class PatientViewSet:
    pagination_class = PageNumberPagination
    page_size = 20  # Patients: 20 per page
```

**Alternatives Considered**:
- **Cursor pagination**: Rejected - better for real-time feeds, unnecessary complexity for MVP
- **Limit/offset**: Rejected - less user-friendly, page numbers more intuitive for doctors
- **No pagination**: Rejected - spec explicitly requires it (FR-039), poor performance for large datasets

---

### 8. Error Handling Strategy

**Decision**: DRF exception handlers + custom exception classes for domain errors

**Rationale**:
- DRF handles common errors (404, 403, 400 validation) automatically
- Custom exceptions for domain logic: `DeviceAlreadyPairedException`, `UnpairedDeviceException`
- Consistent error response format: `{"error": "message", "code": "ERROR_CODE"}`
- HTTP status codes follow REST conventions (spec requirement: FR per API Standards section)

**Custom Exceptions**:
```python
# devices/exceptions.py
class DeviceAlreadyPairedException(APIException):
    status_code = 400
    default_detail = 'Device is already paired to another patient'
    default_code = 'device_already_paired'
```

**Error Response Format**:
```json
{
  "error": "Device is already paired to another patient",
  "code": "device_already_paired",
  "details": {"device_id": "abc123", "current_patient_id": 42}
}
```

**Alternatives Considered**:
- **Generic error messages**: Rejected - poor developer experience, harder debugging
- **HTTP status only**: Rejected - doesn't convey domain-specific error reasons
- **Exception middleware**: Rejected - DRF exception handlers are sufficient

---

### 9. Database Configuration for Supabase

**Decision**: dj-database-url to parse DATABASE_URL from .env file

**Rationale**:
- Constitution requires Supabase PostgreSQL (remote DB)
- Supabase provides DATABASE_URL in postgres://user:pass@host:port/db format
- dj-database-url parses connection string into Django DATABASES dict
- All secrets in .env (constitutional requirement)

**Configuration**:
```python
# settings.py
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

**.env file**:
```
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

**Alternatives Considered**:
- **Manual DATABASES dict**: Rejected - error-prone, multiple env vars instead of one URL
- **SQLite for development**: Rejected - violates constitution (Supabase PostgreSQL only)

---

## Research Summary

All technical decisions documented above follow constitutional principles:
- ✅ Django 5.x + DRF + SimpleJWT (Tech Stack Immutability)
- ✅ Supabase PostgreSQL with dj-database-url (Database Strategy)
- ✅ JWT authentication with patient/doctor roles (Authentication & Authorization)
- ✅ All secrets in .env files (Security-First Configuration)
- ✅ REST + JSON APIs with standard conventions (API Standards)
- ✅ Local development setup only (Development Scope)

**Next Steps**: Phase 1 - Create data-model.md and API contracts
