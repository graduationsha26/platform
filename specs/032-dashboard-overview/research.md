# Research: Dashboard Overview Page

**Branch**: `032-dashboard-overview` | **Date**: 2026-02-20

---

## Finding 1: Existing Analytics Endpoint Cannot Serve Dashboard Needs

**Decision**: Create a new `GET /api/analytics/dashboard/` endpoint separate from the existing `GET /api/analytics/stats/` endpoint.

**Rationale**: The existing `StatisticsView` at `/api/analytics/stats/` requires a `patient_id` query parameter and returns per-patient tremor statistics with pagination. The dashboard needs system-wide aggregates scoped to the logged-in doctor (total patients, active devices, alerts, 7-day cross-patient trend). These are fundamentally different queries that cannot be satisfied by the existing endpoint.

**Alternatives considered**:
- *Reuse `/api/analytics/stats/`*: Rejected — endpoint design is per-patient, adding optional patient_id with fallback to all-patients would break the existing contract and mix concerns.
- *Call multiple existing endpoints from the frontend*: Rejected — would require 3+ separate API calls, no single endpoint returns patient count or device status, and the frontend would need to aggregate across all patients.

---

## Finding 2: "Alerts" Definition (No Alert Model Exists)

**Decision**: Define `alerts_count` as the count of `BiometricSession` records belonging to the doctor's patients where `ml_prediction->>'severity' = 'severe'` and `session_start >= now() - interval '24 hours'`.

**Rationale**: No dedicated Alert model exists in the codebase. The `BiometricSession` model stores `ml_prediction` as a JSON field with a `severity` key (values: `mild`, `moderate`, `severe`). Severe sessions in the last 24 hours represent the most actionable clinical signal. The 24-hour window keeps the count relevant without surfacing stale events.

**Alternatives considered**:
- *Severe sessions in last 7 days*: Too broad — could surface hundreds of events, reducing urgency.
- *Device-offline alerts*: Also valid but overlaps with "Active Devices" card; keeping alerts tied to ML predictions maintains separation of concerns.
- *Create a new Alert model*: Out of scope for this feature; the spec does not require an acknowledgement workflow.

---

## Finding 3: "Active Devices" Definition

**Decision**: Define `active_devices` as the count of `Device` objects belonging to the doctor's patients where `status = 'online'`.

**Rationale**: The `Device` model has an explicit `status` field with values `online` / `offline`, maintained by the MQTT ingestion pipeline. This is the most direct signal of device activity. The `last_seen` field could be used as a fallback, but `status` is already authoritative.

**Alternatives considered**:
- *`last_seen` within last 15 minutes*: More nuanced but redundant given the `status` field already encodes this.
- *BiometricSession activity in last hour*: Indirect; a device could be online without active sessions.

---

## Finding 4: Tremor Trend Data Source

**Decision**: Aggregate the 7-day tremor trend from `TremorMetrics.dominant_amplitude` grouped by date, scoped to the doctor's patients.

**Rationale**: `TremorMetrics` stores per-window FFT analysis results (approximately 1 record per second per patient), with `dominant_amplitude` being the most relevant scalar measure of tremor intensity. It has better granularity than `BiometricSession.sensor_data` (which requires JSON unpacking of arrays). The table is already indexed on `window_start`, making date-range queries efficient.

**Alternatives considered**:
- *BiometricSession.sensor_data tremor_intensity arrays*: Requires unpacking JSON arrays and averaging; more complex and slower.
- *BiometricReading raw 6-axis values*: Too granular; no tremor intensity scalar available without FFT post-processing.
- *Use existing StatisticsService.get_daily_statistics()*: Requires a patient_id; would require looping over all patients and merging — O(N patients) queries instead of a single aggregation.

---

## Finding 5: Doctor–Patient Scoping

**Decision**: Scope all dashboard metrics to patients assigned to the logged-in doctor via `DoctorPatientAssignment`.

**Rationale**: The `DoctorPatientAssignment` model provides the canonical many-to-many link between doctors and patients. The existing analytics views already use this pattern. Consistency with the rest of the API is essential.

**SQL pattern** (Django ORM):
```python
# Patients scoped to the doctor
patients = Patient.objects.filter(doctor_assignments__doctor=request.user)

# Active devices scoped to those patients
active_devices = Device.objects.filter(patient__in=patients, status='online').count()

# Alerts (severe sessions in last 24h)
from django.utils import timezone
alerts = BiometricSession.objects.filter(
    patient__in=patients,
    session_start__gte=timezone.now() - timedelta(hours=24),
    ml_prediction__severity='severe'
).count()

# 7-day tremor trend (daily averages)
from django.db.models import Avg
from django.db.models.functions import TruncDate
trend = (
    TremorMetrics.objects
    .filter(patient__in=patients, window_start__date__gte=today - timedelta(days=6))
    .annotate(day=TruncDate('window_start'))
    .values('day')
    .annotate(avg_amplitude=Avg('dominant_amplitude'))
    .order_by('day')
)
```

---

## Finding 6: Frontend — DoctorDashboard Already Exists as Placeholder

**Decision**: Modify the existing `frontend/src/pages/DoctorDashboard.jsx` rather than creating a new page.

**Rationale**: The page already exists with the correct route (`/doctor/dashboard`), layout wrapper (`AppLayout`), and a 3-column card grid. It shows "--" placeholder values. The implementation replaces those placeholders with live data and adds the trend chart below the cards.

**Existing structure to build on**:
- 3-column responsive grid already scaffolded with Tailwind
- Color scheme established (primary, success, secondary tokens)
- `api.js` Axios client handles JWT injection automatically

---

## Finding 7: Recharts LineChart Pattern (from SuppressionEffectivenessChart)

**Decision**: Follow the pattern established by `SuppressionEffectivenessChart.jsx` for the `TremorTrendChart` component.

**Rationale**: An existing Recharts `LineChart` implementation is already in the codebase at `frontend/src/components/CMG/SuppressionEffectivenessChart.jsx`. It demonstrates the correct import pattern, data shape (array of objects with named keys), and use of `ResponsiveContainer`, `XAxis`, `YAxis`, `Tooltip`, `Legend`, and `Line` components.

**Data shape for chart**:
```js
// Expected format from API
[
  { date: "Feb 14", avg_amplitude: 0.45 },
  { date: "Feb 15", avg_amplitude: 0.52 },
  // ...
  { date: "Feb 20", avg_amplitude: 0.38 }
]
```
